"""Service for materializing base_item catalog into campaign-level items."""
from __future__ import annotations

import logging
from uuid import uuid4

from sqlmodel import Session, select

from app.models.base_item import BaseItem, BaseItemCostUnit, BaseItemKind
from app.models.campaign import SystemType
from app.models.item import Item, ItemType

logger = logging.getLogger(__name__)

ITEM_KIND_TO_ITEM_TYPE: dict[BaseItemKind, ItemType] = {
    BaseItemKind.WEAPON: ItemType.WEAPON,
    BaseItemKind.ARMOR: ItemType.ARMOR,
    BaseItemKind.GEAR: ItemType.MISC,
    BaseItemKind.TOOL: ItemType.MISC,
    BaseItemKind.CONSUMABLE: ItemType.CONSUMABLE,
    BaseItemKind.FOCUS: ItemType.MISC,
    BaseItemKind.AMMO: ItemType.MISC,
    BaseItemKind.PACK: ItemType.MISC,
}


def _base_item_price_gp(base_item: BaseItem) -> float | None:
    if base_item.cost_quantity is None:
        return None
    unit = base_item.cost_unit
    if unit is None or unit == BaseItemCostUnit.GP:
        return base_item.cost_quantity
    if unit == BaseItemCostUnit.CP:
        return base_item.cost_quantity / 100.0
    if unit == BaseItemCostUnit.SP:
        return base_item.cost_quantity / 10.0
    if unit == BaseItemCostUnit.EP:
        return base_item.cost_quantity / 2.0
    if unit == BaseItemCostUnit.PP:
        return base_item.cost_quantity * 10.0
    return base_item.cost_quantity


def _feet_to_meters(feet: int | None) -> float | None:
    if feet is None or feet <= 5:
        return None
    return max(1.0, round(feet * 0.3048))


def _build_weapon_properties(base_item: BaseItem) -> list[str]:
    props: list[str] = []
    if base_item.weapon_properties_json:
        props.extend(base_item.weapon_properties_json)
    return props


def _build_armor_properties(base_item: BaseItem) -> list[str]:
    props: list[str] = []
    if base_item.armor_class_base is not None:
        props.append(f"CA base {base_item.armor_class_base}")
    if base_item.armor_category:
        category_labels = {
            "light": "leve",
            "medium": "média",
            "heavy": "pesada",
            "shield": "escudo",
        }
        label = category_labels.get(base_item.armor_category.value, base_item.armor_category.value)
        if base_item.armor_category.value == "shield":
            props.append("Bônus de escudo")
        else:
            props.append(f"Tipo {label}")
    if base_item.dex_bonus_rule and base_item.dex_bonus_rule != "unlimited":
        props.append(f"DEX máx {base_item.dex_bonus_rule}")
    if base_item.strength_requirement:
        props.append(f"FOR {base_item.strength_requirement}")
    if base_item.stealth_disadvantage:
        props.append("Desvantagem em furtividade")
    return props


def _base_item_to_campaign_item(
    base_item: BaseItem,
    campaign_id: str,
) -> Item:
    item_type = ITEM_KIND_TO_ITEM_TYPE.get(base_item.item_kind, ItemType.MISC)

    properties: list[str] = []
    if base_item.item_kind == BaseItemKind.WEAPON:
        properties = _build_weapon_properties(base_item)
    elif base_item.item_kind == BaseItemKind.ARMOR:
        properties = _build_armor_properties(base_item)

    return Item(  # type: ignore[call-arg]
        id=str(uuid4()),
        campaign_id=campaign_id,
        name=base_item.name_en,
        type=item_type,
        description=base_item.description_pt or base_item.description_en or base_item.name_pt or "",
        price=_base_item_price_gp(base_item),
        weight=base_item.weight,
        damage_dice=base_item.damage_dice,
        range_meters=_feet_to_meters(base_item.range_normal),
        properties=properties,
        base_item_id=base_item.id,
        canonical_key_snapshot=base_item.canonical_key,
        name_en_snapshot=base_item.name_en,
        name_pt_snapshot=base_item.name_pt,
        item_kind=base_item.item_kind,
        cost_unit=base_item.cost_unit,
        is_custom=False,
        is_enabled=True,
    )


def seed_campaign_catalog(
    campaign_id: str,
    system: SystemType,
    db: Session,
) -> dict[str, int]:
    """Materializes active base items into campaign-level items.

    Returns {"inserted": N, "existing": M}.
    """
    base_items = db.exec(
        select(BaseItem)
        .where(BaseItem.system == system, BaseItem.is_active == True)  # noqa: E712
        .order_by(BaseItem.item_kind, BaseItem.canonical_key)
    ).all()

    existing_base_ids: set[str] = set()
    existing_items = db.exec(
        select(Item.base_item_id)
        .where(
            Item.campaign_id == campaign_id,
            Item.base_item_id.is_not(None),  # type: ignore[union-attr]
        )
    ).all()
    for row in existing_items:
        if row is not None:
            existing_base_ids.add(row)

    inserted = 0
    for base_item in base_items:
        if base_item.id in existing_base_ids:
            continue
        campaign_item = _base_item_to_campaign_item(base_item, campaign_id)
        db.add(campaign_item)
        inserted += 1

    if inserted > 0:
        db.commit()
        logger.info(
            "Seeded %d campaign items for campaign=%s system=%s",
            inserted,
            campaign_id,
            system.value,
        )

    return {"inserted": inserted, "existing": len(existing_base_ids)}


def list_campaign_catalog(
    campaign_id: str,
    db: Session,
    *,
    item_kind: BaseItemKind | None = None,
    search: str | None = None,
    enabled_only: bool = True,
) -> list[Item]:
    """List campaign items (catalog) with optional filters."""
    statement = select(Item).where(Item.campaign_id == campaign_id)

    if enabled_only:
        statement = statement.where(Item.is_enabled == True)  # noqa: E712

    if item_kind is not None:
        statement = statement.where(Item.item_kind == item_kind)

    if search:
        pattern = f"%{search.strip().lower()}%"
        from sqlalchemy import or_, func
        statement = statement.where(
            or_(
                func.lower(Item.name).like(pattern),
                func.lower(Item.name_en_snapshot).like(pattern),
                func.lower(Item.name_pt_snapshot).like(pattern),
                func.lower(Item.canonical_key_snapshot).like(pattern),
            )
        )

    statement = statement.order_by(Item.name)
    return list(db.exec(statement).all())
