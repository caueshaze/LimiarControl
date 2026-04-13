from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.models.session_state import SessionState
from app.services.centrifugo import centrifugo
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)
from ._shared import require_identifier, resolve_party_id_for_campaign
from .shop import _publish_session_state_realtime

VALID_COMMANDS = {
    "open_shop",
    "close_shop",
    "request_roll",
    "start_combat",
    "end_combat",
    "start_short_rest",
    "start_long_rest",
    "end_rest",
}


def validate_roll_target(
    entry: Session,
    target_user_id: object,
    session: DbSession,
) -> tuple[str, str] | None:
    if target_user_id is None:
        return None
    if not isinstance(target_user_id, str) or not target_user_id.strip():
        raise HTTPException(status_code=400, detail="Invalid target user")
    cleaned_target_user_id = target_user_id.strip()
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == cleaned_target_user_id,
            CampaignMember.role_mode == RoleMode.PLAYER,
        )
    ).first()
    if not member:
        raise HTTPException(
            status_code=400,
            detail="Target user must be a player in this campaign",
        )
    if entry.party_id:
        party_member = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.user_id == cleaned_target_user_id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not party_member:
            raise HTTPException(
                status_code=400,
                detail="Target user is not in the active party",
            )
    display_name = member.display_name or cleaned_target_user_id
    return cleaned_target_user_id, display_name


def require_active_gm_session(
    session_id: str,
    user,
    session: DbSession,
) -> tuple[Session, CampaignMember]:
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member or member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")
    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party or party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    return entry, member


def build_base_event_payload(
    entry: Session,
    member: CampaignMember,
    issued_at: datetime,
) -> dict:
    return {
        "sessionId": require_identifier(entry.id, "Session is missing an id"),
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "issuedBy": member.display_name,
        "issuedAt": issued_at.isoformat(),
    }


async def publish_state_updates(
    entry: Session,
    states: list[SessionState],
    issued_at: datetime,
) -> None:
    for state in states:
        await _publish_session_state_realtime(
            entry,
            state.player_user_id,
            state.updated_at or state.created_at or issued_at,
            state.state_json if isinstance(state.state_json, dict) else None,
        )


async def publish_command_event(
    entry: Session,
    event_type: str,
    event_payload: dict,
    issued_at: datetime,
) -> None:
    built_event = build_event(
        event_type,
        event_payload,
        version=event_version(issued_at),
    )
    await centrifugo.publish(
        session_channel(require_identifier(entry.id, "Session is missing an id")),
        built_event,
    )
    await centrifugo.publish(campaign_channel(entry.campaign_id), built_event)


def resolve_active_session_id(campaign_id: str, session: DbSession) -> str:
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        active = session.exec(
            select(Session).where(
                Session.party_id == party_id,
                Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    else:
        active = session.exec(
            select(Session).where(
                Session.campaign_id == campaign_id,
                Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    return require_identifier(active.id, "Session is missing an id")
