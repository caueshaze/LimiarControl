from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.base_item import BaseItem, BaseItemKind
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
