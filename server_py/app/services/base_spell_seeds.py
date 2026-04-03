from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlmodel import Session, select

from app.api.serializers.base_spell import to_base_spell_seed_entry
from app.models.base_spell import BaseSpell
from app.schemas.base_spell import BaseSpellCreate, BaseSpellSeedDocument
from app.services.base_spells import create_base_spell, update_base_spell

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_SPELLS_SEED_PATH = REPO_ROOT / "Base" / "base_spells.seed.json"


def read_base_spell_seed_document(path: Path = DEFAULT_BASE_SPELLS_SEED_PATH) -> BaseSpellSeedDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BaseSpellSeedDocument.model_validate(payload)


def write_base_spell_seed_document(
    document: BaseSpellSeedDocument,
    path: Path = DEFAULT_BASE_SPELLS_SEED_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_document = BaseSpellSeedDocument(
        version=document.version,
        spells=sorted(
            document.spells,
            key=lambda spell: (
                spell.system.value,
                spell.level,
                spell.canonicalKey,
            ),
        ),
    )
    serialized = json.dumps(
        normalized_document.model_dump(mode="json", exclude_none=True),
        ensure_ascii=False,
        indent=2,
    )
    path.write_text(f"{serialized}\n", encoding="utf-8")


def export_base_spell_seed_document(
    db: Session,
    *,
    path: Path = DEFAULT_BASE_SPELLS_SEED_PATH,
) -> BaseSpellSeedDocument:
    spells = db.exec(
        select(BaseSpell).order_by(
            BaseSpell.system,
            BaseSpell.level,
            BaseSpell.canonical_key,
        )
    ).all()
    document = BaseSpellSeedDocument(
        version=1,
        spells=[to_base_spell_seed_entry(spell) for spell in spells],
    )
    write_base_spell_seed_document(document, path)
    return document


def import_base_spell_seed_document(
    db: Session,
    document: BaseSpellSeedDocument,
    *,
    replace: bool = False,
) -> dict[str, int]:
    inserted = 0
    updated = 0
    deactivated = 0
    spells_by_key: dict[tuple[str, str], BaseSpell] = {}
    touched_keys: set[tuple[str, str]] = set()
    systems = sorted({spell.system for spell in document.spells}, key=lambda value: value.value)

    if systems:
        existing_spells = db.exec(
            select(BaseSpell).where(BaseSpell.system.in_(systems))  # type: ignore[arg-type]
        ).all()
        spells_by_key = {
            (spell.system.value, spell.canonical_key): spell
            for spell in existing_spells
        }

    try:
        for entry in document.spells:
            key = (entry.system.value, entry.canonicalKey)
            touched_keys.add(key)
            existing = spells_by_key.get(key)
            if existing:
                update_base_spell(
                    db=db,
                    spell=existing,
                    payload=entry,
                    commit=False,
                    refresh=False,
                )
                updated += 1
                continue

            created = create_base_spell(
                db=db,
                payload=BaseSpellCreate.model_validate(entry.model_dump()),
                commit=False,
                refresh=False,
            )
            spells_by_key[key] = created
            inserted += 1

        if replace:
            for key, stale_spell in spells_by_key.items():
                if key in touched_keys or not stale_spell.is_active:
                    continue
                stale_spell.is_active = False
                db.add(stale_spell)
                deactivated += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "inserted": inserted,
        "updated": updated,
        "deactivated": deactivated,
        "total": len(document.spells),
    }


def import_base_spell_seed_file(
    db: Session,
    *,
    path: Path = DEFAULT_BASE_SPELLS_SEED_PATH,
    replace: bool = False,
) -> dict[str, int]:
    document = read_base_spell_seed_document(path)
    return import_base_spell_seed_document(db, document, replace=replace)


def bootstrap_base_spells_if_empty(
    db: Session,
    *,
    path: Path = DEFAULT_BASE_SPELLS_SEED_PATH,
) -> dict[str, int]:
    existing_spell_id = db.exec(select(BaseSpell.id)).first()
    if existing_spell_id is not None:
        return {"inserted": 0, "updated": 0, "total": 0}

    if not path.is_file():
        logger.warning("Base spell seed file not found at %s", path)
        return {"inserted": 0, "updated": 0, "total": 0}

    result = import_base_spell_seed_file(db, path=path, replace=False)
    logger.info("Bootstrapped base spell catalog from %s: %s", path, result)
    return result
