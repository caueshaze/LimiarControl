from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.base_item import BaseItem, BaseItemKind
from app.models.campaign import SystemType
from app.models.user import User
from app.schemas.base_item import BaseItemRead
from app.services.base_items import (
    get_base_item_by_id,
    list_base_items as list_catalog_base_items,
)

router = APIRouter()


def to_base_item_read(item: BaseItem) -> BaseItemRead:
    return BaseItemRead(
        id=item.id,
        system=item.system,
        canonicalKey=item.canonical_key,
        nameEn=item.name_en,
        namePt=item.name_pt,
        descriptionEn=item.description_en,
        descriptionPt=item.description_pt,
        itemKind=item.item_kind,
        equipmentCategory=item.equipment_category,
        costQuantity=item.cost_quantity,
        costUnit=item.cost_unit,
        weight=item.weight,
        weaponCategory=item.weapon_category,
        weaponRangeType=item.weapon_range_type,
        damageDice=item.damage_dice,
        damageType=item.damage_type,
        rangeNormal=item.range_normal,
        rangeLong=item.range_long,
        versatileDamage=item.versatile_damage,
        weaponPropertiesJson=item.weapon_properties_json,
        armorCategory=item.armor_category,
        armorClassBase=item.armor_class_base,
        dexBonusRule=item.dex_bonus_rule,
        strengthRequirement=item.strength_requirement,
        stealthDisadvantage=item.stealth_disadvantage,
        isShield=item.is_shield,
        source=item.source,
        sourceRef=item.source_ref,
        isSrd=item.is_srd,
        isActive=item.is_active,
        aliases=[],
    )


@router.get("", response_model=list[BaseItemRead])
def list_base_items(
    system: SystemType | None = None,
    item_kind: BaseItemKind | None = None,
    canonical_key: str | None = None,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    items = list_catalog_base_items(
        db=session,
        system=system,
        item_kind=item_kind,
        canonical_key=canonical_key,
    )
    return [to_base_item_read(item) for item in items]


@router.get("/{base_item_id}", response_model=BaseItemRead)
def get_base_item(
    base_item_id: str,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = get_base_item_by_id(db=session, base_item_id=base_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Base item not found")

    return to_base_item_read(item)
