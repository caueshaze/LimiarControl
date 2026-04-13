from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.inventory import InventoryItem


def normalize_inventory_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_inventory_item_expired(
    entry: InventoryItem | None,
    *,
    now: datetime | None = None,
) -> bool:
    if entry is None:
        return False
    expires_at = normalize_inventory_timestamp(entry.expires_at)
    if expires_at is None:
        return False
    reference = normalize_inventory_timestamp(now) or utcnow()
    return expires_at <= reference


def purge_expired_inventory_items(
    db: Session,
    *,
    campaign_id: str | None = None,
    member_id: str | None = None,
    party_id: str | None = None,
    inventory_item_id: str | None = None,
    now: datetime | None = None,
    flush: bool = True,
) -> list[str]:
    reference = normalize_inventory_timestamp(now) or utcnow()

    filters = [InventoryItem.expires_at.is_not(None)]
    if campaign_id:
        filters.append(InventoryItem.campaign_id == campaign_id)
    if member_id:
        filters.append(InventoryItem.member_id == member_id)
    if party_id is not None:
        filters.append(InventoryItem.party_id == party_id)
    if inventory_item_id:
        filters.append(InventoryItem.id == inventory_item_id)

    entries = db.exec(select(InventoryItem).where(*filters)).all()
    removed_ids: list[str] = []
    for entry in entries:
        expires_at = normalize_inventory_timestamp(entry.expires_at)
        if expires_at is None or expires_at > reference:
            continue
        if entry.id:
            removed_ids.append(entry.id)
        db.delete(entry)

    if removed_ids and flush:
        db.flush()
    return removed_ids
