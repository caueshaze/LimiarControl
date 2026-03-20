from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.base_item import BaseItem, BaseItemAlias, BaseItemKind
from app.models.campaign import SystemType


def _normalize_lookup(value: str) -> str:
    return value.strip().lower()


def list_base_items(
    *,
    db: Session,
    system: SystemType | None = None,
    item_kind: BaseItemKind | None = None,
    canonical_key: str | None = None,
) -> list[BaseItem]:
    statement = select(BaseItem)
    if system is not None:
        statement = statement.where(BaseItem.system == system)
    if item_kind is not None:
        statement = statement.where(BaseItem.item_kind == item_kind)
    if canonical_key:
        statement = statement.where(
            func.lower(BaseItem.canonical_key) == _normalize_lookup(canonical_key)
        )
    statement = statement.order_by(BaseItem.item_kind, BaseItem.canonical_key)
    return db.exec(statement).all()


def get_base_item_by_id(*, db: Session, base_item_id: str) -> BaseItem | None:
    return db.exec(select(BaseItem).where(BaseItem.id == base_item_id)).first()


def get_base_item_by_canonical_key(
    *,
    db: Session,
    system: SystemType,
    canonical_key: str,
) -> BaseItem | None:
    return db.exec(
        select(BaseItem).where(
            BaseItem.system == system,
            func.lower(BaseItem.canonical_key) == _normalize_lookup(canonical_key),
        )
    ).first()


def get_base_item_by_alias(
    *,
    db: Session,
    system: SystemType,
    alias: str,
) -> BaseItem | None:
    statement = (
        select(BaseItem)
        .join(BaseItemAlias, BaseItemAlias.base_item_id == BaseItem.id)
        .where(
            BaseItem.system == system,
            func.lower(BaseItemAlias.alias) == _normalize_lookup(alias),
        )
    )
    return db.exec(statement).first()


def list_base_item_aliases(
    *,
    db: Session,
    base_item_ids: list[str],
) -> dict[str, list[BaseItemAlias]]:
    if not base_item_ids:
        return {}

    aliases = db.exec(
        select(BaseItemAlias)
        .where(BaseItemAlias.base_item_id.in_(base_item_ids))
        .order_by(BaseItemAlias.alias)
    ).all()

    grouped: dict[str, list[BaseItemAlias]] = defaultdict(list)
    for alias in aliases:
        grouped[alias.base_item_id].append(alias)
    return dict(grouped)
