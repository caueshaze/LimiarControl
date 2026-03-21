from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.api.serializers.item import to_item_read
from app.db.session import get_session
from app.models.base_item import BaseItemKind
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.item import ItemType
from app.models.user import User
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.services.item_properties import normalize_item_properties

router = APIRouter()

def _infer_item_kind(item_type: ItemType) -> BaseItemKind | None:
    if item_type == ItemType.WEAPON:
        return BaseItemKind.WEAPON
    if item_type == ItemType.ARMOR:
        return BaseItemKind.ARMOR
    if item_type == ItemType.CONSUMABLE:
        return BaseItemKind.CONSUMABLE
    return None


def _apply_item_payload(item: Item, payload: ItemCreate | ItemUpdate) -> None:
    item.name = payload.name
    item.type = payload.type
    item.description = payload.description
    item.price = payload.price
    item.weight = payload.weight
    item.damage_dice = payload.damageDice
    item.damage_type = payload.damageType
    item.range_meters = payload.rangeMeters
    item.range_long_meters = payload.rangeLongMeters
    item.versatile_damage = payload.versatileDamage
    item.weapon_category = payload.weaponCategory
    item.weapon_range_type = payload.weaponRangeType
    item.armor_category = payload.armorCategory
    item.armor_class_base = payload.armorClassBase
    item.dex_bonus_rule = payload.dexBonusRule
    item.strength_requirement = payload.strengthRequirement
    item.stealth_disadvantage = payload.stealthDisadvantage
    item.is_shield = payload.isShield
    item.properties = payload.properties
    if item.is_custom:
        item.item_kind = _infer_item_kind(payload.type)
        item.name_en_snapshot = payload.name
        item.name_pt_snapshot = payload.name


@router.get("/{campaign_id}/items", response_model=List[ItemRead])
def list_items(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_campaign_member(campaign_id, user, session)
    statement = select(Item).where(Item.campaign_id == campaign_id).order_by(
        Item.created_at.desc()
    )
    items = session.exec(statement).all()
    return [to_item_read(item) for item in items]


@router.post("/{campaign_id}/items", response_model=ItemRead, status_code=201)
def create_item(
    campaign_id: str,
    payload: ItemCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    if not payload.name.strip() or not payload.description.strip():
        raise HTTPException(status_code=400, detail="Invalid payload")
    normalized_properties, invalid_properties = normalize_item_properties(payload.properties)
    if invalid_properties:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid item properties: {', '.join(invalid_properties)}",
        )
    payload.properties = normalized_properties
    item = Item(
        id=str(uuid4()),
        campaign_id=campaign_id,
        is_custom=True,
    )
    _apply_item_payload(item, payload)
    session.add(item)
    session.commit()
    session.refresh(item)
    return to_item_read(item)


@router.put("/{campaign_id}/items/{item_id}", response_model=ItemRead)
def update_item(
    campaign_id: str,
    item_id: str,
    payload: ItemUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    item = session.exec(
        select(Item).where(Item.id == item_id, Item.campaign_id == campaign_id)
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not payload.name.strip() or not payload.description.strip():
        raise HTTPException(status_code=400, detail="Invalid payload")
    normalized_properties, invalid_properties = normalize_item_properties(payload.properties)
    if invalid_properties:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid item properties: {', '.join(invalid_properties)}",
        )
    payload.properties = normalized_properties
    _apply_item_payload(item, payload)
    session.add(item)
    session.commit()
    session.refresh(item)
    return to_item_read(item)


@router.delete("/{campaign_id}/items/{item_id}", status_code=204)
def delete_item(
    campaign_id: str,
    item_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    item = session.exec(
        select(Item).where(Item.id == item_id, Item.campaign_id == campaign_id)
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.base_item_id:
        raise HTTPException(
            status_code=409,
            detail="Base campaign items cannot be deleted because character-sheet automation depends on stable ids",
        )
    in_use = session.exec(
        select(InventoryItem.id).where(
            InventoryItem.campaign_id == campaign_id,
            InventoryItem.item_id == item_id,
        )
    ).first()
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Item cannot be deleted because it is already present in a character inventory",
        )
    session.delete(item)
    session.commit()
    return None
