from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unicodedata
from uuid import uuid4

from sqlmodel import Session, select

from app.models.campaign import SystemType
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.session import Session as CampaignSession
from app.services.campaign_catalog import ensure_campaign_catalog_item_for_base_canonical_key
from app.services.inventory_expiration import normalize_inventory_timestamp
from app.services.magic_item_effects import initialize_inventory_item_charges, inventory_item_supports_stacking


def _normalize_lookup(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return " ".join(normalized.replace("_", " ").replace("-", " ").split())


def _get_campaign_member(
    db: Session,
    *,
    campaign_id: str,
    player_user_id: str,
) -> CampaignMember | None:
    return db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == player_user_id,
        )
    ).first()


def grant_catalog_item_to_player_inventory(
    db: Session,
    *,
    session_entry: CampaignSession,
    player_user_id: str,
    system: SystemType,
    canonical_key: str,
    quantity: int,
    notes: str | None = None,
    expires_at: datetime | None = None,
    source_spell_canonical_key: str | None = None,
) -> InventoryItem:
    member = _get_campaign_member(
        db,
        campaign_id=session_entry.campaign_id,
        player_user_id=player_user_id,
    )
    if not member or not member.id:
        raise ValueError("Campaign member not found for inventory grant.")

    campaign_item = ensure_campaign_catalog_item_for_base_canonical_key(
        db=db,
        campaign_id=session_entry.campaign_id,
        system=system,
        canonical_key=canonical_key,
        commit=False,
    )

    entry = None
    if expires_at is None and not source_spell_canonical_key and inventory_item_supports_stacking(campaign_item):
        entry = db.exec(
            select(InventoryItem).where(
                InventoryItem.campaign_id == session_entry.campaign_id,
                InventoryItem.party_id == session_entry.party_id,
                InventoryItem.member_id == member.id,
                InventoryItem.item_id == campaign_item.id,
            )
        ).first()

    if entry:
        entry.quantity = max(0, int(entry.quantity or 0)) + max(0, quantity)
        if notes and not (entry.notes or "").strip():
            entry.notes = notes
        entry.updated_at = datetime.now(timezone.utc)
        db.add(entry)
        db.flush()
        return entry

    created = InventoryItem(
        id=str(uuid4()),
        campaign_id=session_entry.campaign_id,
        party_id=session_entry.party_id,
        member_id=member.id,
        item_id=campaign_item.id,
        quantity=max(0, quantity),
        charges_current=campaign_item.charges_max if isinstance(campaign_item.charges_max, int) and campaign_item.charges_max > 0 else None,
        is_equipped=False,
        notes=notes or "Granted by spell",
        source_spell_canonical_key=source_spell_canonical_key,
        expires_at=normalize_inventory_timestamp(expires_at),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    initialize_inventory_item_charges(created, campaign_item)
    db.add(created)
    db.flush()
    return created


def build_goodberry_expiration(*, created_at: datetime | None = None) -> datetime:
    reference = normalize_inventory_timestamp(created_at) or datetime.now(timezone.utc)
    return reference + timedelta(hours=24)


def remove_catalog_item_from_player_inventory(
    db: Session,
    *,
    campaign_id: str,
    party_id: str | None,
    player_user_id: str,
    canonical_key: str,
) -> int:
    member = _get_campaign_member(
        db,
        campaign_id=campaign_id,
        player_user_id=player_user_id,
    )
    if not member or not member.id:
        return 0

    items = db.exec(
        select(Item).where(
            Item.campaign_id == campaign_id,
            Item.canonical_key_snapshot == canonical_key,
        )
    ).all()
    if not items:
        return 0

    item_ids = {item.id for item in items if item.id}
    if not item_ids:
        return 0

    inventory_entries = db.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == campaign_id,
            InventoryItem.member_id == member.id,
            InventoryItem.item_id.in_(item_ids),
        )
    ).all()

    removed = 0
    for entry in inventory_entries:
        if party_id is not None and entry.party_id not in (None, party_id):
            continue
        db.delete(entry)
        removed += 1
    if removed > 0:
        db.flush()
    return removed


def strip_catalog_item_from_state_inventory(
    data: dict | None,
    *,
    canonical_key: str,
    fallback_names: tuple[str, ...] = (),
) -> dict:
    next_data = dict(data) if isinstance(data, dict) else {}
    raw_inventory = next_data.get("inventory")
    if not isinstance(raw_inventory, list):
        return next_data

    normalized_key = _normalize_lookup(canonical_key)
    normalized_names = {normalized_key, *(_normalize_lookup(name) for name in fallback_names)}

    filtered_inventory = []
    for raw_entry in raw_inventory:
        if not isinstance(raw_entry, dict):
            filtered_inventory.append(raw_entry)
            continue
        entry_key = _normalize_lookup(
            raw_entry.get("canonicalKey")
            or raw_entry.get("canonical_key")
            or raw_entry.get("name")
        )
        if entry_key in normalized_names:
            continue
        filtered_inventory.append(raw_entry)

    next_data["inventory"] = filtered_inventory
    return next_data
