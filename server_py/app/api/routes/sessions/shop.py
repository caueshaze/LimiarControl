from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.purchase_event import PurchaseEvent
from app.models.session import Session, SessionStatus
from app.schemas.inventory import InventoryBuy, InventoryRead
from app.schemas.item import ItemRead
from ._shared import to_inventory_read, to_item_read

router = APIRouter()


@router.get("/sessions/{session_id}/shop/items", response_model=list[ItemRead])
def list_session_shop_items(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    items = session.exec(
        select(Item).where(Item.campaign_id == entry.campaign_id)
        .order_by(Item.created_at.desc())
    ).all()
    return [to_item_read(item) for item in items]


@router.post("/sessions/{session_id}/shop/buy", response_model=InventoryRead, status_code=201)
def buy_session_shop_item(
    session_id: str,
    payload: InventoryBuy,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    item = session.exec(select(Item).where(Item.id == payload.itemId)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.campaign_id != entry.campaign_id:
        raise HTTPException(status_code=400, detail="Item does not belong to campaign")
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    session.add(PurchaseEvent(
        id=str(uuid4()),
        session_id=session_id,
        user_id=user.id,
        member_id=member.id,
        item_id=payload.itemId,
        item_name=item.name,
        quantity=payload.quantity,
    ))

    existing = session.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == entry.party_id,
            InventoryItem.member_id == member.id,
            InventoryItem.item_id == payload.itemId,
        )
    ).first()

    if existing:
        existing.quantity += payload.quantity
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return to_inventory_read(existing)

    new_entry = InventoryItem(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        party_id=entry.party_id,
        member_id=member.id,
        item_id=payload.itemId,
        quantity=payload.quantity,
        is_equipped=False,
        notes=None,
    )
    session.add(new_entry)
    session.commit()
    session.refresh(new_entry)
    return to_inventory_read(new_entry)
