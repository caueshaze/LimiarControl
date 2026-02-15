from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.models.item import Item
from app.models.user import User
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate

router = APIRouter()


def to_item_read(item: Item) -> ItemRead:
    return ItemRead(
        id=item.id,
        campaignId=item.campaign_id,
        name=item.name,
        type=item.type,
        description=item.description,
        price=item.price,
        weight=item.weight,
        damageDice=item.damage_dice,
        rangeMeters=item.range_meters,
        properties=item.properties,
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )


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
    item = Item(
        id=str(uuid4()),
        campaign_id=campaign_id,
        name=payload.name.strip(),
        type=payload.type,
        description=payload.description.strip(),
        price=payload.price,
        weight=payload.weight,
        damage_dice=payload.damageDice,
        range_meters=payload.rangeMeters,
        properties=payload.properties,
    )
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
    item.name = payload.name.strip()
    item.type = payload.type
    item.description = payload.description.strip()
    item.price = payload.price
    item.weight = payload.weight
    item.damage_dice = payload.damageDice
    item.range_meters = payload.rangeMeters
    item.properties = payload.properties
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
    session.delete(item)
    session.commit()
    return None
