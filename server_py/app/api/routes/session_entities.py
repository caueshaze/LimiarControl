from fastapi import APIRouter, Depends
from sqlmodel import Session as DbSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.session_entity import (
    SessionEntityCreate,
    SessionEntityPlayerRead,
    SessionEntityRead,
    SessionEntityUpdate,
)
from app.api.routes.session_entities_service import (
    add_session_entity_service,
    hide_session_entity_service,
    list_session_entities_service,
    list_visible_session_entities_service,
    remove_session_entity_service,
    reveal_session_entity_service,
    update_session_entity_service,
)

router = APIRouter()


@router.get("/sessions/{session_id}/entities", response_model=list[SessionEntityRead])
def list_session_entities(
    session_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return list_session_entities_service(session_id, user, session)


@router.post("/sessions/{session_id}/entities", response_model=SessionEntityRead, status_code=201)
async def add_session_entity(
    session_id: str,
    payload: SessionEntityCreate,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await add_session_entity_service(session_id, payload, user, session)


@router.put("/sessions/{session_id}/entities/{session_entity_id}", response_model=SessionEntityRead)
async def update_session_entity(
    session_id: str,
    session_entity_id: str,
    payload: SessionEntityUpdate,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await update_session_entity_service(
        session_id,
        session_entity_id,
        payload,
        user,
        session,
    )


@router.delete("/sessions/{session_id}/entities/{session_entity_id}", status_code=204)
async def remove_session_entity(
    session_id: str,
    session_entity_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    await remove_session_entity_service(session_id, session_entity_id, user, session)


@router.post("/sessions/{session_id}/entities/{session_entity_id}/reveal", response_model=SessionEntityRead)
async def reveal_session_entity(
    session_id: str,
    session_entity_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await reveal_session_entity_service(session_id, session_entity_id, user, session)


@router.post("/sessions/{session_id}/entities/{session_entity_id}/hide", response_model=SessionEntityRead)
async def hide_session_entity(
    session_id: str,
    session_entity_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await hide_session_entity_service(session_id, session_entity_id, user, session)


@router.get("/sessions/{session_id}/entities/visible", response_model=list[SessionEntityPlayerRead])
def list_visible_session_entities(
    session_id: str,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return list_visible_session_entities_service(session_id, user, session)
