from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user
from app.api.routes.character_sheet_drafts_common import (
    archive_party_character_sheet_draft_service,
    create_party_character_sheet_draft_service,
    delete_party_character_sheet_draft_service,
    derive_party_character_sheet_draft_service,
    get_party_character_sheet_draft_service,
    list_party_character_sheet_drafts_service,
    restore_party_character_sheet_draft_service,
    update_party_character_sheet_draft_service,
)
from app.api.routes.character_sheets_common import (
    get_party_or_404,
    publish_character_sheet_realtime,
)
from app.db.session import get_session
from app.models.user import User
from app.schemas.character_sheet import CharacterSheetRead
from app.schemas.character_sheet_draft import (
    PartyCharacterSheetDraftCreate,
    PartyCharacterSheetDraftDeriveRequest,
    PartyCharacterSheetDraftRead,
    PartyCharacterSheetDraftUpdate,
)

router = APIRouter()


@router.get(
    "/parties/{party_id}/character-sheet-drafts",
    response_model=list[PartyCharacterSheetDraftRead],
)
def list_party_character_sheet_drafts(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return list_party_character_sheet_drafts_service(party_id, user, session)


@router.post(
    "/parties/{party_id}/character-sheet-drafts",
    response_model=PartyCharacterSheetDraftRead,
    status_code=201,
)
def create_party_character_sheet_draft(
    party_id: str,
    payload: PartyCharacterSheetDraftCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return create_party_character_sheet_draft_service(party_id, payload, user, session)


@router.get(
    "/parties/{party_id}/character-sheet-drafts/{draft_id}",
    response_model=PartyCharacterSheetDraftRead,
)
def get_party_character_sheet_draft(
    party_id: str,
    draft_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return get_party_character_sheet_draft_service(party_id, draft_id, user, session)


@router.put(
    "/parties/{party_id}/character-sheet-drafts/{draft_id}",
    response_model=PartyCharacterSheetDraftRead,
)
def update_party_character_sheet_draft(
    party_id: str,
    draft_id: str,
    payload: PartyCharacterSheetDraftUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return update_party_character_sheet_draft_service(
        party_id,
        draft_id,
        payload,
        user,
        session,
    )


@router.post(
    "/parties/{party_id}/character-sheet-drafts/{draft_id}/archive",
    response_model=PartyCharacterSheetDraftRead,
)
def archive_party_character_sheet_draft(
    party_id: str,
    draft_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return archive_party_character_sheet_draft_service(party_id, draft_id, user, session)


@router.post(
    "/parties/{party_id}/character-sheet-drafts/{draft_id}/restore",
    response_model=PartyCharacterSheetDraftRead,
)
def restore_party_character_sheet_draft(
    party_id: str,
    draft_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return restore_party_character_sheet_draft_service(party_id, draft_id, user, session)


@router.delete("/parties/{party_id}/character-sheet-drafts/{draft_id}", status_code=204)
def delete_party_character_sheet_draft(
    party_id: str,
    draft_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    delete_party_character_sheet_draft_service(party_id, draft_id, user, session)


@router.post(
    "/parties/{party_id}/character-sheet-drafts/{draft_id}/derive",
    response_model=CharacterSheetRead,
)
async def derive_party_character_sheet_draft(
    party_id: str,
    draft_id: str,
    payload: PartyCharacterSheetDraftDeriveRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    record = derive_party_character_sheet_draft_service(
        party_id,
        draft_id,
        payload,
        user,
        session,
    )
    party = get_party_or_404(party_id, session)
    await publish_character_sheet_realtime(
        party.campaign_id,
        party_id,
        record,
        "delivered",
    )
    return record
