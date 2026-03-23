from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.character_sheet import (
    CharacterSheetCreate,
    CharacterSheetRead,
    CharacterSheetUpdate,
)
from app.api.routes.character_sheets_common import (
    create_character_sheet_service,
    delete_character_sheet_service,
    get_my_character_sheet_service,
    get_party_character_sheet_service,
    update_character_sheet_service,
)
from app.api.routes.character_sheets_progression import (
    approve_level_up_service,
    deny_level_up_service,
    request_level_up_service,
)

router = APIRouter()


@router.get("/parties/{party_id}/character-sheet/me", response_model=CharacterSheetRead)
def get_my_character_sheet(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return get_my_character_sheet_service(party_id, user, session)


@router.get(
    "/parties/{party_id}/character-sheets/{player_user_id}",
    response_model=CharacterSheetRead,
)
def get_party_character_sheet(
    party_id: str,
    player_user_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return get_party_character_sheet_service(party_id, player_user_id, user, session)


@router.post(
    "/parties/{party_id}/character-sheet",
    response_model=CharacterSheetRead,
    status_code=201,
)
def create_character_sheet(
    party_id: str,
    payload: CharacterSheetCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return create_character_sheet_service(party_id, payload, user, session)


@router.put("/parties/{party_id}/character-sheet/me", response_model=CharacterSheetRead)
def update_character_sheet(
    party_id: str,
    payload: CharacterSheetUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return update_character_sheet_service(party_id, payload, user, session)


@router.delete("/parties/{party_id}/character-sheet/me", status_code=204)
def delete_character_sheet(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    delete_character_sheet_service(party_id, user, session)


@router.post(
    "/parties/{party_id}/character-sheet/me/request-level-up",
    response_model=CharacterSheetRead,
)
async def request_level_up(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return await request_level_up_service(party_id, user, session)


@router.post(
    "/parties/{party_id}/character-sheets/{player_user_id}/approve-level-up",
    response_model=CharacterSheetRead,
)
async def approve_level_up(
    party_id: str,
    player_user_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return await approve_level_up_service(party_id, player_user_id, user, session)


@router.post(
    "/parties/{party_id}/character-sheets/{player_user_id}/deny-level-up",
    response_model=CharacterSheetRead,
)
async def deny_level_up(
    party_id: str,
    player_user_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return await deny_level_up_service(party_id, player_user_id, user, session)
