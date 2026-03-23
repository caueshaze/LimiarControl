from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.character_sheet import CharacterSheet
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.user import User
from app.schemas.character_sheet import (
    CharacterSheetCreate,
    CharacterSheetRead,
    CharacterSheetUpdate,
)
from app.services.character_sheet_inventory import sync_character_sheet_inventory
from app.services.race_config import normalize_race_state, validate_race_state


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def require_identifier(value: str | None, detail: str) -> str:
    if value is None:
        raise HTTPException(status_code=500, detail=detail)
    return value


def user_id(user: User) -> str:
    return require_identifier(user.id, "Authenticated user is missing an id")


def party_id(party: Party) -> str:
    return require_identifier(party.id, "Party is missing an id")


def get_party_or_404(party_id_value: str, session: Session) -> Party:
    party = session.get(Party, party_id_value)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")
    return party


def require_party_member(
    party_id_value: str,
    user: User,
    session: Session,
) -> Party:
    party = get_party_or_404(party_id_value, session)
    current_user_id = user_id(user)
    if party.gm_user_id == current_user_id:
        return party
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id_value,
            PartyMember.user_id == current_user_id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).first()
    if member is None:
        raise HTTPException(status_code=403, detail="Not a party member")
    return party


def get_party_with_gm_check(
    party_id_value: str,
    user: User,
    session: Session,
) -> Party:
    party = get_party_or_404(party_id_value, session)
    if party.gm_user_id != user_id(user):
        raise HTTPException(status_code=403, detail="GM required")
    return party


def require_joined_player(
    party_id_value: str,
    player_user_id: str,
    session: Session,
) -> None:
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id_value,
            PartyMember.user_id == player_user_id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Player not found in party")


def get_character_sheet(
    party_id_value: str,
    player_user_id: str,
    session: Session,
) -> CharacterSheet | None:
    return session.exec(
        select(CharacterSheet).where(
            CharacterSheet.party_id == party_id_value,
            CharacterSheet.player_user_id == player_user_id,
        )
    ).first()


def get_character_sheet_or_404(
    party_id_value: str,
    player_user_id: str,
    session: Session,
) -> CharacterSheet:
    entry = get_character_sheet(party_id_value, player_user_id, session)
    if entry is None:
        raise HTTPException(status_code=404, detail="Character sheet not found")
    return entry


def to_character_sheet_read(entry: CharacterSheet) -> CharacterSheetRead:
    return CharacterSheetRead(
        id=entry.id,
        partyId=entry.party_id,
        playerId=entry.player_user_id,
        data=entry.data,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def validate_character_sheet_payload(data: object) -> None:
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Character sheet payload must be an object")
    ok, error = validate_race_state(data)
    if not ok:
        raise HTTPException(status_code=422, detail=error)


def normalize_character_sheet_payload(data: object) -> dict:
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Character sheet payload must be an object")
    normalized = normalize_race_state(data.get("race"), data.get("raceConfig"))
    return {
        **data,
        "race": normalized["race"],
        "raceConfig": normalized["raceConfig"],
    }


def get_my_character_sheet_service(
    party_id_value: str,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    require_party_member(party_id_value, user, session)
    entry = get_character_sheet_or_404(party_id_value, user_id(user), session)
    return to_character_sheet_read(entry)


def get_party_character_sheet_service(
    party_id_value: str,
    player_user_id: str,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    get_party_with_gm_check(party_id_value, user, session)
    entry = get_character_sheet_or_404(party_id_value, player_user_id, session)
    return to_character_sheet_read(entry)


def create_character_sheet_service(
    party_id_value: str,
    payload: CharacterSheetCreate,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    party = require_party_member(party_id_value, user, session)
    current_user_id = user_id(user)
    existing = get_character_sheet(party_id_value, current_user_id, session)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Character sheet already exists")

    validate_character_sheet_payload(payload.data)
    normalized_payload = normalize_character_sheet_payload(payload.data)
    entry = CharacterSheet(
        id=str(uuid4()),
        party_id=party_id_value,
        player_user_id=current_user_id,
        data=normalized_payload,
        created_at=utcnow(),
        updated_at=None,
    )
    session.add(entry)
    sync_character_sheet_inventory(
        party=party,
        player_user_id=current_user_id,
        sheet_data=normalized_payload,
        db=session,
    )
    session.commit()
    session.refresh(entry)
    return to_character_sheet_read(entry)


def update_character_sheet_service(
    party_id_value: str,
    payload: CharacterSheetUpdate,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    party = require_party_member(party_id_value, user, session)
    current_user_id = user_id(user)
    entry = get_character_sheet_or_404(party_id_value, current_user_id, session)
    validate_character_sheet_payload(payload.data)
    normalized_payload = normalize_character_sheet_payload(payload.data)
    entry.data = normalized_payload
    session.add(entry)
    sync_character_sheet_inventory(
        party=party,
        player_user_id=current_user_id,
        sheet_data=normalized_payload,
        db=session,
        only_if_inventory_empty=True,
    )
    session.commit()
    session.refresh(entry)
    return to_character_sheet_read(entry)


def delete_character_sheet_service(
    party_id_value: str,
    user: User,
    session: Session,
) -> None:
    require_party_member(party_id_value, user, session)
    entry = get_character_sheet_or_404(party_id_value, user_id(user), session)
    session.delete(entry)
    session.commit()
