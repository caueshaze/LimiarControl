#!/usr/bin/env python3
"""Import D&D 5e spells from CSV into base_spell / base_spell_alias tables."""
from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "server_py"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.base_spell import BaseSpell, BaseSpellAlias, SpellSchool
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


@dataclass(frozen=True)
class AliasSeed:
    alias: str
    locale: str | None = None
    alias_type: str | None = None


@dataclass
class BaseSpellSeed:
    canonical_key: str
    name_en: str
    name_pt: str | None
    description_en: str
    description_pt: str | None
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
    source: str | None = None
    source_ref: str | None = None
    aliases: list[AliasSeed] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_lookup(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_only.lower()).strip()


def snake_case(value: str) -> str:
    return normalize_lookup(value).replace(" ", "_")


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


def parse_components(raw: str) -> tuple[list[str], str | None]:
    """Parse component string like 'V, S, M' into list and extract material text."""
    raw = raw.strip()
    if not raw:
        return [], None

    components: list[str] = []
    for part in raw.split(","):
        component = part.strip().upper()
        if component in ("V", "S", "M"):
            components.append(component)
    return components, None


def parse_bool_pt(raw: str) -> bool:
    return raw.strip().lower() == "sim"


def parse_nullable(raw: str) -> str | None:
    raw = raw.strip()
    if not raw or raw in ("-", "—", "N/A"):
        return None
    return raw


def load_spells_csv() -> list[dict[str, str]]:
    with SPELLS_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_spell_row(row: dict[str, str]) -> BaseSpellSeed | None:
    name_en = row["Nome"].strip()
    if not name_en:
        LOGGER.warning("Skipping row with empty name")
        return None

    school = parse_school(row["Escola"])
    if not school:
        LOGGER.warning("Skipping spell with unknown school: %s", name_en)
        return None

    level = parse_level(row["Nível"])
    classes = parse_classes(row["Classe(s)"])
    components, material_text = parse_components(row["Componentes"])
    concentration = parse_bool_pt(row["Concentração"])
    ritual = parse_bool_pt(row["Ritual"])

    description_en = row["Descrição"].strip()
    if not description_en:
        LOGGER.warning("Skipping spell with empty description: %s", name_en)
        return None

    canonical_key = snake_case(name_en)

    aliases: list[AliasSeed] = [
        AliasSeed(alias=name_en, locale="en", alias_type="primary"),
    ]

    return BaseSpellSeed(
        canonical_key=canonical_key,
        name_en=name_en,
        name_pt=None,
        description_en=description_en,
        description_pt=None,
        level=level,
        school=school,
        classes_json=classes,
        casting_time=row["Tempo de conjuração"].strip() or None,
        range_text=row["Alcance"].strip() or None,
        duration=row["Duração"].strip() or None,
        components_json=components if components else None,
        material_component_text=material_text,
        concentration=concentration,
        ritual=ritual,
        damage_type=parse_nullable(row["Tipo de dano"]),
        saving_throw=parse_nullable(row["Teste de resistência"]),
        source=SPELLS_CSV_PATH.name,
        source_ref=name_en,
        aliases=aliases,
    )


# ---------------------------------------------------------------------------
# Alias sync
# ---------------------------------------------------------------------------

def dedupe_aliases(aliases: list[AliasSeed]) -> list[AliasSeed]:
    deduped: list[AliasSeed] = []
    seen: set[str] = set()
    for entry in aliases:
        alias_key = normalize_lookup(entry.alias)
        if not alias_key or alias_key in seen:
            continue
        seen.add(alias_key)
        deduped.append(entry)
    return deduped


def sync_aliases(
    *,
    session: Session,
    spell: BaseSpell,
    alias_seeds: list[AliasSeed],
    aliases_by_spell_id: dict[str, dict[str, BaseSpellAlias]],
    alias_owner_by_key: dict[str, str],
) -> tuple[int, int]:
    created = 0
    updated = 0
    existing_aliases = aliases_by_spell_id.setdefault(spell.id, {})

    for alias_seed in dedupe_aliases(alias_seeds):
        alias_key = normalize_lookup(alias_seed.alias)
        if not alias_key:
            continue

        owner_id = alias_owner_by_key.get(alias_key)
        if owner_id and owner_id != spell.id:
            LOGGER.warning(
                "Alias conflict for %s: %s already belongs to another spell (%s)",
                spell.canonical_key,
                alias_seed.alias,
                owner_id,
            )
            continue

        existing = existing_aliases.get(alias_key)
        if existing:
            changed = False
            if alias_seed.locale is not None and existing.locale != alias_seed.locale:
                existing.locale = alias_seed.locale
                changed = True
            if alias_seed.alias_type is not None and existing.alias_type != alias_seed.alias_type:
                existing.alias_type = alias_seed.alias_type
                changed = True
            if changed:
                session.add(existing)
                updated += 1
            continue

        alias_record = BaseSpellAlias(
            base_spell_id=spell.id,
            alias=alias_seed.alias,
            locale=alias_seed.locale,
            alias_type=alias_seed.alias_type,
        )
        session.add(alias_record)
        session.flush()
        existing_aliases[alias_key] = alias_record
        alias_owner_by_key[alias_key] = spell.id
        created += 1

    return created, updated


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def load_existing_spells(
    session: Session,
) -> tuple[dict[str, BaseSpell], dict[str, dict[str, BaseSpellAlias]], dict[str, str]]:
    spells = session.exec(
        select(BaseSpell).where(BaseSpell.system == SYSTEM)
    ).all()
    spells_by_key = {spell.canonical_key: spell for spell in spells}

    aliases = session.exec(
        select(BaseSpellAlias, BaseSpell)
        .join(BaseSpell, BaseSpellAlias.base_spell_id == BaseSpell.id)  # type: ignore[arg-type]
        .where(BaseSpell.system == SYSTEM)
    ).all()

    aliases_by_spell_id: dict[str, dict[str, BaseSpellAlias]] = {}
    alias_owner_by_key: dict[str, str] = {}

    for alias, spell in aliases:
        spell_aliases = aliases_by_spell_id.setdefault(spell.id, {})
        alias_key = normalize_lookup(alias.alias)
        if alias_key in alias_owner_by_key and alias_owner_by_key[alias_key] != spell.id:
            LOGGER.warning(
                "Existing alias conflict in database: %s used by %s and %s",
                alias.alias,
                alias_owner_by_key[alias_key],
                spell.id,
            )
            continue
        spell_aliases[alias_key] = alias
        alias_owner_by_key[alias_key] = spell.id

    return spells_by_key, aliases_by_spell_id, alias_owner_by_key


def apply_seed_to_spell(spell: BaseSpell, seed: BaseSpellSeed) -> None:
    spell.system = SYSTEM
    spell.canonical_key = seed.canonical_key
    spell.name_en = seed.name_en
    spell.name_pt = seed.name_pt
    spell.description_en = seed.description_en
    spell.description_pt = seed.description_pt
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
    spell.source = seed.source
    spell.source_ref = seed.source_ref
    spell.is_srd = False
    spell.is_active = True


# ---------------------------------------------------------------------------
# Main import
# ---------------------------------------------------------------------------

def run_import(*, dry_run: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = load_spells_csv()
    LOGGER.info("Loaded %d rows from CSV.", len(rows))

    prepared_spells: list[BaseSpellSeed] = []
    seen_canonical_keys: dict[str, str] = {}
    skipped = 0

    for row in rows:
        seed = normalize_spell_row(row)
        if not seed:
            skipped += 1
            continue

        previous = seen_canonical_keys.get(seed.canonical_key)
        if previous and previous != seed.name_en:
            LOGGER.warning(
                "Canonical key conflict: %s maps both %s and %s. Skipping %s.",
                seed.canonical_key,
                previous,
                seed.name_en,
                seed.name_en,
            )
            skipped += 1
            continue

        seen_canonical_keys[seed.canonical_key] = seed.name_en
        prepared_spells.append(seed)

    LOGGER.info("Prepared %d spells (%d skipped).", len(prepared_spells), skipped)

    inserted = 0
    updated = 0
    created_aliases = 0
    updated_aliases = 0

    with Session(engine) as session:
        spells_by_key, aliases_by_spell_id, alias_owner_by_key = load_existing_spells(session)

        for seed in prepared_spells:
            spell = spells_by_key.get(seed.canonical_key)
            if spell is None:
                spell = BaseSpell(  # type: ignore[call-arg]
                    system=SYSTEM,
                    canonical_key=seed.canonical_key,
                    name_en=seed.name_en,
                    description_en=seed.description_en,
                    level=seed.level,
                    school=seed.school,
                )
                apply_seed_to_spell(spell, seed)
                session.add(spell)
                session.flush()
                spells_by_key[seed.canonical_key] = spell
                inserted += 1
                LOGGER.info("Inserted %s (%s)", seed.name_en, seed.canonical_key)
            else:
                apply_seed_to_spell(spell, seed)
                session.add(spell)
                updated += 1
                LOGGER.info("Updated %s (%s)", seed.name_en, seed.canonical_key)

            alias_created, alias_updated = sync_aliases(
                session=session,
                spell=spell,
                alias_seeds=seed.aliases,
                aliases_by_spell_id=aliases_by_spell_id,
                alias_owner_by_key=alias_owner_by_key,
            )
            created_aliases += alias_created
            updated_aliases += alias_updated

        if dry_run:
            session.rollback()
            LOGGER.info("Dry-run completed. Database changes were rolled back.")
        else:
            session.commit()

    LOGGER.info(
        "Import summary: %d inserted, %d updated, %d aliases created, %d aliases updated, %d skipped.",
        inserted,
        updated,
        created_aliases,
        updated_aliases,
        skipped,
    )

    # Spot-check: verify famous spells
    spot_check = ["magic_missile", "mage_hand", "shield", "fire_bolt", "cure_wounds", "guiding_bolt"]
    found = [k for k in spot_check if k in seen_canonical_keys]
    missing = [k for k in spot_check if k not in seen_canonical_keys]
    LOGGER.info("Spot-check found: %s", ", ".join(found) if found else "(none)")
    if missing:
        LOGGER.warning("Spot-check missing: %s", ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import D&D 5e spells from CSV into base_spell/base_spell_alias."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and normalize data, but roll back database changes at the end.",
    )
    args = parser.parse_args()
    run_import(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
