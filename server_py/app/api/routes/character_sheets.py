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
    accept_my_character_sheet_service,
    create_character_sheet_service,
    delete_character_sheet_service,
    get_my_character_sheet_service,
    get_party_or_404,
    get_party_character_sheet_service,
    publish_character_sheet_realtime,
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
async def create_character_sheet(
    party_id: str,
    payload: CharacterSheetCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    record = create_character_sheet_service(party_id, payload, user, session)
    party = get_party_or_404(party_id, session)
    await publish_character_sheet_realtime(
        party.campaign_id,
        party_id,
        record,
        "created",
    )
    return record


@router.put("/parties/{party_id}/character-sheet/me", response_model=CharacterSheetRead)
async def update_character_sheet(
    party_id: str,
    payload: CharacterSheetUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    record = update_character_sheet_service(party_id, payload, user, session)
    party = get_party_or_404(party_id, session)
    await publish_character_sheet_realtime(
        party.campaign_id,
        party_id,
        record,
        "updated",
    )
    return record


@router.post("/parties/{party_id}/character-sheet/me/accept", response_model=CharacterSheetRead)
async def accept_my_character_sheet(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    record = accept_my_character_sheet_service(party_id, user, session)
    party = get_party_or_404(party_id, session)
    await publish_character_sheet_realtime(
        party.campaign_id,
        party_id,
        record,
        "accepted",
    )
    return record


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
