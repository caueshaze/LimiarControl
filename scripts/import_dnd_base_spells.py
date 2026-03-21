#!/usr/bin/env python3
"""Import D&D 5e spells from CSV into the base_spell table.

Source of truth: Base/DND5e_Magias_Completas_API.csv
Each row must include a `canonical_key` column used as the unique spell identifier.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "server_py"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.base_spell import BaseSpell, SpellSchool
from app.models.campaign import SystemType

LOGGER = logging.getLogger("import_dnd_base_spells")

SPELLS_CSV_PATH = REPO_ROOT / "Base" / "DND5e_Magias_Completas_API.csv"
SYSTEM = SystemType.DND5E

SCHOOL_MAP: dict[str, SpellSchool] = {
    "abjuration": SpellSchool.ABJURATION,
    "conjuration": SpellSchool.CONJURATION,
    "divination": SpellSchool.DIVINATION,
    "enchantment": SpellSchool.ENCHANTMENT,
    "evocation": SpellSchool.EVOCATION,
    "illusion": SpellSchool.ILLUSION,
    "necromancy": SpellSchool.NECROMANCY,
    "transmutation": SpellSchool.TRANSMUTATION,
}


@dataclass
class BaseSpellSeed:
    canonical_key: str
    name: str
    description: str
    level: int
    school: SpellSchool
    classes_json: list[str]
    casting_time: str | None = None
    range_text: str | None = None
    duration: str | None = None
    components_json: list[str] | None = None
    material_component_text: str | None = None
    concentration: bool = False
    ritual: bool = False
    damage_type: str | None = None
    saving_throw: str | None = None


# ── Parsing utilities ───────────────────────────────────────────────────


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def parse_level(raw: str) -> int:
    raw = raw.strip()
    try:
        return int(raw)
    except ValueError:
        LOGGER.warning("Unrecognized level: %s, defaulting to 0", raw)
        return 0


def parse_school(raw: str) -> SpellSchool | None:
    school = SCHOOL_MAP.get(raw.strip().lower())
    if not school:
        LOGGER.warning("Unknown school: %s", raw)
    return school


def parse_classes(raw: str) -> list[str]:
    return [c.strip() for c in raw.split(",") if c.strip()]


def parse_components(raw: str) -> list[str] | None:
    raw = raw.strip()
    if not raw:
        return None
    components = [p.strip().upper() for p in raw.split(",") if p.strip().upper() in ("V", "S", "M")]
    return components or None


def parse_bool_pt(raw: str) -> bool:
    return raw.strip().lower() == "sim"


def parse_nullable(raw: str) -> str | None:
    raw = raw.strip()
    if not raw or raw in ("-", "—", "N/A"):
        return None
    return raw


# ── Row normalization ───────────────────────────────────────────────────


def normalize_spell_row(row: dict[str, str]) -> BaseSpellSeed | None:
    canonical_key = row.get("canonical_key", "").strip()
    name = row.get("Nome", "").strip()
    if not canonical_key or not name:
        LOGGER.warning("Skipping row without canonical_key or Nome: %s", row)
        return None

    school = parse_school(row.get("Escola", ""))
    if not school:
        return None

    description = row.get("Descrição", "").strip()
    if not description:
        LOGGER.warning("Skipping spell with empty description: %s", name)
        return None

    return BaseSpellSeed(
        canonical_key=canonical_key,
        name=name,
        description=description,
        level=parse_level(row.get("Nível", "")),
        school=school,
        classes_json=parse_classes(row.get("Classe(s)", "")),
        casting_time=row.get("Tempo de conjuração", "").strip() or None,
        range_text=row.get("Alcance", "").strip() or None,
        duration=row.get("Duração", "").strip() or None,
        components_json=parse_components(row.get("Componentes", "")),
        concentration=parse_bool_pt(row.get("Concentração", "")),
        ritual=parse_bool_pt(row.get("Ritual", "")),
        damage_type=parse_nullable(row.get("Tipo de dano", "")),
        saving_throw=parse_nullable(row.get("Teste de resistência", "")),
    )


# ── Database operations ─────────────────────────────────────────────────


def apply_seed_to_spell(spell: BaseSpell, seed: BaseSpellSeed) -> None:
    spell.system = SYSTEM
    spell.canonical_key = seed.canonical_key
    spell.name_en = seed.name
    spell.name_pt = seed.name
    spell.description_en = seed.description
    spell.description_pt = seed.description
    spell.level = seed.level
    spell.school = seed.school
    spell.classes_json = seed.classes_json
    spell.casting_time = seed.casting_time
    spell.range_text = seed.range_text
    spell.duration = seed.duration
    spell.components_json = seed.components_json
    spell.material_component_text = seed.material_component_text
    spell.concentration = seed.concentration
    spell.ritual = seed.ritual
    spell.damage_type = seed.damage_type
    spell.saving_throw = seed.saving_throw
    spell.source = "csv_import"
    spell.source_ref = seed.name
    spell.is_srd = False
    spell.is_active = True


def run_import(*, dry_run: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = load_csv(SPELLS_CSV_PATH)
    LOGGER.info("Loaded %d rows from CSV.", len(rows))

    seeds: list[BaseSpellSeed] = []
    seen_keys: dict[str, str] = {}
    skipped = 0

    for row in rows:
        seed = normalize_spell_row(row)
        if not seed:
            skipped += 1
            continue

        prev = seen_keys.get(seed.canonical_key)
        if prev and prev != seed.name:
            LOGGER.warning("Duplicate canonical_key %s: %s vs %s", seed.canonical_key, prev, seed.name)
            skipped += 1
            continue

        seen_keys[seed.canonical_key] = seed.name
        seeds.append(seed)

    inserted = 0
    updated = 0

    with Session(engine) as session:
        existing = session.exec(select(BaseSpell).where(BaseSpell.system == SYSTEM)).all()
        spells_by_key = {spell.canonical_key: spell for spell in existing}

        for seed in seeds:
            spell = spells_by_key.get(seed.canonical_key)
            if spell is None:
                spell = BaseSpell(
                    system=SYSTEM,
                    canonical_key=seed.canonical_key,
                    name_en=seed.name,
                    description_en=seed.description,
                    level=seed.level,
                    school=seed.school,
                )
                apply_seed_to_spell(spell, seed)
                session.add(spell)
                session.flush()
                spells_by_key[seed.canonical_key] = spell
                inserted += 1
                LOGGER.info("Inserted %s (%s)", seed.name, seed.canonical_key)
            else:
                apply_seed_to_spell(spell, seed)
                session.add(spell)
                updated += 1

        if dry_run:
            session.rollback()
            LOGGER.info("Dry-run completed. Changes rolled back.")
        else:
            session.commit()

    LOGGER.info("Import: %d inserted, %d updated, %d skipped.", inserted, updated, skipped)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import D&D 5e spells from CSV.")
    parser.add_argument("--dry-run", action="store_true", help="Roll back changes after import.")
    args = parser.parse_args()
    run_import(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
