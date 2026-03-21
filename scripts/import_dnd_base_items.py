#!/usr/bin/env python3
"""Import D&D 5e base items (weapons, armors, gear) from CSV files into the database.

Source of truth: CSV files in Base/ directory.
  - DND5e_Armas_Database_Programador.csv  (weapons)
  - DND5e_Armaduras_Database.csv           (armors)
  - DND5e_Equipamentos_Database.csv        (gear, tools, packs, etc.)

Each CSV must include a `canonical_key` column used as the unique item identifier.
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "server_py"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.base_item import (
    BaseItem,
    BaseItemArmorCategory,
    BaseItemCostUnit,
    BaseItemKind,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.campaign import SystemType

LOGGER = logging.getLogger("import_dnd_base_items")

WEAPONS_CSV_PATH = REPO_ROOT / "Base" / "DND5e_Armas_Database_Programador.csv"
ARMORS_CSV_PATH = REPO_ROOT / "Base" / "DND5e_Armaduras_Database.csv"
GEAR_CSV_PATH = REPO_ROOT / "Base" / "DND5e_Equipamentos_Database.csv"
SYSTEM = SystemType.DND5E

# ── PT value mappings (CSV columns use PT labels for categories/types) ──

DAMAGE_TYPE_BY_PT: dict[str, str] = {
    "contundente": "bludgeoning",
    "cortante": "slashing",
    "perfurante": "piercing",
}

PROPERTY_BY_PT: dict[str, str] = {
    "alcance": "reach",
    "arremesso": "thrown",
    "carregamento": "loading",
    "duas maos": "two-handed",
    "especial": "special",
    "fineza": "finesse",
    "lancavel": "thrown",
    "leve": "light",
    "municao": "ammunition",
    "pesada": "heavy",
    "versatil": "versatile",
}

WEAPON_CATEGORY_BY_PT: dict[str, BaseItemWeaponCategory] = {
    "simples": BaseItemWeaponCategory.SIMPLE,
    "marcial": BaseItemWeaponCategory.MARTIAL,
}

WEAPON_RANGE_TYPE_BY_PT: dict[str, BaseItemWeaponRangeType] = {
    "corpo a corpo": BaseItemWeaponRangeType.MELEE,
    "a distancia": BaseItemWeaponRangeType.RANGED,
}

ARMOR_CATEGORY_BY_PT: dict[str, BaseItemArmorCategory] = {
    "leve": BaseItemArmorCategory.LIGHT,
    "media": BaseItemArmorCategory.MEDIUM,
    "pesada": BaseItemArmorCategory.HEAVY,
    "escudo": BaseItemArmorCategory.SHIELD,
}

GEAR_KIND_MAP: dict[str, BaseItemKind] = {
    "gear": BaseItemKind.GEAR,
    "tool": BaseItemKind.TOOL,
    "focus": BaseItemKind.FOCUS,
    "ammo": BaseItemKind.AMMO,
    "pack": BaseItemKind.PACK,
    "consumable": BaseItemKind.CONSUMABLE,
}


# ── Seed dataclass ──────────────────────────────────────────────────────

@dataclass
class BaseItemSeed:
    canonical_key: str
    name: str
    item_kind: BaseItemKind
    equipment_category: str | None = None
    cost_quantity: float | None = None
    cost_unit: BaseItemCostUnit | None = None
    weight: float | None = None
    description: str | None = None
    source: str | None = None
    source_ref: str | None = None
    # Weapon fields
    weapon_category: BaseItemWeaponCategory | None = None
    weapon_range_type: BaseItemWeaponRangeType | None = None
    damage_dice: str | None = None
    damage_type: str | None = None
    range_normal: int | None = None
    range_long: int | None = None
    versatile_damage: str | None = None
    weapon_properties_json: list[str] | None = None
    # Armor fields
    armor_category: BaseItemArmorCategory | None = None
    armor_class_base: int | None = None
    dex_bonus_rule: str | None = None
    strength_requirement: int | None = None
    stealth_disadvantage: bool | None = None
    is_shield: bool = False


# ── Parsing utilities ───────────────────────────────────────────────────

def _normalize_pt(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def parse_cost(raw: str) -> tuple[float | None, BaseItemCostUnit | None]:
    raw = raw.strip()
    if not raw or raw == "-":
        return None, None
    match = re.match(r"^\s*([\d.]+)\s*(cp|sp|ep|gp|pp)\s*$", raw, flags=re.IGNORECASE)
    if not match:
        return None, None
    return float(match.group(1)), BaseItemCostUnit(match.group(2).lower())


def parse_weight(raw: str) -> float | None:
    raw = raw.strip()
    if not raw or raw == "-":
        return None
    match = re.search(r"[\d.]+", raw)
    return float(match.group(0)) if match else None


def parse_int(raw: str) -> int | None:
    raw = raw.strip()
    if not raw or raw in ("-", "N/A"):
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def parse_damage_type(raw: str) -> str | None:
    key = _normalize_pt(raw)
    return DAMAGE_TYPE_BY_PT.get(key)


def parse_properties(raw: str) -> list[str] | None:
    if not raw.strip() or raw.strip() == "-":
        return None
    props = []
    for part in raw.split(","):
        key = _normalize_pt(part)
        mapped = PROPERTY_BY_PT.get(key)
        if mapped:
            props.append(mapped)
    return props or None


def parse_dex_bonus_rule(raw: str) -> str | None:
    val = raw.strip().lower()
    if val == "ilimitado":
        return "full"
    if val in ("n/a", ""):
        return "none"
    try:
        cap = int(val)
        return f"max_{cap}"
    except ValueError:
        return None


# ── Row normalizers ─────────────────────────────────────────────────────

def normalize_weapon_row(row: dict[str, str]) -> BaseItemSeed | None:
    canonical_key = row.get("canonical_key", "").strip()
    name = row.get("Nome", "").strip()
    if not canonical_key or not name:
        LOGGER.warning("Skipping weapon row without canonical_key or Nome: %s", row)
        return None

    categoria = _normalize_pt(row.get("Categoria", ""))
    weapon_category = WEAPON_CATEGORY_BY_PT.get(categoria)
    if not weapon_category:
        LOGGER.warning("Unknown weapon category '%s' for %s", row.get("Categoria"), name)
        return None

    tipo = _normalize_pt(row.get("Tipo", ""))
    weapon_range_type = WEAPON_RANGE_TYPE_BY_PT.get(tipo)
    if not weapon_range_type:
        LOGGER.warning("Unknown weapon type '%s' for %s", row.get("Tipo"), name)
        return None

    cost_qty, cost_unit = parse_cost(row.get("Custo", ""))

    return BaseItemSeed(
        canonical_key=canonical_key,
        name=name,
        item_kind=BaseItemKind.WEAPON,
        source="csv_import",
        source_ref=name,
        weapon_category=weapon_category,
        weapon_range_type=weapon_range_type,
        cost_quantity=cost_qty,
        cost_unit=cost_unit,
        weight=parse_weight(row.get("Peso", "")),
        damage_dice=row.get("Dano", "").strip() or None,
        damage_type=parse_damage_type(row.get("Tipo de dano", "")),
        range_normal=parse_int(row.get("Alcance normal", "")),
        range_long=parse_int(row.get("Alcance máximo", "")),
        versatile_damage=row.get("Dano versátil", "").strip() or None,
        weapon_properties_json=parse_properties(row.get("Propriedades", "")),
        description=row.get("Descrição curta", "").strip() or None,
    )


def normalize_armor_row(row: dict[str, str]) -> BaseItemSeed | None:
    canonical_key = row.get("canonical_key", "").strip()
    name = row.get("Nome", "").strip()
    if not canonical_key or not name:
        LOGGER.warning("Skipping armor row without canonical_key or Nome: %s", row)
        return None

    categoria = _normalize_pt(row.get("Categoria", ""))
    armor_category = ARMOR_CATEGORY_BY_PT.get(categoria)
    if not armor_category:
        LOGGER.warning("Unknown armor category '%s' for %s", row.get("Categoria"), name)
        return None

    cost_qty, cost_unit = parse_cost(row.get("Custo", ""))
    stealth_raw = _normalize_pt(row.get("Desvantagem em furtividade", ""))

    return BaseItemSeed(
        canonical_key=canonical_key,
        name=name,
        item_kind=BaseItemKind.ARMOR,
        source="csv_import",
        source_ref=name,
        armor_category=armor_category,
        armor_class_base=parse_int(row.get("CA base", "")),
        dex_bonus_rule=parse_dex_bonus_rule(row.get("Mod DEX máximo", "")),
        strength_requirement=parse_int(row.get("Requisito de FOR", "")),
        stealth_disadvantage=stealth_raw == "sim",
        is_shield=armor_category == BaseItemArmorCategory.SHIELD,
        cost_quantity=cost_qty,
        cost_unit=cost_unit,
        weight=parse_weight(row.get("Peso", "")),
        description=row.get("Descrição", "").strip() or None,
    )


def normalize_gear_row(row: dict[str, str]) -> BaseItemSeed | None:
    canonical_key = row.get("canonical_key", "").strip()
    name = row.get("Nome", "").strip()
    if not canonical_key or not name:
        LOGGER.warning("Skipping gear row without canonical_key or Nome: %s", row)
        return None

    tipo_raw = row.get("Tipo", "").strip().lower()
    item_kind = GEAR_KIND_MAP.get(tipo_raw)
    if not item_kind:
        LOGGER.warning("Unknown gear type '%s' for %s", row.get("Tipo"), name)
        return None

    cost_qty, cost_unit = parse_cost(row.get("Custo", ""))

    return BaseItemSeed(
        canonical_key=canonical_key,
        name=name,
        item_kind=item_kind,
        equipment_category=row.get("Categoria", "").strip() or None,
        cost_quantity=cost_qty,
        cost_unit=cost_unit,
        weight=parse_weight(row.get("Peso", "")),
        description=row.get("Descrição", "").strip() or None,
        source="csv_import",
        source_ref=name,
    )


# ── Database operations ─────────────────────────────────────────────────

def apply_seed_to_item(item: BaseItem, seed: BaseItemSeed) -> None:
    item.system = SYSTEM
    item.canonical_key = seed.canonical_key
    item.name_en = seed.name
    item.name_pt = seed.name
    item.description_en = seed.description
    item.description_pt = seed.description
    item.item_kind = seed.item_kind
    item.equipment_category = seed.equipment_category
    item.cost_quantity = seed.cost_quantity
    item.cost_unit = seed.cost_unit
    item.weight = seed.weight
    item.weapon_category = seed.weapon_category
    item.weapon_range_type = seed.weapon_range_type
    item.damage_dice = seed.damage_dice
    item.damage_type = seed.damage_type
    item.range_normal = seed.range_normal
    item.range_long = seed.range_long
    item.versatile_damage = seed.versatile_damage
    item.weapon_properties_json = seed.weapon_properties_json
    item.armor_category = seed.armor_category
    item.armor_class_base = seed.armor_class_base
    item.dex_bonus_rule = seed.dex_bonus_rule
    item.strength_requirement = seed.strength_requirement
    item.stealth_disadvantage = seed.stealth_disadvantage
    item.is_shield = seed.is_shield
    item.source = seed.source
    item.source_ref = seed.source_ref
    item.is_srd = False
    item.is_active = True


def run_import(*, dry_run: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    weapon_rows = load_csv(WEAPONS_CSV_PATH)
    armor_rows = load_csv(ARMORS_CSV_PATH)
    gear_rows = load_csv(GEAR_CSV_PATH)

    seeds: list[BaseItemSeed] = []
    seen_keys: dict[str, str] = {}
    skipped = 0

    def append(seed: BaseItemSeed | None) -> None:
        nonlocal skipped
        if not seed:
            skipped += 1
            return
        prev = seen_keys.get(seed.canonical_key)
        if prev and prev != seed.name:
            LOGGER.warning("Duplicate canonical_key %s: %s vs %s", seed.canonical_key, prev, seed.name)
            skipped += 1
            return
        seen_keys[seed.canonical_key] = seed.name
        seeds.append(seed)

    for row in weapon_rows:
        append(normalize_weapon_row(row))
    for row in armor_rows:
        append(normalize_armor_row(row))
    for row in gear_rows:
        append(normalize_gear_row(row))

    inserted = 0
    updated = 0

    with Session(engine) as session:
        existing = session.exec(select(BaseItem).where(BaseItem.system == SYSTEM)).all()
        items_by_key = {item.canonical_key: item for item in existing}

        for seed in seeds:
            item = items_by_key.get(seed.canonical_key)
            if item is None:
                item = BaseItem(
                    system=SYSTEM,
                    canonical_key=seed.canonical_key,
                    name_en=seed.name,
                    name_pt=seed.name,
                    item_kind=seed.item_kind,
                )
                apply_seed_to_item(item, seed)
                session.add(item)
                session.flush()
                items_by_key[seed.canonical_key] = item
                inserted += 1
                LOGGER.info("Inserted %s (%s)", seed.name, seed.canonical_key)
            else:
                apply_seed_to_item(item, seed)
                session.add(item)
                updated += 1

        if dry_run:
            session.rollback()
            LOGGER.info("Dry-run completed. Changes rolled back.")
        else:
            session.commit()

    LOGGER.info("Import: %s inserted, %s updated, %s skipped.", inserted, updated, skipped)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import D&D 5e base items from CSV files.")
    parser.add_argument("--dry-run", action="store_true", help="Roll back changes after import.")
    args = parser.parse_args()
    run_import(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
