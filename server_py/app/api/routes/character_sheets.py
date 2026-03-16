from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.character_sheet import CharacterSheet
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.schemas.character_sheet import (
    CharacterSheetCreate,
    CharacterSheetRead,
    CharacterSheetUpdate,
)
from app.services.character_sheet_inventory import sync_character_sheet_inventory

router = APIRouter()


def _require_party_member(party_id: str, user, session: Session) -> Party:
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id == user.id:
        return party
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a party member")
    return party


def _to_read(entry: CharacterSheet) -> CharacterSheetRead:
    return CharacterSheetRead(
        id=entry.id,
        partyId=entry.party_id,
        playerId=entry.player_user_id,
        data=entry.data,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


@router.get("/parties/{party_id}/character-sheet/me", response_model=CharacterSheetRead)
def get_my_character_sheet(
    party_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_party_member(party_id, user, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")
    return _to_read(entry)


@router.post(
    "/parties/{party_id}/character-sheet",
    response_model=CharacterSheetRead,
    status_code=201,
)
def create_character_sheet(
    party_id: str,
    payload: CharacterSheetCreate,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = _require_party_member(party_id, user, session)
    existing = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Character sheet already exists")
    entry = CharacterSheet(
        id=str(uuid4()),
        party_id=party_id,
        player_user_id=user.id,
        data=payload.data,
    )
    session.add(entry)
    sync_character_sheet_inventory(
        party=party,
        player_user_id=user.id,
        sheet_data=payload.data,
        db=session,
    )
    session.commit()
    session.refresh(entry)
    return _to_read(entry)


@router.put("/parties/{party_id}/character-sheet/me", response_model=CharacterSheetRead)
def update_character_sheet(
    party_id: str,
    payload: CharacterSheetUpdate,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = _require_party_member(party_id, user, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")
    entry.data = payload.data
    session.add(entry)
    sync_character_sheet_inventory(
        party=party,
        player_user_id=user.id,
        sheet_data=payload.data,
        db=session,
        only_if_inventory_empty=True,
    )
    session.commit()
    session.refresh(entry)
    return _to_read(entry)


@router.delete("/parties/{party_id}/character-sheet/me", status_code=204)
def delete_character_sheet(
    party_id: str,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    _require_party_member(party_id, user, session)
    entry = session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id,
            CharacterSheet.player_user_id == user.id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Character sheet not found")
    session.delete(entry)
    session.commit()
