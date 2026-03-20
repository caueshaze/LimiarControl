from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from uuid import uuid4

from sqlmodel import Session, select

from app.models.base_item import BaseItem, BaseItemAlias
from app.models.campaign import Campaign, SystemType
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.models.party import Party
from app.services.campaign_catalog import _base_item_to_campaign_item

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
    base_item_id: str | None = None


@dataclass(frozen=True)
class _BaseCatalogIndex:
    by_id: dict[str, BaseItem]
    by_canonical_key: dict[str, BaseItem]
    by_lookup: dict[str, BaseItem]


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

    base_catalog = _load_base_catalog_index(campaign.system, db)
    campaign_items = db.exec(select(Item).where(Item.campaign_id == party.campaign_id)).all()
    items_by_base_item_id: dict[str, Item] = {}
    items_by_lookup: dict[str, Item] = {}
    item_keys_by_id: dict[str, str] = {}

    for item in campaign_items:
        _index_campaign_item(item, items_by_base_item_id, items_by_lookup, item_keys_by_id)

    existing_inventory_keys = {
        item_keys_by_id[entry.item_id]
        for entry in existing_inventory
        if entry.item_id in item_keys_by_id
    }

    for sheet_item in sheet_items:
        base_item = _resolve_base_item(sheet_item, base_catalog)
        if base_item:
            catalog_item = _ensure_campaign_item_for_base_item(
                campaign_id=party.campaign_id,
                base_item=base_item,
                db=db,
                items_by_base_item_id=items_by_base_item_id,
                items_by_lookup=items_by_lookup,
                item_keys_by_id=item_keys_by_id,
            )
        else:
            logger.warning(
                "Character-sheet starter item missing from base catalog; using fallback custom item.",
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
        base_item_id = _normalize_optional_string(
            raw_entry.get("baseItemId") or raw_entry.get("base_item_id")
        )
        weight = _to_float(raw_entry.get("weight"))

        merge_key = (
            f"base:{base_item_id}"
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
            base_item_id=base_item_id or (existing.base_item_id if existing else None),
        )

    return list(merged.values())


def _load_base_catalog_index(system_type: SystemType, db: Session) -> _BaseCatalogIndex:
    base_items = db.exec(
        select(BaseItem).where(
            BaseItem.system == system_type,
            BaseItem.is_active == True,  # noqa: E712
        )
    ).all()

    by_id = {item.id: item for item in base_items if item.id}
    by_canonical_key = {item.canonical_key: item for item in base_items}
    by_lookup: dict[str, BaseItem] = {}

    aliases = db.exec(
        select(BaseItemAlias).where(
            BaseItemAlias.base_item_id.in_(list(by_id.keys()))  # type: ignore[union-attr]
        )
    ).all()

    for item in base_items:
        for raw_lookup in (item.canonical_key, item.name_en, item.name_pt):
            lookup = _normalize_lookup(raw_lookup)
            if lookup and lookup not in by_lookup:
                by_lookup[lookup] = item

    for alias in aliases:
        item = by_id.get(alias.base_item_id)
        if not item:
            continue
        lookup = _normalize_lookup(alias.alias)
        if lookup and lookup not in by_lookup:
            by_lookup[lookup] = item

    for lookup, canonical_key in LEGACY_STARTER_CANONICAL_KEYS.items():
        item = by_canonical_key.get(canonical_key)
        if item:
            by_lookup.setdefault(lookup, item)

    return _BaseCatalogIndex(
        by_id=by_id,
        by_canonical_key=by_canonical_key,
        by_lookup=by_lookup,
    )


def _resolve_base_item(seed: _SheetInventorySeed, index: _BaseCatalogIndex) -> BaseItem | None:
    if seed.base_item_id:
        item = index.by_id.get(seed.base_item_id)
        if item:
            return item

    if seed.canonical_key:
        item = index.by_canonical_key.get(seed.canonical_key)
        if item:
            return item

    compatibility_key = LEGACY_STARTER_CANONICAL_KEYS.get(_normalize_lookup(seed.name))
    if compatibility_key:
        item = index.by_canonical_key.get(compatibility_key)
        if item:
            return item

    return index.by_lookup.get(_normalize_lookup(seed.name))


def _ensure_campaign_item_for_base_item(
    *,
    campaign_id: str,
    base_item: BaseItem,
    db: Session,
    items_by_base_item_id: dict[str, Item],
    items_by_lookup: dict[str, Item],
    item_keys_by_id: dict[str, str],
) -> Item:
    existing = items_by_base_item_id.get(base_item.id)
    if existing:
        return existing

    for lookup in (base_item.canonical_key, base_item.name_en, base_item.name_pt):
        matched = items_by_lookup.get(_normalize_lookup(lookup))
        if matched:
            _attach_base_item_metadata(matched, base_item)
            db.add(matched)
            db.flush()
            _index_campaign_item(matched, items_by_base_item_id, items_by_lookup, item_keys_by_id)
            return matched

    campaign_item = _base_item_to_campaign_item(base_item, campaign_id)
    db.add(campaign_item)
    db.flush()
    _index_campaign_item(campaign_item, items_by_base_item_id, items_by_lookup, item_keys_by_id)
    return campaign_item


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
        properties=[],
        is_custom=True,
        is_enabled=True,
    )
    db.add(item)
    db.flush()
    _index_campaign_item(item, {}, items_by_lookup, item_keys_by_id)
    return item


def _attach_base_item_metadata(item: Item, base_item: BaseItem) -> None:
    item.base_item_id = base_item.id
    item.canonical_key_snapshot = base_item.canonical_key
    item.name_en_snapshot = base_item.name_en
    item.name_pt_snapshot = base_item.name_pt
    item.item_kind = base_item.item_kind
    item.cost_unit = base_item.cost_unit
    item.is_custom = False


def _index_campaign_item(
    item: Item,
    items_by_base_item_id: dict[str, Item],
    items_by_lookup: dict[str, Item],
    item_keys_by_id: dict[str, str],
) -> None:
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
