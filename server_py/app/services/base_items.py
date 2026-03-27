from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_
from sqlmodel import Session, select

from app.models.base_item import BaseItem, BaseItemEquipmentCategory, BaseItemKind
from app.models.campaign import SystemType
from app.schemas.base_item import BaseItemCreate, BaseItemUpdate


def _normalize_lookup(value: str) -> str:
    return value.strip().lower()


def list_base_items(
    *,
    db: Session,
    system: SystemType | None = None,
    item_kind: BaseItemKind | None = None,
    canonical_key: str | None = None,
    search: str | None = None,
    equipment_category: BaseItemEquipmentCategory | None = None,
    is_active: bool | None = None,
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
    if search:
        pattern = f"%{_normalize_lookup(search)}%"
        statement = statement.where(
            or_(
                func.lower(BaseItem.canonical_key).like(pattern),
                func.lower(BaseItem.name_en).like(pattern),
                func.lower(BaseItem.name_pt).like(pattern),
                func.lower(func.coalesce(cast(BaseItem.equipment_category, String), "")).like(pattern),
            )
        )
    if equipment_category:
        statement = statement.where(BaseItem.equipment_category == equipment_category)
    if is_active is not None:
        statement = statement.where(BaseItem.is_active == is_active)  # noqa: E712
    statement = statement.order_by(BaseItem.item_kind, BaseItem.name_pt, BaseItem.canonical_key)
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


def _apply_payload(item: BaseItem, payload: BaseItemCreate | BaseItemUpdate) -> None:
    item.system = payload.system
    item.canonical_key = payload.canonicalKey
    item.name_en = payload.nameEn or payload.namePt or payload.canonicalKey
    item.name_pt = payload.namePt or payload.nameEn or payload.canonicalKey
    item.description_en = payload.descriptionEn
    item.description_pt = payload.descriptionPt
    item.item_kind = payload.itemKind
    item.equipment_category = payload.equipmentCategory
    item.cost_quantity = payload.costQuantity
    item.cost_unit = payload.costUnit
    item.weight = payload.weight
    item.weapon_category = payload.weaponCategory
    item.weapon_range_type = payload.weaponRangeType
    item.damage_dice = payload.damageDice
    item.damage_type = payload.damageType
    item.range_normal_meters = payload.rangeNormalMeters
    item.range_long_meters = payload.rangeLongMeters
    item.versatile_damage = payload.versatileDamage
    item.weapon_properties_json = [
        property_value.value for property_value in payload.weaponPropertiesJson
    ] or None
    item.armor_category = payload.armorCategory
    item.armor_class_base = payload.armorClassBase
    item.dex_bonus_rule = payload.dexBonusRule
    item.strength_requirement = payload.strengthRequirement
    item.stealth_disadvantage = payload.stealthDisadvantage
    item.is_shield = payload.isShield
    item.source = payload.source
    item.source_ref = payload.sourceRef
    item.is_srd = payload.isSrd
    item.is_active = payload.isActive


def create_base_item(*, db: Session, payload: BaseItemCreate) -> BaseItem:
    existing = get_base_item_by_canonical_key(
        db=db,
        system=payload.system,
        canonical_key=payload.canonicalKey,
    )
    if existing:
        raise HTTPException(status_code=409, detail="canonicalKey already exists")

    item = BaseItem(id=str(uuid4()))
    _apply_payload(item, payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_base_item(
    *,
    db: Session,
    item: BaseItem,
    payload: BaseItemUpdate,
) -> BaseItem:
    existing = get_base_item_by_canonical_key(
        db=db,
        system=payload.system,
        canonical_key=payload.canonicalKey,
    )
    if existing and existing.id != item.id:
        raise HTTPException(status_code=409, detail="canonicalKey already exists")

    _apply_payload(item, payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_base_item(*, db: Session, item: BaseItem) -> None:
    db.delete(item)
    db.commit()
