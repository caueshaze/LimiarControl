from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DbSession, func, select

from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.models.session_runtime import SessionRuntime
from app.models.session_state import SessionState
from app.models.user import User
from app.schemas.session import ActiveSessionRead, LobbyPlayer, SessionActivateRequest
from app.services.session_rest import ensure_rest_state
from app.services.session_state_finalize import finalize_session_state_data
from ._shared import check_character_sheets, get_or_create_session_runtime, to_session_read
from .campaign_sessions_common import (
    build_expected_players,
    get_open_campaign_session,
    publish_session_closed,
    publish_session_lobby,
    publish_session_started,
    require_campaign_member_role,
    require_identifier,
    resolve_party_id_for_campaign,
    utcnow,
)


def find_last_closed_session(party_id: str, session: DbSession) -> Session | None:
    entries = list(
        session.exec(
            select(Session).where(
                Session.party_id == party_id,
                Session.status == SessionStatus.CLOSED,
            )
        ).all()
    )
    entries.sort(
        key=lambda entry: (
            entry.ended_at.timestamp() if entry.ended_at is not None else 0.0,
            entry.sequence_number if entry.sequence_number is not None else 0,
        ),
        reverse=True,
    )
    return entries[0] if entries else None


def clone_session_states(
    *,
    entry: Session,
    last_closed_source: Session | None,
    party_id: str,
    campaign_id: str,
    session: DbSession,
) -> None:
    previous_states: list[SessionState] = []
    if last_closed_source is not None:
        previous_states = list(
            session.exec(
                select(SessionState).where(
                    SessionState.session_id == require_identifier(
                        last_closed_source.id,
                        "Previous session is missing an id",
                    )
                )
            ).all()
        )
    previous_by_user = {state.player_user_id: state for state in previous_states}
    campaign_players = list(
        session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == campaign_id,
                CampaignMember.role_mode == RoleMode.PLAYER,
            )
        ).all()
    )
    for campaign_player in campaign_players:
        prev = previous_by_user.get(campaign_player.user_id)
        base_sheet = session.exec(
            select(CharacterSheet).where(
                CharacterSheet.party_id == party_id,
                CharacterSheet.player_user_id == campaign_player.user_id,
            )
        ).first()
        cloned = (
            dict(prev.state_json)
            if prev and isinstance(prev.state_json, dict)
            else dict(base_sheet.data)
            if base_sheet and isinstance(base_sheet.data, dict)
            else {}
        )
        cloned = ensure_rest_state(cloned)
        cloned["restState"] = "exploration"
        cloned = finalize_session_state_data(cloned)
        session.add(
            SessionState(
                id=str(uuid4()),
                session_id=require_identifier(entry.id, "Session is missing an id"),
                player_user_id=campaign_player.user_id,
                state_json=cloned,
                created_at=utcnow(),
                updated_at=None,
            )
        )


def reset_runtime(runtime: SessionRuntime) -> None:
    runtime.lobby_expected = []
    runtime.lobby_ready = []
    runtime.shop_open = False
    runtime.combat_active = False


def create_lobby_session(
    *,
    campaign_id: str,
    party_id: str,
    title: str,
    session: DbSession,
) -> Session:
    max_retries = 5
    for attempt in range(max_retries):
        next_number_raw = session.exec(
            select(func.coalesce(func.max(Session.sequence_number), 0)).where(
                Session.party_id == party_id
            )
        ).one()
        number = int(next_number_raw or 0) + 1
        entry = Session(
            id=str(uuid4()),
            party_id=party_id,
            campaign_id=campaign_id,
            number=number,
            sequence_number=number,
            title=title,
            status=SessionStatus.LOBBY,
            started_at=None,
            ended_at=None,
            created_at=utcnow(),
            updated_at=None,
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
        return entry
    raise HTTPException(status_code=409, detail="Failed to allocate session number")


async def start_session_service(
    campaign_id: str,
    payload: SessionActivateRequest,
    user: User,
    session: DbSession,
) -> ActiveSessionRead:
    _campaign, member = require_campaign_member_role(campaign_id, user, session)
    if member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")

    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if not party_id:
        raise HTTPException(
            status_code=400,
            detail="No party found for campaign; create a party before starting sessions",
        )

    party_player_members = list(
        session.exec(
            select(PartyMember).where(
                PartyMember.party_id == party_id,
                PartyMember.role == RoleMode.PLAYER,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).all()
    )
    check_character_sheets(party_id, party_player_members, session)

    existing_active = get_open_campaign_session(
        campaign_id=campaign_id,
        party_id=party_id,
        session=session,
    )
    last_closed_source: Session | None = None
    if existing_active is not None:
        now = utcnow()
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
            select(SessionRuntime).where(
                SessionRuntime.session_id
                == require_identifier(existing_active.id, "Session is missing an id")
            )
        ).first()
        if existing_runtime is not None:
            reset_runtime(existing_runtime)
            session.add(existing_runtime)
            session.commit()
        last_closed_source = existing_active
        await publish_session_closed(
            existing_active=existing_active,
            campaign_id=campaign_id,
            ended_at=now,
        )

    if last_closed_source is None:
        last_closed_source = find_last_closed_session(party_id, session)

    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Invalid title")

    entry = create_lobby_session(
        campaign_id=campaign_id,
        party_id=party_id,
        title=title,
        session=session,
    )
    clone_session_states(
        entry=entry,
        last_closed_source=last_closed_source,
        party_id=party_id,
        campaign_id=campaign_id,
        session=session,
    )
    session.commit()

    runtime = get_or_create_session_runtime(
        require_identifier(entry.id, "Session is missing an id"),
        session,
    )
    expected = build_expected_players(party_player_members, session)

    if not expected:
        now = utcnow()
        entry.status = SessionStatus.ACTIVE
        entry.started_at = now
        reset_runtime(runtime)
        session.add(entry)
        session.add(runtime)
        session.commit()
        session.refresh(entry)
        await publish_session_started(
            entry=entry,
            campaign_id=campaign_id,
            party_id=party_id,
            started_at=now,
        )
    else:
        expected_list = [
            LobbyPlayer(userId=user_id, displayName=display_name).model_dump()
            for user_id, display_name in expected.items()
        ]
        runtime.lobby_expected = expected_list
        runtime.lobby_ready = []
        runtime.shop_open = False
        runtime.combat_active = False
        session.add(runtime)
        session.commit()
        await publish_session_lobby(
            entry=entry,
            campaign_id=campaign_id,
            party_id=party_id,
            expected_list=expected_list,
        )

    return ActiveSessionRead(**to_session_read(entry).model_dump())
