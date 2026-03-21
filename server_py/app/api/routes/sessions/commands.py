from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.api.deprecation import log_deprecated_route
from app.db.session import get_session
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session, SessionStatus
from app.models.session_state import SessionState
from app.schemas.session import SessionCommandRequest
from app.services.session_rest import (
    SessionRestError,
    end_rest as end_rest_state,
    start_rest as start_rest_state,
)
from ._shared import (
    DEPRECATION_REMOVAL_DATE,
    get_or_create_session_runtime,
    get_session_rest_state,
    parse_expression,
    record_session_activity,
    resolve_party_id_for_campaign,
)
from .shop import _publish_session_state_realtime

router = APIRouter()

_VALID_COMMANDS = {
    "open_shop",
    "close_shop",
    "request_roll",
    "start_combat",
    "end_combat",
    "start_short_rest",
    "start_long_rest",
    "end_rest",
}


def _validate_roll_target(
    entry: Session,
    target_user_id: object,
    session: DbSession,
) -> tuple[str, str] | None:
    if target_user_id is None:
        return None
    if not isinstance(target_user_id, str) or not target_user_id.strip():
        raise HTTPException(status_code=400, detail="Invalid target user")
    target_user_id = target_user_id.strip()
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == target_user_id,
            CampaignMember.role_mode == RoleMode.PLAYER,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=400, detail="Target user must be a player in this campaign")
    if entry.party_id:
        party_member = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.user_id == target_user_id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not party_member:
            raise HTTPException(status_code=400, detail="Target user is not in the active party")
    display_name = member.display_name or target_user_id
    return target_user_id, display_name


async def _send_session_command(
    session_id: str,
    payload: SessionCommandRequest,
    user,
    session: DbSession,
):
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
    if payload.type not in _VALID_COMMANDS:
        raise HTTPException(status_code=400, detail="Invalid command")
    runtime = get_or_create_session_runtime(entry.id, session)
    current_rest_state = get_session_rest_state(entry.id, session)
    issued_at = datetime.now(timezone.utc)
    payload_data = payload.payload or {}
    activity_payload: dict = {}
    if payload.type == "request_roll":
        expression = payload_data.get("expression")
        if not expression or not isinstance(expression, str):
            raise HTTPException(status_code=400, detail="Missing dice expression")
        if not parse_expression(expression.strip()):
            raise HTTPException(status_code=400, detail="Invalid dice expression")
        activity_payload["expression"] = expression.strip()
        reason = payload_data.get("reason")
        if reason is not None:
            if not isinstance(reason, str):
                raise HTTPException(status_code=400, detail="Reason must be a string")
            reason = reason.strip()
            if reason:
                activity_payload["reason"] = reason
        mode = payload_data.get("mode")
        if mode is not None:
            if mode not in {"advantage", "disadvantage"}:
                raise HTTPException(status_code=400, detail="Invalid roll mode")
            activity_payload["mode"] = mode
        target = _validate_roll_target(entry, payload_data.get("targetUserId"), session)
        if target:
            activity_payload["targetUserId"] = target[0]
            activity_payload["targetDisplayName"] = target[1]
    event_payload = {
        "sessionId": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "issuedBy": member.display_name,
        "issuedAt": issued_at.isoformat(),
    }
    event_type = payload.type
    if payload.type == "open_shop":
        runtime.shop_open = True
        activity_payload["shopOpen"] = True
        record_session_activity(
            entry,
            "open_shop",
            session,
            member_id=member.id,
            user_id=user.id,
            actor_name=member.display_name,
            payload=activity_payload,
            created_at=issued_at,
        )
        session.add(runtime)
        session.commit()
        event_type = "shop_opened"
        event_payload["shopOpen"] = True
    elif payload.type == "close_shop":
        runtime.shop_open = False
        activity_payload["shopOpen"] = False
        record_session_activity(
            entry,
            "close_shop",
            session,
            member_id=member.id,
            user_id=user.id,
            actor_name=member.display_name,
            payload=activity_payload,
            created_at=issued_at,
        )
        session.add(runtime)
        session.commit()
        event_type = "shop_closed"
        event_payload["shopOpen"] = False
    elif payload.type == "request_roll":
        event_type = "roll_requested"
        event_payload.update(activity_payload)
        record_session_activity(
            entry,
            "request_roll",
            session,
            member_id=member.id,
            user_id=user.id,
            actor_name=member.display_name,
            payload=activity_payload,
            created_at=issued_at,
        )
        session.commit()
    elif payload.type == "start_combat":
        if current_rest_state != "exploration":
            raise HTTPException(status_code=400, detail="Cannot start combat during a rest")
        runtime.combat_active = True
        note = payload_data.get("note")
        if note is not None:
            if not isinstance(note, str):
                raise HTTPException(status_code=400, detail="Combat note must be a string")
            note = note.strip()
            if note:
                activity_payload["note"] = note
        record_session_activity(
            entry,
            "start_combat",
            session,
            member_id=member.id,
            user_id=user.id,
            actor_name=member.display_name,
            payload=activity_payload,
            created_at=issued_at,
        )
        session.add(runtime)
        session.commit()
        event_type = "combat_started"
        event_payload["combatActive"] = True
        event_payload.update(activity_payload)
    elif payload.type == "end_combat":
        runtime.combat_active = False
        note = payload_data.get("note")
        if note is not None:
            if not isinstance(note, str):
                raise HTTPException(status_code=400, detail="Combat note must be a string")
            note = note.strip()
            if note:
                activity_payload["note"] = note
        record_session_activity(
            entry,
            "end_combat",
            session,
            member_id=member.id,
            user_id=user.id,
            actor_name=member.display_name,
            payload=activity_payload,
            created_at=issued_at,
        )
        session.add(runtime)
        session.commit()
        event_type = "combat_ended"
        event_payload["combatActive"] = False
        event_payload.update(activity_payload)
    elif payload.type in {"start_short_rest", "start_long_rest"}:
        if runtime.combat_active:
            raise HTTPException(status_code=400, detail="Cannot start a rest during combat")
        if current_rest_state != "exploration":
            raise HTTPException(status_code=400, detail="A rest is already active")

        target_rest_type = "short_rest" if payload.type == "start_short_rest" else "long_rest"
        activity_payload["restType"] = target_rest_type
        record_session_activity(
            entry,
            payload.type,
            session,
            member_id=member.id,
            user_id=user.id,
            actor_name=member.display_name,
            payload=activity_payload,
            created_at=issued_at,
        )
        states = session.exec(
            select(SessionState).where(SessionState.session_id == entry.id)
        ).all()
        if not states:
            raise HTTPException(status_code=400, detail="Session has no player states")

        for state in states:
            try:
                state.state_json = start_rest_state(state.state_json, target_rest_type)
            except SessionRestError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            session.add(state)

        session.commit()
        for state in states:
            session.refresh(state)

        event_type = "rest_started"
        event_payload["restType"] = target_rest_type
        event_payload["issuedAt"] = issued_at.isoformat()
        for state in states:
            await _publish_session_state_realtime(
                entry,
                state.player_user_id,
                state.updated_at or state.created_at or issued_at,
                state.state_json if isinstance(state.state_json, dict) else None,
            )
    elif payload.type == "end_rest":
        if current_rest_state == "exploration":
            raise HTTPException(status_code=400, detail="No rest is active")
        activity_payload["restType"] = current_rest_state
        record_session_activity(
            entry,
            "end_rest",
            session,
            member_id=member.id,
            user_id=user.id,
            actor_name=member.display_name,
            payload=activity_payload,
            created_at=issued_at,
        )

        states = session.exec(
            select(SessionState).where(SessionState.session_id == entry.id)
        ).all()
        if not states:
            raise HTTPException(status_code=400, detail="Session has no player states")

        ended_rest_type = current_rest_state
        for state in states:
            try:
                state.state_json, ended_rest_type = end_rest_state(state.state_json)
            except SessionRestError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            session.add(state)

        session.commit()
        for state in states:
            session.refresh(state)

        event_type = "rest_ended"
        event_payload["restType"] = ended_rest_type
        event_payload["issuedAt"] = issued_at.isoformat()
        for state in states:
            await _publish_session_state_realtime(
                entry,
                state.player_user_id,
                state.updated_at or state.created_at or issued_at,
                state.state_json if isinstance(state.state_json, dict) else None,
            )
    await centrifugo.publish(
        session_channel(entry.id),
        build_event(
            event_type,
            event_payload,
            version=event_version(issued_at),
        ),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event(
            event_type,
            event_payload,
            version=event_version(issued_at),
        ),
    )
    return {"ok": True}


@router.post("/sessions/{session_id}/commands")
async def send_session_command(
    session_id: str,
    payload: SessionCommandRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await _send_session_command(session_id, payload, user, session)


@router.post("/campaigns/{campaign_id}/session/command", deprecated=True)
async def send_session_command_deprecated(
    campaign_id: str,
    payload: SessionCommandRequest,
    request: Request,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/sessions/{session_id}/commands."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/command",
        new_path="/api/sessions/{session_id}/commands",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        active = session.exec(
            select(Session).where(
                Session.party_id == party_id, Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    else:
        active = session.exec(
            select(Session).where(
                Session.campaign_id == campaign_id, Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    return await _send_session_command(active.id, payload, user, session)
