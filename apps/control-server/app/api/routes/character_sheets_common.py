from __future__ import annotations

from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.campaign import RoleMode
from app.models.campaign_spell import CampaignSpell
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
from app.services.centrifugo import centrifugo
from app.services.dragonborn_breath_weapon import apply_dragonborn_breath_weapon_canonical_state
from app.services.draconic_ancestry import (
    normalize_subclass_config,
    validate_draconic_subclass_state,
)
from app.services.guardian_progression import apply_guardian_canonical_state
from app.services.realtime import build_event, campaign_channel, event_version
from app.services.race_config import normalize_race_state, validate_race_state
from app.services.sorcerer_progression import apply_sorcerer_canonical_state

logger = logging.getLogger(__name__)


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
            PartyMember.role == RoleMode.PLAYER,
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
        sourceDraftId=entry.source_draft_id,
        deliveredByUserId=entry.delivered_by_user_id,
        deliveredAt=entry.delivered_at,
        acceptedAt=entry.accepted_at,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


async def publish_character_sheet_realtime(
    campaign_id: str,
    party_id_value: str,
    record: CharacterSheetRead,
    update_kind: str,
) -> None:
    await centrifugo.publish(
        campaign_channel(campaign_id),
        build_event(
            "character_sheet_updated",
            {
                "campaignId": campaign_id,
                "partyId": party_id_value,
                "playerUserId": record.playerId,
                "characterSheetId": record.id,
                "sourceDraftId": record.sourceDraftId,
                "deliveredAt": record.deliveredAt.isoformat() if record.deliveredAt else None,
                "acceptedAt": record.acceptedAt.isoformat() if record.acceptedAt else None,
                "updateKind": update_kind,
            },
            version=event_version(),
        ),
    )


async def publish_character_sheet_realtime_safe(
    campaign_id: str,
    party_id_value: str,
    record: CharacterSheetRead,
    update_kind: str,
) -> None:
    try:
        await publish_character_sheet_realtime(campaign_id, party_id_value, record, update_kind)
    except Exception:
        logger.exception(
            "Failed to publish character sheet realtime event",
            extra={
                "campaign_id": campaign_id,
                "party_id": party_id_value,
                "player_user_id": record.playerId,
                "character_sheet_id": record.id,
                "update_kind": update_kind,
            },
        )


def validate_character_sheet_payload(data: object) -> None:
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Character sheet payload must be an object")
    ok, error = validate_race_state(data)
    if not ok:
        raise HTTPException(status_code=422, detail=error)
    ok, error = validate_draconic_subclass_state(data)
    if not ok:
        raise HTTPException(status_code=422, detail=error)


def normalize_character_sheet_payload(data: object) -> dict:
    if not isinstance(data, dict):
        raise HTTPException(status_code=422, detail="Character sheet payload must be an object")
    normalized = normalize_race_state(data.get("race"), data.get("raceConfig"))
    subclass = data.get("subclass")
    next_data = {
        **data,
        "race": normalized["race"],
        "raceConfig": normalized["raceConfig"],
        "subclassConfig": normalize_subclass_config(subclass, data.get("subclassConfig")),
    }
    next_data = apply_guardian_canonical_state(next_data)
    next_data = apply_sorcerer_canonical_state(next_data)
    next_data = apply_dragonborn_breath_weapon_canonical_state(next_data)
    return next_data


def _find_campaign_spell_by_canonical_key(
    session: Session,
    campaign_id: str,
    canonical_key: str,
) -> CampaignSpell | None:
    return session.exec(
        select(CampaignSpell).where(
            CampaignSpell.campaign_id == campaign_id,
            CampaignSpell.canonical_key == canonical_key,
        )
    ).first()


def normalize_character_sheet_spell_references(
    data: dict,
    *,
    campaign_id: str,
    session: Session,
) -> dict:
    """Resolve and upgrade sheet spell entries to campaignSpellId.

    For each entry under data["spellcasting"]["spells"]:
      - if campaignSpellId already present and non-empty → keep (do not re-validate here)
      - elif canonicalKey resolves to a CampaignSpell in this campaign
        → set campaignSpellId (self-heal); log at debug
      - else leave untouched (legacy reads will still work via resolver fallbacks)

    Never drops canonicalKey or name — they remain as display/fallback fields.
    """
    spellcasting = data.get("spellcasting")
    if not isinstance(spellcasting, dict):
        return data
    spells = spellcasting.get("spells")
    if not isinstance(spells, list):
        return data

    healed_any = False
    next_spells = []
    for spell in spells:
        if not isinstance(spell, dict):
            next_spells.append(spell)
            continue

        existing_id = spell.get("campaignSpellId")
        if existing_id and isinstance(existing_id, str) and existing_id.strip():
            # Already has a campaignSpellId — leave untouched.
            next_spells.append(spell)
            continue

        canonical_key = spell.get("canonicalKey")
        if not canonical_key or not isinstance(canonical_key, str):
            next_spells.append(spell)
            continue

        campaign_spell = _find_campaign_spell_by_canonical_key(
            session, campaign_id, canonical_key
        )
        if campaign_spell is not None:
            logger.debug(
                "self-healing sheet spell entry: set campaignSpellId from canonicalKey",
                extra={"canonical_key": canonical_key, "campaign_spell_id": campaign_spell.id},
            )
            next_spells.append({**spell, "campaignSpellId": campaign_spell.id})
            healed_any = True
        else:
            next_spells.append(spell)

    if not healed_any:
        return data

    return {
        **data,
        "spellcasting": {**spellcasting, "spells": next_spells},
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
    normalized_payload = normalize_character_sheet_spell_references(
        normalized_payload, campaign_id=party.campaign_id, session=session
    )
    entry = CharacterSheet(
        id=str(uuid4()),
        party_id=party_id_value,
        player_user_id=current_user_id,
        data=normalized_payload,
        source_draft_id=None,
        delivered_by_user_id=None,
        delivered_at=None,
        accepted_at=utcnow(),
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
    if entry.accepted_at is not None:
        raise HTTPException(status_code=409, detail="Character sheet is already accepted")
    validate_character_sheet_payload(payload.data)
    normalized_payload = normalize_character_sheet_payload(payload.data)
    normalized_payload = normalize_character_sheet_spell_references(
        normalized_payload, campaign_id=party.campaign_id, session=session
    )
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


def accept_my_character_sheet_service(
    party_id_value: str,
    user: User,
    session: Session,
) -> CharacterSheetRead:
    require_party_member(party_id_value, user, session)
    entry = get_character_sheet_or_404(party_id_value, user_id(user), session)
    if entry.accepted_at is None:
        entry.accepted_at = utcnow()
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return to_character_sheet_read(entry)
