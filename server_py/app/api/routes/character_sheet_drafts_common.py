from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.api.routes.character_sheets_common import (
    get_character_sheet,
    get_party_with_gm_check,
    normalize_character_sheet_payload,
    require_joined_player,
    to_character_sheet_read,
    user_id,
    validate_character_sheet_payload,
    utcnow,
)
from app.models.character_sheet import CharacterSheet
from app.models.party_character_sheet_draft import (
    PartyCharacterSheetDraft,
    PartyCharacterSheetDraftStatus,
)
from app.models.user import User
from app.schemas.character_sheet import CharacterSheetRead
from app.schemas.character_sheet_draft import (
    PartyCharacterSheetDraftCreate,
    PartyCharacterSheetDraftDeriveRequest,
    PartyCharacterSheetDraftRead,
    PartyCharacterSheetDraftUpdate,
)
from app.services.character_sheet_inventory import sync_character_sheet_inventory


def _normalize_draft_name(name: str) -> str:
    return name.strip() or "Untitled Draft"


def to_party_character_sheet_draft_read(
    entry: PartyCharacterSheetDraft,
) -> PartyCharacterSheetDraftRead:
    return PartyCharacterSheetDraftRead(
        id=entry.id,
        partyId=entry.party_id,
        name=entry.name,
        data=entry.data,
        status=entry.status.value,
        createdByUserId=entry.created_by_user_id,
        archivedAt=entry.archived_at,
        lastDerivedAt=entry.last_derived_at,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def get_party_character_sheet_draft(
    party_id_value: str,
    draft_id: str,
    session: Session,
) -> PartyCharacterSheetDraft | None:
    return session.exec(
        select(PartyCharacterSheetDraft).where(
            PartyCharacterSheetDraft.party_id == party_id_value,
            PartyCharacterSheetDraft.id == draft_id,
        )
    ).first()


def get_party_character_sheet_draft_or_404(
    party_id_value: str,
    draft_id: str,
    session: Session,
) -> PartyCharacterSheetDraft:
    entry = get_party_character_sheet_draft(party_id_value, draft_id, session)
    if entry is None:
        raise HTTPException(status_code=404, detail="Character sheet draft not found")
    return entry


def list_party_character_sheet_drafts_service(
    party_id_value: str,
    user: User,
    session: Session,
) -> list[PartyCharacterSheetDraftRead]:
    get_party_with_gm_check(party_id_value, user, session)
    entries = session.exec(
        select(PartyCharacterSheetDraft).where(
            PartyCharacterSheetDraft.party_id == party_id_value,
        )
    ).all()
    ordered_entries = sorted(
        entries,
        key=lambda entry: (
            entry.status != PartyCharacterSheetDraftStatus.ACTIVE,
            -(entry.updated_at or entry.created_at).timestamp(),
        ),
    )
    return [to_party_character_sheet_draft_read(entry) for entry in ordered_entries]


def create_party_character_sheet_draft_service(
    party_id_value: str,
    payload: PartyCharacterSheetDraftCreate,
    user: User,
    session: Session,
) -> PartyCharacterSheetDraftRead:
    get_party_with_gm_check(party_id_value, user, session)
    validate_character_sheet_payload(payload.data)
    entry = PartyCharacterSheetDraft(
        id=str(uuid4()),
        party_id=party_id_value,
        name=_normalize_draft_name(payload.name),
        data=normalize_character_sheet_payload(payload.data),
        status=PartyCharacterSheetDraftStatus.ACTIVE,
        created_by_user_id=user_id(user),
        archived_at=None,
        last_derived_at=None,
        created_at=utcnow(),
        updated_at=None,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_party_character_sheet_draft_read(entry)


def get_party_character_sheet_draft_service(
    party_id_value: str,
    draft_id: str,
    user: User,
    session: Session,
) -> PartyCharacterSheetDraftRead:
    get_party_with_gm_check(party_id_value, user, session)
    return to_party_character_sheet_draft_read(
        get_party_character_sheet_draft_or_404(party_id_value, draft_id, session)
    )


def update_party_character_sheet_draft_service(
    party_id_value: str,
    draft_id: str,
    payload: PartyCharacterSheetDraftUpdate,
    user: User,
    session: Session,
) -> PartyCharacterSheetDraftRead:
    get_party_with_gm_check(party_id_value, user, session)
    entry = get_party_character_sheet_draft_or_404(party_id_value, draft_id, session)
    if entry.status != PartyCharacterSheetDraftStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Character sheet draft is archived")
    validate_character_sheet_payload(payload.data)
    entry.name = _normalize_draft_name(payload.name)
    entry.data = normalize_character_sheet_payload(payload.data)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_party_character_sheet_draft_read(entry)


def archive_party_character_sheet_draft_service(
    party_id_value: str,
    draft_id: str,
    user: User,
    session: Session,
) -> PartyCharacterSheetDraftRead:
    get_party_with_gm_check(party_id_value, user, session)
    entry = get_party_character_sheet_draft_or_404(party_id_value, draft_id, session)
    if entry.status != PartyCharacterSheetDraftStatus.ARCHIVED:
        entry.status = PartyCharacterSheetDraftStatus.ARCHIVED
        entry.archived_at = utcnow()
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return to_party_character_sheet_draft_read(entry)


def restore_party_character_sheet_draft_service(
    party_id_value: str,
    draft_id: str,
    user: User,
    session: Session,
) -> PartyCharacterSheetDraftRead:
    get_party_with_gm_check(party_id_value, user, session)
    entry = get_party_character_sheet_draft_or_404(party_id_value, draft_id, session)
    if entry.status != PartyCharacterSheetDraftStatus.ACTIVE:
        entry.status = PartyCharacterSheetDraftStatus.ACTIVE
        entry.archived_at = None
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return to_party_character_sheet_draft_read(entry)


def delete_party_character_sheet_draft_service(
    party_id_value: str,
    draft_id: str,
    user: User,
    session: Session,
) -> None:
    get_party_with_gm_check(party_id_value, user, session)
    entry = get_party_character_sheet_draft_or_404(party_id_value, draft_id, session)
    session.delete(entry)
    session.commit()


def derive_party_character_sheet_draft_service(
    party_id_value: str,
    draft_id: str,
    payload: PartyCharacterSheetDraftDeriveRequest,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    party = get_party_with_gm_check(party_id_value, user, session)
    entry = get_party_character_sheet_draft_or_404(party_id_value, draft_id, session)
    if entry.status != PartyCharacterSheetDraftStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Character sheet draft is archived")

    require_joined_player(party_id_value, payload.playerUserId, session)
    if get_character_sheet(party_id_value, payload.playerUserId, session) is not None:
        raise HTTPException(status_code=409, detail="Character sheet already exists")

    validate_character_sheet_payload(entry.data)
    normalized_payload = normalize_character_sheet_payload(entry.data)
    now = utcnow()
    sheet_entry = CharacterSheet(
        id=str(uuid4()),
        party_id=party_id_value,
        player_user_id=payload.playerUserId,
        data=normalized_payload,
        source_draft_id=entry.id,
        delivered_by_user_id=user_id(user),
        delivered_at=now,
        accepted_at=None,
        created_at=now,
        updated_at=None,
    )
    session.add(sheet_entry)
    sync_character_sheet_inventory(
        party=party,
        player_user_id=payload.playerUserId,
        sheet_data=normalized_payload,
        db=session,
    )

    entry.status = PartyCharacterSheetDraftStatus.ARCHIVED
    entry.archived_at = now
    entry.last_derived_at = now
    session.add(entry)

    session.commit()
    session.refresh(sheet_entry)
    return to_character_sheet_read(sheet_entry)
