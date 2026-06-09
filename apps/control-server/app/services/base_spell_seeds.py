from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from sqlmodel import Session, col, select

from app.api.serializers.base_spell import to_base_spell_seed_entry
from app.models.base_spell import BaseSpell
from app.schemas.base_spell import BaseSpellCreate, BaseSpellSeedDocument, BaseSpellUpdate
from app.services.base_spells import create_base_spell, update_base_spell
from app.services.seed_paths import resolve_base_seed_path

logger = logging.getLogger(__name__)

DEFAULT_BASE_SPELLS_SEED_PATH = resolve_base_seed_path(
    __file__, "base_spells.seed.json"
)


def read_base_spell_seed_document(
    path: Path = DEFAULT_BASE_SPELLS_SEED_PATH,
) -> BaseSpellSeedDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    spells = payload.get("spells")
    if isinstance(spells, list):
        deduped: list[dict] = []
        seen_indexes: dict[tuple[str, str], int] = {}
        duplicate_count = 0
        for entry in spells:
            if not isinstance(entry, dict):
                deduped.append(entry)
                continue
            classes_json = entry.get("classesJson")
            if isinstance(classes_json, list):
                normalized_classes = [
                    klass
                    for klass in classes_json
                    if str(klass).strip().lower() != "artificer"
                ]
                if len(normalized_classes) != len(classes_json):
                    logger.warning(
                        "Removed unsupported class 'Artificer' from seed spell %s",
                        entry.get("canonicalKey"),
                    )
                entry = {**entry, "classesJson": normalized_classes}
            system = str(entry.get("system") or "").strip()
            canonical_key = str(entry.get("canonicalKey") or "").strip()
            key = (system, canonical_key)
            if system and canonical_key and key in seen_indexes:
                deduped[seen_indexes[key]] = entry
                duplicate_count += 1
                continue
            seen_indexes[key] = len(deduped)
            deduped.append(entry)
        if duplicate_count:
            logger.warning(
                "Deduplicated %s duplicate base spell seed entries while reading %s",
                duplicate_count,
                path,
            )
        payload["spells"] = deduped
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
            col(BaseSpell.system),
            col(BaseSpell.level),
            col(BaseSpell.canonical_key),
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
    systems = sorted(
        {spell.system for spell in document.spells}, key=lambda value: value.value
    )

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
                    # BaseSpellCreate/BaseSpellUpdate are interchangeable BaseSpellWrite
                    # subclasses; cast keeps the same object (no re-validation).
                    payload=cast(BaseSpellUpdate, entry),
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

    try:
        result = import_base_spell_seed_file(db, path=path, replace=False)
    except ValidationError as exc:
        logger.warning(
            "Base spell seed at %s failed validation (%d errors) — bootstrap skipped. "
            "Use the admin UI to import spells manually.\n%s",
            path,
            exc.error_count(),
            exc,
        )
        return {"inserted": 0, "updated": 0, "total": 0}
    logger.info("Bootstrapped base spell catalog from %s: %s", path, result)
    return result
