from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.routes.character_sheets_common import (
    get_character_sheet_or_404,
    get_party_with_gm_check,
    party_id,
    require_identifier,
    require_joined_player,
    require_party_member,
    to_character_sheet_read,
    user_id,
)
from app.api.routes.sessions._shared import record_session_activity
from app.api.routes.sessions.shop import (
    _ensure_player_session_state,
    _publish_session_state_realtime,
)
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.party import Party
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.user import User
from app.schemas.character_sheet import CharacterSheetRead
from app.services.character_progression import (
    CharacterProgressionError,
    approve_level_up as approve_level_up_data,
    deny_level_up as deny_level_up_data,
    request_level_up as request_level_up_data,
)
from app.services.session_state_finalize import finalize_session_state_data
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version


def get_open_party_session(
    party_id_value: str,
    session: Session,
) -> CampaignSession | None:
    return session.exec(
        select(CampaignSession).where(
            CampaignSession.party_id == party_id_value,
            (
                (CampaignSession.status == SessionStatus.LOBBY)
                | (CampaignSession.status == SessionStatus.ACTIVE)
            ),
        )
    ).first()


def get_campaign_member(
    campaign_id: str,
    member_user_id: str,
    session: Session,
) -> CampaignMember | None:
    return session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == member_user_id,
        )
    ).first()


def sync_progression_session_state(
    entry: CampaignSession | None,
    *,
    player_user_id: str,
    sheet_data: dict,
    session: Session,
):
    if entry is None:
        return None

    state = _ensure_player_session_state(entry, player_user_id, session)
    state.state_json = finalize_session_state_data({
        **state.state_json,
        "level": int(sheet_data.get("level", 1)),
        "experiencePoints": int(sheet_data.get("experiencePoints", 0)),
        "pendingLevelUp": bool(sheet_data.get("pendingLevelUp", False)),
    })
    session.add(state)
    return state


async def publish_level_up_event(
    party: Party,
    *,
    event_type: str,
    player_user_id: str,
    sheet: CharacterSheet,
) -> None:
    version = event_version(sheet.updated_at or sheet.created_at)
    data = sheet.data or {}
    await centrifugo.publish(
        campaign_channel(party.campaign_id),
        build_event(
            event_type,
            {
                "partyId": party_id(party),
                "campaignId": party.campaign_id,
                "playerUserId": player_user_id,
                "level": data.get("level", 1),
                "experiencePoints": data.get("experiencePoints", 0),
                "pendingLevelUp": data.get("pendingLevelUp", False),
            },
            version=version,
        ),
    )


def record_progression_activity(
    open_session: CampaignSession | None,
    *,
    command_type: str,
    actor_user_id: str,
    target_user_id: str,
    data: dict,
    session: Session,
) -> None:
    if open_session is None:
        return
    actor_member = get_campaign_member(open_session.campaign_id, actor_user_id, session)
    target_member = get_campaign_member(open_session.campaign_id, target_user_id, session)
    if actor_member is None:
        return
    record_session_activity(
        open_session,
        command_type,
        session,
        member_id=require_identifier(actor_member.id, "Campaign member is missing an id"),
        user_id=actor_user_id,
        actor_name=actor_member.display_name,
        payload={
            "targetUserId": target_user_id,
            "targetDisplayName": target_member.display_name if target_member else target_user_id,
            "level": int(data.get("level", 1)),
            "experiencePoints": int(data.get("experiencePoints", 0)),
            "pendingLevelUp": bool(data.get("pendingLevelUp", False)),
        },
    )


async def publish_progression_session_state(
    open_session: CampaignSession | None,
    *,
    player_user_id: str,
    state,
) -> None:
    if open_session is None or state is None:
        return
    await _publish_session_state_realtime(
        open_session,
        player_user_id,
        state.updated_at or state.created_at,
        state.state_json if isinstance(state.state_json, dict) else None,
    )


async def request_level_up_service(
    party_id_value: str,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    party = require_party_member(party_id_value, user, session)
    current_user_id = user_id(user)
    entry = get_character_sheet_or_404(party_id_value, current_user_id, session)
    try:
        data = request_level_up_data(entry.data)
    except CharacterProgressionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    entry.data = data
    session.add(entry)
    open_session = get_open_party_session(party_id_value, session)
    state = sync_progression_session_state(
        open_session,
        player_user_id=current_user_id,
        sheet_data=data,
        session=session,
    )
    record_progression_activity(
        open_session,
        command_type="level_up_requested",
        actor_user_id=current_user_id,
        target_user_id=current_user_id,
        data=data,
        session=session,
    )
    session.commit()
    session.refresh(entry)
    if state is not None:
        session.refresh(state)

    await publish_level_up_event(
        party,
        event_type="level_up_requested",
        player_user_id=current_user_id,
        sheet=entry,
    )
    await publish_progression_session_state(
        open_session,
        player_user_id=current_user_id,
        state=state,
    )
    return to_character_sheet_read(entry)


async def approve_level_up_service(
    party_id_value: str,
    player_user_id: str,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    party = get_party_with_gm_check(party_id_value, user, session)
    require_joined_player(party_id_value, player_user_id, session)
    entry = get_character_sheet_or_404(party_id_value, player_user_id, session)
    try:
        data = approve_level_up_data(entry.data)
    except CharacterProgressionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    entry.data = data
    session.add(entry)
    open_session = get_open_party_session(party_id_value, session)
    state = sync_progression_session_state(
        open_session,
        player_user_id=player_user_id,
        sheet_data=data,
        session=session,
    )
    record_progression_activity(
        open_session,
        command_type="level_up_approved",
        actor_user_id=user_id(user),
        target_user_id=player_user_id,
        data=data,
        session=session,
    )
    session.commit()
    session.refresh(entry)
    if state is not None:
        session.refresh(state)

    await publish_level_up_event(
        party,
        event_type="level_up_approved",
        player_user_id=player_user_id,
        sheet=entry,
    )
    await publish_progression_session_state(
        open_session,
        player_user_id=player_user_id,
        state=state,
    )
    return to_character_sheet_read(entry)


async def deny_level_up_service(
    party_id_value: str,
    player_user_id: str,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    party = get_party_with_gm_check(party_id_value, user, session)
    require_joined_player(party_id_value, player_user_id, session)
    entry = get_character_sheet_or_404(party_id_value, player_user_id, session)
    try:
        data = deny_level_up_data(entry.data)
    except CharacterProgressionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    entry.data = data
    session.add(entry)
    open_session = get_open_party_session(party_id_value, session)
    state = sync_progression_session_state(
        open_session,
        player_user_id=player_user_id,
        sheet_data=data,
        session=session,
    )
    record_progression_activity(
        open_session,
        command_type="level_up_denied",
        actor_user_id=user_id(user),
        target_user_id=player_user_id,
        data=data,
        session=session,
    )
    session.commit()
    session.refresh(entry)
    if state is not None:
        session.refresh(state)

    await publish_level_up_event(
        party,
        event_type="level_up_denied",
        player_user_id=player_user_id,
        sheet=entry,
    )
    await publish_progression_session_state(
        open_session,
        player_user_id=player_user_id,
        state=state,
    )
    return to_character_sheet_read(entry)
