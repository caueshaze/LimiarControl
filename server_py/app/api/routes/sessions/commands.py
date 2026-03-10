from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.api.deprecation import log_deprecated_route
from app.db.session import get_session
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, event_version, session_channel
from app.models.campaign import RoleMode
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.session import Session, SessionStatus
from app.schemas.session import SessionCommandRequest
from ._shared import DEPRECATION_REMOVAL_DATE, resolve_party_id_for_campaign

router = APIRouter()

_VALID_COMMANDS = {"open_shop", "close_shop", "request_roll"}


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
    if payload.type == "request_roll":
        expression = (payload.payload or {}).get("expression")
        if not expression or not isinstance(expression, str):
            raise HTTPException(status_code=400, detail="Missing dice expression")
    issued_at = datetime.now(timezone.utc)
    await centrifugo.publish(
        session_channel(entry.id),
        build_event(
            "gm_command",
            {
                "command": payload.type,
                "data": payload.payload or {},
                "issuedBy": member.display_name,
                "issuedAt": issued_at.isoformat(),
            },
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
