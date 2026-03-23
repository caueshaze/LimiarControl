from fastapi import APIRouter, Depends, Request
from sqlmodel import Session as DbSession

from app.api.deprecation import log_deprecated_route
from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.session import SessionCommandRequest
from ._shared import DEPRECATION_REMOVAL_DATE
from .commands_common import resolve_active_session_id
from .commands_service import send_session_command_service

router = APIRouter()


@router.post("/sessions/{session_id}/commands")
async def send_session_command(
    session_id: str,
    payload: SessionCommandRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await send_session_command_service(session_id, payload, user, session)


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
    active_session_id = resolve_active_session_id(campaign_id, session)
    return await send_session_command_service(active_session_id, payload, user, session)
