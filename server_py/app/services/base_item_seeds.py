from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlmodel import Session, select

from app.api.serializers.base_item import to_base_item_seed_entry
from app.models.base_item import BaseItem
from app.schemas.base_item import BaseItemCreate, BaseItemSeedDocument
from app.services.base_items import create_base_item, update_base_item

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_ITEMS_SEED_PATH = REPO_ROOT / "Base" / "base_items.seed.json"


def read_base_item_seed_document(path: Path = DEFAULT_BASE_ITEMS_SEED_PATH) -> BaseItemSeedDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BaseItemSeedDocument.model_validate(payload)


def write_base_item_seed_document(
    document: BaseItemSeedDocument,
    path: Path = DEFAULT_BASE_ITEMS_SEED_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_document = BaseItemSeedDocument(
        version=document.version,
        items=sorted(
            document.items,
            key=lambda item: (
                item.system.value,
                item.itemKind.value,
                item.canonicalKey,
            ),
        ),
    )
    serialized = json.dumps(
        normalized_document.model_dump(mode="json", exclude_none=True),
        ensure_ascii=False,
        indent=2,
    )
    path.write_text(f"{serialized}\n", encoding="utf-8")


def export_base_item_seed_document(
    db: Session,
    *,
    path: Path = DEFAULT_BASE_ITEMS_SEED_PATH,
) -> BaseItemSeedDocument:
    items = db.exec(
        select(BaseItem).order_by(
            BaseItem.system,
            BaseItem.item_kind,
            BaseItem.canonical_key,
        )
    ).all()
    document = BaseItemSeedDocument(
        version=1,
        items=[to_base_item_seed_entry(item) for item in items],
    )
    write_base_item_seed_document(document, path)
    return document


def import_base_item_seed_document(
    db: Session,
    document: BaseItemSeedDocument,
    *,
    replace: bool = False,
) -> dict[str, int]:
    inserted = 0
    updated = 0
    deactivated = 0
    items_by_key: dict[tuple[str, str], BaseItem] = {}
    touched_keys: set[tuple[str, str]] = set()
    systems = sorted({item.system for item in document.items}, key=lambda value: value.value)

    if systems:
        existing_items = db.exec(
            select(BaseItem).where(BaseItem.system.in_(systems))  # type: ignore[arg-type]
        ).all()
        items_by_key = {
            (item.system.value, item.canonical_key): item
            for item in existing_items
        }

    try:
        for entry in document.items:
            key = (entry.system.value, entry.canonicalKey)
            touched_keys.add(key)
            existing = items_by_key.get(key)
            if existing:
                update_base_item(db=db, item=existing, payload=entry, commit=False, refresh=False)
                updated += 1
                continue

            created = create_base_item(
                db=db,
                payload=BaseItemCreate.model_validate(entry.model_dump()),
                commit=False,
                refresh=False,
            )
            items_by_key[key] = created
            inserted += 1

        if replace:
            for key, stale_item in items_by_key.items():
                if key in touched_keys or not stale_item.is_active:
                    continue
                stale_item.is_active = False
                db.add(stale_item)
                deactivated += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "inserted": inserted,
        "updated": updated,
        "deactivated": deactivated,
        "total": len(document.items),
    }


def import_base_item_seed_file(
    db: Session,
    *,
    path: Path = DEFAULT_BASE_ITEMS_SEED_PATH,
    replace: bool = False,
) -> dict[str, int]:
    document = read_base_item_seed_document(path)
    return import_base_item_seed_document(db, document, replace=replace)


def bootstrap_base_items_if_empty(
    db: Session,
    *,
    path: Path = DEFAULT_BASE_ITEMS_SEED_PATH,
) -> dict[str, int]:
    existing_item_id = db.exec(select(BaseItem.id)).first()
    if existing_item_id is not None:
        return {"inserted": 0, "updated": 0, "total": 0}

    if not path.is_file():
        logger.warning("Base item seed file not found at %s", path)
        return {"inserted": 0, "updated": 0, "total": 0}

    result = import_base_item_seed_file(db, path=path, replace=False)
    logger.info("Bootstrapped base item catalog from %s: %s", path, result)
    return result
