from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from uuid import uuid4

from sqlmodel import Session, select

from app.models.campaign import Campaign
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.models.party import Party

logger = logging.getLogger(__name__)

LEGACY_STARTER_CANONICAL_KEYS: dict[str, str] = {
    "leather armor": "leather",
    "studded leather armor": "studded_leather",
    "hide armor": "hide",
    "wooden shield": "shield",
}


@dataclass(frozen=True)
class _SheetInventorySeed:
    name: str
    quantity: int
    weight: float | None = None
    notes: str | None = None
    canonical_key: str | None = None
    campaign_item_id: str | None = None
    base_item_id: str | None = None
def sync_character_sheet_inventory(
    *,
    party: Party,
    player_user_id: str,
    sheet_data: dict,
    db: Session,
    only_if_inventory_empty: bool = False,
) -> None:
    campaign = db.exec(select(Campaign).where(Campaign.id == party.campaign_id)).first()
    if not campaign:
        return

    campaign_member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == party.campaign_id,
            CampaignMember.user_id == player_user_id,
        )
    ).first()
    if not campaign_member or not isinstance(sheet_data, dict):
        return

    sheet_items = _extract_sheet_inventory(sheet_data.get("inventory"))
    if not sheet_items:
        return

    existing_inventory = db.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == party.campaign_id,
            InventoryItem.party_id == party.id,
            InventoryItem.member_id == campaign_member.id,
        )
    ).all()
    if only_if_inventory_empty and existing_inventory:
        return

    campaign_items = db.exec(select(Item).where(Item.campaign_id == party.campaign_id)).all()
    items_by_id: dict[str, Item] = {}
    items_by_base_item_id: dict[str, Item] = {}
    items_by_lookup: dict[str, Item] = {}
    item_keys_by_id: dict[str, str] = {}

    for item in campaign_items:
        _index_campaign_item(item, items_by_id, items_by_base_item_id, items_by_lookup, item_keys_by_id)

    existing_inventory_keys = {
        item_keys_by_id[entry.item_id]
        for entry in existing_inventory
        if entry.item_id in item_keys_by_id
    }

    for sheet_item in sheet_items:
        catalog_item = _resolve_campaign_item(
            seed=sheet_item,
            items_by_id=items_by_id,
            items_by_base_item_id=items_by_base_item_id,
            items_by_lookup=items_by_lookup,
        )
        if not catalog_item:
            logger.warning(
                "Character-sheet starter item missing from campaign catalog snapshot; using fallback custom item.",
                extra={
                    "campaign_id": party.campaign_id,
                    "party_id": party.id,
                    "item_name": sheet_item.name,
                    "canonical_key": sheet_item.canonical_key,
                },
            )
            catalog_item = _ensure_fallback_campaign_item(
                campaign_id=party.campaign_id,
                seed=sheet_item,
                db=db,
                items_by_lookup=items_by_lookup,
                item_keys_by_id=item_keys_by_id,
            )

        item_key = _campaign_item_key(catalog_item)
        if not item_key or item_key in existing_inventory_keys:
            continue

        db.add(
            InventoryItem(  # type: ignore[call-arg]
                id=str(uuid4()),
                campaign_id=party.campaign_id,
                party_id=party.id,
                member_id=campaign_member.id,
                item_id=catalog_item.id,
                quantity=sheet_item.quantity,
                is_equipped=False,
                notes=sheet_item.notes or "Equipamento inicial",
            )
        )
        existing_inventory_keys.add(item_key)


def _extract_sheet_inventory(raw_inventory: object) -> list[_SheetInventorySeed]:
    if not isinstance(raw_inventory, list):
        return []

    merged: dict[str, _SheetInventorySeed] = {}
    for raw_entry in raw_inventory:
        if not isinstance(raw_entry, dict):
            continue

        name = str(raw_entry.get("name", "")).strip()
        if not name:
            continue

        quantity = _to_int(raw_entry.get("quantity"), default=1)
        if quantity < 1:
            continue

        notes = raw_entry.get("notes")
        normalized_notes = notes.strip() if isinstance(notes, str) and notes.strip() else None
        canonical_key = _normalize_canonical_key(
            raw_entry.get("canonicalKey") or raw_entry.get("canonical_key")
        )
        campaign_item_id = _normalize_optional_string(
            raw_entry.get("campaignItemId") or raw_entry.get("campaign_item_id")
        )
        base_item_id = _normalize_optional_string(
            raw_entry.get("baseItemId") or raw_entry.get("base_item_id")
        )
        weight = _to_float(raw_entry.get("weight"))

        merge_key = (
            f"campaign:{campaign_item_id}"
            if campaign_item_id
            else f"base:{base_item_id}"
            if base_item_id
            else f"canonical:{canonical_key}"
            if canonical_key
            else f"name:{_normalize_lookup(name)}"
        )
        existing = merged.get(merge_key)
        merged[merge_key] = _SheetInventorySeed(
            name=name,
            quantity=quantity + (existing.quantity if existing else 0),
            weight=weight if weight is not None else (existing.weight if existing else None),
            notes=normalized_notes or (existing.notes if existing else None),
            canonical_key=canonical_key or (existing.canonical_key if existing else None),
            campaign_item_id=campaign_item_id or (existing.campaign_item_id if existing else None),
            base_item_id=base_item_id or (existing.base_item_id if existing else None),
        )

    return list(merged.values())


def _resolve_campaign_item(
    *,
    seed: _SheetInventorySeed,
    items_by_id: dict[str, Item],
    items_by_base_item_id: dict[str, Item],
    items_by_lookup: dict[str, Item],
) -> Item | None:
    if seed.campaign_item_id:
        item = items_by_id.get(seed.campaign_item_id)
        if item:
            return item

    if seed.base_item_id:
        item = items_by_base_item_id.get(seed.base_item_id)
        if item:
            return item

    if seed.canonical_key:
        item = items_by_lookup.get(_normalize_lookup(seed.canonical_key))
        if item:
            return item

    compatibility_key = LEGACY_STARTER_CANONICAL_KEYS.get(_normalize_lookup(seed.name))
    if compatibility_key:
        item = items_by_lookup.get(_normalize_lookup(compatibility_key))
        if item:
            return item

    return items_by_lookup.get(_normalize_lookup(seed.name))


def _ensure_fallback_campaign_item(
    *,
    campaign_id: str,
    seed: _SheetInventorySeed,
    db: Session,
    items_by_lookup: dict[str, Item],
    item_keys_by_id: dict[str, str],
) -> Item:
    existing = items_by_lookup.get(_normalize_lookup(seed.name))
    if existing:
        return existing

    item = Item(  # type: ignore[call-arg]
        id=str(uuid4()),
        campaign_id=campaign_id,
        name=seed.name,
        type=ItemType.MISC,
        description="Item temporário materializado da ficha; catálogo base ainda não possui correspondência.",
        price=None,
        weight=seed.weight,
        damage_dice=None,
        range_meters=None,
        canonical_key_snapshot=seed.canonical_key,
        name_en_snapshot=seed.name,
        name_pt_snapshot=seed.name,
        properties=[],
        is_custom=True,
        is_enabled=True,
    )
    db.add(item)
    db.flush()
    _index_campaign_item(item, {}, {}, items_by_lookup, item_keys_by_id)
    return item


def _index_campaign_item(
    item: Item,
    items_by_id: dict[str, Item],
    items_by_base_item_id: dict[str, Item],
    items_by_lookup: dict[str, Item],
    item_keys_by_id: dict[str, str],
) -> None:
    if item.id:
        items_by_id[item.id] = item

    if item.base_item_id:
        items_by_base_item_id[item.base_item_id] = item

    for lookup in (
        item.name,
        item.canonical_key_snapshot,
        item.name_en_snapshot,
        item.name_pt_snapshot,
    ):
        key = _normalize_lookup(lookup)
        if key and key not in items_by_lookup:
            items_by_lookup[key] = item

    if item.id:
        item_keys_by_id[item.id] = _campaign_item_key(item)


def _campaign_item_key(item: Item) -> str:
    if item.base_item_id:
        return f"base:{item.base_item_id}"
    if item.canonical_key_snapshot:
        return f"canonical:{item.canonical_key_snapshot}"
    return f"name:{_normalize_lookup(item.name)}"


def _normalize_lookup(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


def _normalize_canonical_key(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", "_", ascii_only.lower()).strip("_")
    return cleaned or None


def _normalize_optional_string(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _to_int(value: object, *, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _to_float(value: object) -> float | None:
    try:
        parsed = float(str(value).replace(",", "."))
    except (AttributeError, TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed
