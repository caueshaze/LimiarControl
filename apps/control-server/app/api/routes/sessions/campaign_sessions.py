from fastapi import APIRouter, Depends, Request
from sqlmodel import Session as DbSession

from app.api.deprecation import log_deprecated_route
from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.session import (
    ActiveSessionRead,
    SessionActivateRequest,
    SessionRead,
)
from ._shared import DEPRECATION_REMOVAL_DATE
from .campaign_sessions_common import get_active_session_service, list_sessions_service
from .campaign_sessions_start_service import start_session_service

router = APIRouter()


@router.get("/campaigns/{campaign_id}/sessions/active", response_model=ActiveSessionRead)
def get_active_session(
    campaign_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return get_active_session_service(campaign_id, user, session)


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
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/active",
        new_path="/api/campaigns/{campaign_id}/sessions/active",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    return get_active_session_service(campaign_id, user, session)


@router.get("/campaigns/{campaign_id}/sessions", response_model=list[SessionRead])
def list_sessions(
    campaign_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return list_sessions_service(campaign_id, user, session)


@router.post("/campaigns/{campaign_id}/sessions", response_model=ActiveSessionRead)
async def create_session(
    campaign_id: str,
    payload: SessionActivateRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await start_session_service(campaign_id, payload, user, session)


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
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/activate",
        new_path="/api/campaigns/{campaign_id}/sessions",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    return await start_session_service(campaign_id, payload, user, session)
