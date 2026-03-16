from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DbSession, select, func

from app.api.deps import get_current_user
from app.api.deprecation import log_deprecated_route
from app.db.session import get_session
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.models.session_runtime import SessionRuntime
from app.models.session_state import SessionState
from app.schemas.session import (
    ActiveSessionRead,
    SessionActivateRequest,
    SessionRead,
)
from ._shared import (
    DEPRECATION_REMOVAL_DATE,
    check_character_sheets,
    get_or_create_session_runtime,
    resolve_party_id_for_campaign,
    to_session_read,
)

router = APIRouter()


def _get_active_session(campaign_id: str, user, session: DbSession) -> ActiveSessionRead:
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        active = session.exec(
            select(Session).where(
                Session.party_id == party_id,
                Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
            )
        ).first()
    else:
        active = session.exec(
            select(Session).where(
                Session.campaign_id == campaign_id,
                Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
            )
        ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    return ActiveSessionRead(**to_session_read(active).model_dump())


async def _start_session(
    campaign_id: str,
    payload: SessionActivateRequest,
    user,
    session: DbSession,
) -> ActiveSessionRead:
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")

    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if not party_id:
        raise HTTPException(
            status_code=400,
            detail="No party found for campaign; create a party before starting sessions",
        )

    party_player_members = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.role == RoleMode.PLAYER,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).all()
    check_character_sheets(party_id, party_player_members, session)

    existing_active = session.exec(
        select(Session).where(
            Session.party_id == party_id,
            Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
        )
    ).first()
    last_closed_source: Session | None = None
    if existing_active:
        now = datetime.now(timezone.utc)
        existing_active.status = SessionStatus.CLOSED
        existing_active.ended_at = now
        if existing_active.started_at:
            existing_active.duration_seconds = max(
                0,
                existing_active.duration_seconds
                + int((now - existing_active.started_at).total_seconds()),
            )
        session.add(existing_active)
        session.commit()
        existing_runtime = session.exec(
            select(SessionRuntime).where(SessionRuntime.session_id == existing_active.id)
        ).first()
        if existing_runtime:
            existing_runtime.lobby_expected = []
            existing_runtime.lobby_ready = []
            existing_runtime.shop_open = False
            session.add(existing_runtime)
            session.commit()
        last_closed_source = existing_active
        closed_payload = {
            "sessionId": existing_active.id,
            "campaignId": campaign_id,
            "partyId": existing_active.party_id,
            "endedAt": now.isoformat(),
        }
        version = event_version(now)
        await centrifugo.publish(
            session_channel(existing_active.id),
            build_event("session_closed", closed_payload, version=version),
        )
        await centrifugo.publish(
            campaign_channel(campaign_id),
            build_event("session_closed", closed_payload, version=version),
        )

    if not last_closed_source:
        last_closed_source = session.exec(
            select(Session)
            .where(Session.party_id == party_id, Session.status == SessionStatus.CLOSED)
            .order_by(Session.ended_at.desc(), Session.sequence_number.desc())
        ).first()

    max_retries = 5
    for attempt in range(max_retries):
        next_number = session.exec(
            select(func.coalesce(func.max(Session.sequence_number), 0)).where(
                Session.party_id == party_id
            )
        ).one()
        number = int(next_number) + 1
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Invalid title")
        entry = Session(
            id=str(uuid4()),
            party_id=party_id,
            campaign_id=campaign_id,
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
    player_members = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.role_mode == RoleMode.PLAYER,
        )
    ).all()
    for m in player_members:
        prev = previous_by_user.get(m.user_id)
        base_sheet = session.exec(
            select(CharacterSheet).where(
                CharacterSheet.party_id == party_id,
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
    for pm in party_player_members:
        u = session.exec(select(UserModel).where(UserModel.id == pm.user_id)).first()
        expected[pm.user_id] = (u.display_name or u.username or pm.user_id) if u else pm.user_id

    if not expected:
        now = datetime.now(timezone.utc)
        entry.status = SessionStatus.ACTIVE
        entry.started_at = now
        runtime.lobby_expected = []
        runtime.lobby_ready = []
        runtime.shop_open = False
        session.add(entry)
        session.add(runtime)
        session.commit()
        session.refresh(entry)
        started_payload = {
            "sessionId": entry.id,
            "campaignId": campaign_id,
            "partyId": party_id,
            "title": entry.title,
            "startedAt": now.isoformat(),
        }
        version = event_version(entry.started_at or now)
        await centrifugo.publish(
            session_channel(entry.id),
            build_event("session_started", started_payload, version=version),
        )
        await centrifugo.publish(
            campaign_channel(campaign_id),
            build_event("session_started", started_payload, version=version),
        )
    else:
        expected_list = [{"userId": uid, "displayName": name} for uid, name in expected.items()]
        runtime.lobby_expected = expected_list
        runtime.lobby_ready = []
        runtime.shop_open = False
        session.add(runtime)
        session.commit()
        await centrifugo.publish(
            campaign_channel(campaign_id),
            build_event(
                "session_lobby",
                {
                    "sessionId": entry.id,
                    "campaignId": campaign_id,
                    "partyId": party_id,
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


@router.get("/campaigns/{campaign_id}/sessions/active", response_model=ActiveSessionRead)
def get_active_session(
    campaign_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return _get_active_session(campaign_id, user, session)


@router.get(
    "/campaigns/{campaign_id}/session/active",
    response_model=ActiveSessionRead,
    deprecated=True,
)
def get_active_session_deprecated(
    campaign_id: str,
    request: Request,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/campaigns/{campaign_id}/sessions/active."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/active",
        new_path="/api/campaigns/{campaign_id}/sessions/active",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    return _get_active_session(campaign_id, user, session)


@router.get("/campaigns/{campaign_id}/sessions", response_model=list[SessionRead])
def list_sessions(
    campaign_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        statement = (
            select(Session).where(Session.party_id == party_id)
            .order_by(Session.sequence_number.desc())
        )
    else:
        statement = (
            select(Session).where(Session.campaign_id == campaign_id)
            .order_by(Session.number.desc())
        )
    return [to_session_read(e) for e in session.exec(statement).all()]


@router.post("/campaigns/{campaign_id}/sessions", response_model=ActiveSessionRead)
async def create_session(
    campaign_id: str,
    payload: SessionActivateRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await _start_session(campaign_id, payload, user, session)


@router.post(
    "/campaigns/{campaign_id}/session/activate",
    response_model=ActiveSessionRead,
    deprecated=True,
)
async def activate_session_deprecated(
    campaign_id: str,
    payload: SessionActivateRequest,
    request: Request,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/campaigns/{campaign_id}/sessions."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/activate",
        new_path="/api/campaigns/{campaign_id}/sessions",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    return await _start_session(campaign_id, payload, user, session)
