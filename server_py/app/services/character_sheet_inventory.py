from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session, select

from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.models.party import Party

_BASE_DIR = Path(__file__).resolve().parents[3] / "Base"
_COIN_TO_GP = {
    "cp": 0.01,
    "sp": 0.1,
    "ep": 0.5,
    "gp": 1.0,
    "pp": 10.0,
}


@dataclass(frozen=True)
class _CatalogSeed:
    name: str
    item_type: ItemType
    description: str
    price: float | None = None
    weight: float | None = None
    damage_dice: str | None = None
    range_meters: float | None = None
    properties: tuple[str, ...] = ()


@dataclass(frozen=True)
class _SheetInventorySeed:
    name: str
    quantity: int
    weight: float | None = None
    notes: str | None = None


def sync_character_sheet_inventory(
    *,
    party: Party,
    player_user_id: str,
    sheet_data: dict,
    db: Session,
    only_if_inventory_empty: bool = False,
) -> None:
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

    campaign_items = db.exec(
        select(Item).where(Item.campaign_id == party.campaign_id)
    ).all()
    items_by_key = {_normalize_name(item.name): item for item in campaign_items}
    item_names_by_id = {item.id: _normalize_name(item.name) for item in campaign_items if item.id}
    existing_inventory_keys = {
        item_names_by_id[entry.item_id]
        for entry in existing_inventory
        if entry.item_id in item_names_by_id
    }

    for sheet_item in sheet_items:
        item_key = _normalize_name(sheet_item.name)
        if not item_key or item_key in existing_inventory_keys:
            continue

        catalog_item = items_by_key.get(item_key)
        if not catalog_item:
            catalog_item = _create_catalog_item(
                campaign_id=party.campaign_id,
                seed=sheet_item,
                db=db,
            )
            items_by_key[item_key] = catalog_item

        db.add(
            InventoryItem(
                id=str(uuid4()),
                campaign_id=party.campaign_id,
                party_id=party.id,
                member_id=campaign_member.id,
                item_id=catalog_item.id,
                quantity=sheet_item.quantity,
                is_equipped=False,
                notes=sheet_item.notes or "Starting equipment",
            )
        )
        existing_inventory_keys.add(item_key)


def _create_catalog_item(*, campaign_id: str, seed: _SheetInventorySeed, db: Session) -> Item:
    catalog_seed = _load_base_catalog().get(_normalize_name(seed.name))
    item = Item(
        id=str(uuid4()),
        campaign_id=campaign_id,
        name=catalog_seed.name if catalog_seed else seed.name.strip(),
        type=catalog_seed.item_type if catalog_seed else ItemType.MISC,
        description=(
            catalog_seed.description
            if catalog_seed
            else "Starting equipment imported from character sheet."
        ),
        price=catalog_seed.price if catalog_seed else None,
        weight=(
            catalog_seed.weight
            if catalog_seed and catalog_seed.weight is not None
            else seed.weight
        ),
        damage_dice=catalog_seed.damage_dice if catalog_seed else None,
        range_meters=catalog_seed.range_meters if catalog_seed else None,
        properties=list(catalog_seed.properties) if catalog_seed else [],
    )
    db.add(item)
    db.flush()
    return item


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
        weight = _to_float(raw_entry.get("weight"))
        notes = raw_entry.get("notes")
        normalized_notes = notes.strip() if isinstance(notes, str) and notes.strip() else None
        key = _normalize_name(name)
        existing = merged.get(key)
        merged[key] = _SheetInventorySeed(
            name=name,
            quantity=quantity + (existing.quantity if existing else 0),
            weight=weight if weight is not None else (existing.weight if existing else None),
            notes=normalized_notes or (existing.notes if existing else None),
        )
    return list(merged.values())


@lru_cache(maxsize=1)
def _load_base_catalog() -> dict[str, _CatalogSeed]:
    catalog: dict[str, _CatalogSeed] = {}

    weapons_path = _BASE_DIR / "DND5e_Armas_Database_Programador.csv"
    with weapons_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = str(row.get("Nome", "")).strip()
            if not name:
                continue
            catalog[_normalize_name(name)] = _CatalogSeed(
                name=name,
                item_type=ItemType.WEAPON,
                description=str(row.get("Descrição curta", "")).strip() or "Weapon",
                price=_parse_price_gp(row.get("Custo")),
                weight=_parse_weight(row.get("Peso")),
                damage_dice=_clean_value(row.get("Dano")),
                range_meters=_feet_to_meters(_to_float(row.get("Alcance normal"))),
                properties=tuple(_split_properties(row.get("Propriedades"))),
            )

    armors_path = _BASE_DIR / "DND5e_Armaduras_Database.csv"
    with armors_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = str(row.get("Nome", "")).strip()
            if not name:
                continue
            properties = []
            base_ac = _to_int(row.get("CA base"), default=0)
            if base_ac > 0:
                properties.append(f"Base AC {base_ac}")
            category = str(row.get("Categoria", "")).strip()
            if category:
                properties.append(f"Categoria {category}")
            dex_cap = _clean_value(row.get("Mod DEX máximo"))
            if dex_cap and dex_cap.lower() not in {"n/a", "ilimitado"}:
                properties.append(f"DEX max {dex_cap}")
            if str(row.get("Desvantagem em furtividade", "")).strip().lower() == "sim":
                properties.append("Stealth disadvantage")
            catalog[_normalize_name(name)] = _CatalogSeed(
                name=name,
                item_type=ItemType.ARMOR,
                description=str(row.get("Descrição", "")).strip() or "Armor",
                price=_parse_price_gp(row.get("Custo")),
                weight=_parse_weight(row.get("Peso")),
                properties=tuple(properties),
            )

    equipment_path = _BASE_DIR / "DND5e_Equipamentos.json"
    data = json.loads(equipment_path.read_text(encoding="utf-8"))
    for raw_entry in data:
        if not isinstance(raw_entry, dict):
            continue
        name = str(raw_entry.get("name", "")).strip()
        if not name:
            continue
        description = raw_entry.get("desc")
        catalog.setdefault(
            _normalize_name(name),
            _CatalogSeed(
                name=name,
                item_type=ItemType.MISC,
                description=(
                    " ".join(str(part).strip() for part in description if str(part).strip())
                    if isinstance(description, list)
                    else str(description).strip() or "Equipment"
                ),
                price=_parse_json_cost(raw_entry.get("cost")),
                weight=_to_float(raw_entry.get("weight")),
                properties=tuple(
                    str(part).strip()
                    for part in raw_entry.get("properties", [])
                    if str(part).strip()
                ),
            ),
        )

    return catalog


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


def _clean_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or normalized == "-":
        return None
    return normalized


def _split_properties(value: object) -> list[str]:
    if not isinstance(value, str):
        return []
    return [part.strip() for part in value.split(",") if part.strip() and part.strip() != "-"]


def _parse_price_gp(raw_value: object) -> float | None:
    if not isinstance(raw_value, str):
        return None
    match = re.match(r"^\s*([\d.,]+)\s*(cp|sp|ep|gp|pp)\s*$", raw_value, flags=re.IGNORECASE)
    if not match:
        return None
    amount = _to_float(match.group(1))
    unit = match.group(2).lower()
    if amount is None:
        return None
    return round(amount * _COIN_TO_GP[unit], 2)


def _parse_json_cost(raw_cost: object) -> float | None:
    if not isinstance(raw_cost, dict):
        return None
    amount = _to_float(raw_cost.get("quantity"))
    unit = str(raw_cost.get("unit", "")).strip().lower()
    if amount is None or unit not in _COIN_TO_GP:
        return None
    return round(amount * _COIN_TO_GP[unit], 2)


def _parse_weight(raw_value: object) -> float | None:
    if not isinstance(raw_value, str):
        return None
    match = re.search(r"[\d.,]+", raw_value)
    if not match:
        return None
    return _to_float(match.group(0))


def _feet_to_meters(feet: float | None) -> float | None:
    if feet is None or feet <= 5:
        return None
    return float(max(1, round(feet * 0.3048)))


def _to_int(value: object, *, default: int = 0) -> int:
    try:
        parsed = int(float(str(value)))
    except (TypeError, ValueError):
        return default
    return parsed


def _to_float(value: object) -> float | None:
    try:
        parsed = float(str(value).replace(",", "."))
    except (AttributeError, TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed
