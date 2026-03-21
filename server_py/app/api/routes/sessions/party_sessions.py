from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DbSession, select, func

from app.api.deps import get_current_user
from app.db.session import get_session
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.models.campaign import RoleMode
from app.models.character_sheet import CharacterSheet
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.models.session_state import SessionState
from app.schemas.session import ActiveSessionRead, SessionCreateByParty, SessionRead
from ._shared import (
    check_character_sheets,
    get_or_create_session_runtime,
    require_party_gm,
    require_party_member_or_gm,
    to_session_read,
)

router = APIRouter()


async def _start_session_for_party(
    party: Party,
    payload: SessionCreateByParty,
    user,
    session: DbSession,
) -> ActiveSessionRead:
    if party.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="GM required")
    existing_active = session.exec(
        select(Session).where(
            Session.party_id == party.id,
            Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
        )
    ).first()
    if existing_active:
        raise HTTPException(status_code=409, detail="Active session already exists")

    player_members = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party.id,
            PartyMember.role == RoleMode.PLAYER,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).all()
    check_character_sheets(party.id, player_members, session)

    last_closed_source = session.exec(
        select(Session)
        .where(Session.party_id == party.id, Session.status == SessionStatus.CLOSED)
        .order_by(Session.ended_at.desc(), Session.sequence_number.desc())
    ).first()

    max_retries = 5
    for attempt in range(max_retries):
        next_number = session.exec(
            select(func.coalesce(func.max(Session.sequence_number), 0)).where(
                Session.party_id == party.id
            )
        ).one()
        number = int(next_number) + 1
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Invalid title")
        entry = Session(
            id=str(uuid4()),
            party_id=party.id,
            campaign_id=party.campaign_id,
            number=number,
            sequence_number=number,
            title=title,
            status=SessionStatus.LOBBY,
            started_at=None,
        )
        session.add(entry)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            if attempt < max_retries - 1:
                continue
            raise
        session.refresh(entry)
        break
    else:
        raise HTTPException(status_code=409, detail="Failed to allocate session number")

    previous_states = []
    if last_closed_source:
        previous_states = session.exec(
            select(SessionState).where(SessionState.session_id == last_closed_source.id)
        ).all()
    previous_by_user = {s.player_user_id: s for s in previous_states}
    for m in player_members:
        prev = previous_by_user.get(m.user_id)
        base_sheet = session.exec(
            select(CharacterSheet).where(
                CharacterSheet.party_id == party.id,
                CharacterSheet.player_user_id == m.user_id,
            )
        ).first()
        cloned = (
            dict(prev.state_json)
            if prev and isinstance(prev.state_json, dict)
            else dict(base_sheet.data)
            if base_sheet and isinstance(base_sheet.data, dict)
            else {}
        )
        session.add(SessionState(
            id=str(uuid4()), session_id=entry.id, player_user_id=m.user_id, state_json=cloned,
        ))
    session.commit()
    runtime = get_or_create_session_runtime(entry.id, session)

    from app.models.user import User as UserModel
    expected: dict[str, str] = {}
    for pm in player_members:
        u = session.exec(select(UserModel).where(UserModel.id == pm.user_id)).first()
        expected[pm.user_id] = (u.display_name or u.username or pm.user_id) if u else pm.user_id

    if not expected:
        now = datetime.now(timezone.utc)
        entry.status = SessionStatus.ACTIVE
        entry.started_at = now
        runtime.lobby_expected = []
        runtime.lobby_ready = []
        runtime.shop_open = False
        runtime.combat_active = False
        session.add(entry)
        session.add(runtime)
        session.commit()
        session.refresh(entry)
        started_payload = {
            "sessionId": entry.id,
            "campaignId": party.campaign_id,
            "partyId": party.id,
            "title": entry.title,
            "startedAt": now.isoformat(),
        }
        version = event_version(entry.started_at or now)
        await centrifugo.publish(
            session_channel(entry.id),
            build_event("session_started", started_payload, version=version),
        )
        await centrifugo.publish(
            campaign_channel(party.campaign_id),
            build_event("session_started", started_payload, version=version),
        )
    else:
        expected_list = [{"userId": uid, "displayName": name} for uid, name in expected.items()]
        runtime.lobby_expected = expected_list
        runtime.lobby_ready = []
        runtime.shop_open = False
        runtime.combat_active = False
        session.add(runtime)
        session.commit()
        await centrifugo.publish(
            campaign_channel(party.campaign_id),
            build_event(
                "session_lobby",
                {
                    "sessionId": entry.id,
                    "campaignId": party.campaign_id,
                    "partyId": party.id,
                    "title": entry.title,
                    "expectedPlayers": expected_list,
                    "readyUserIds": [],
                    "readyCount": 0,
                    "totalCount": len(expected_list),
                },
                version=event_version(entry.created_at),
            ),
        )
    return ActiveSessionRead(**to_session_read(entry).model_dump())


@router.post("/parties/{party_id}/sessions", response_model=ActiveSessionRead)
async def create_party_session(
    party_id: str,
    payload: SessionCreateByParty,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    party = require_party_gm(party_id, user, session)
    return await _start_session_for_party(party, payload, user, session)


@router.get("/parties/{party_id}/sessions", response_model=list[SessionRead])
def list_party_sessions(
    party_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    require_party_member_or_gm(party_id, user, session)
    entries = session.exec(
        select(Session).where(Session.party_id == party_id)
        .order_by(Session.sequence_number.desc())
    ).all()
    return [to_session_read(e) for e in entries]


@router.get("/parties/{party_id}/sessions/active", response_model=ActiveSessionRead)
def get_party_active_session(
    party_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    require_party_member_or_gm(party_id, user, session)
    active = session.exec(
        select(Session).where(
            Session.party_id == party_id,
            Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
        )
    ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    return ActiveSessionRead(**to_session_read(active).model_dump())
