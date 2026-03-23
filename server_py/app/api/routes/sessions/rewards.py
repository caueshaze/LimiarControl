from fastapi import APIRouter, Depends
from sqlmodel import Session as DbSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.session_reward import (
    SessionGrantCurrencyRead,
    SessionGrantCurrencyRequest,
    SessionGrantItemRead,
    SessionGrantItemRequest,
    SessionGrantXpRead,
    SessionGrantXpRequest,
)
from .rewards_service import (
    grant_session_currency_service,
    grant_session_item_service,
    grant_session_xp_service,
)

router = APIRouter()


@router.post(
    "/sessions/{session_id}/grants/currency",
    response_model=SessionGrantCurrencyRead,
)
async def grant_session_currency(
    session_id: str,
    payload: SessionGrantCurrencyRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await grant_session_currency_service(session_id, payload, user, session)


@router.post(
    "/sessions/{session_id}/grants/item",
    response_model=SessionGrantItemRead,
)
async def grant_session_item(
    session_id: str,
    payload: SessionGrantItemRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await grant_session_item_service(session_id, payload, user, session)


@router.post(
    "/sessions/{session_id}/grants/xp",
    response_model=SessionGrantXpRead,
)
async def grant_session_xp(
    session_id: str,
    payload: SessionGrantXpRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await grant_session_xp_service(session_id, payload, user, session)
