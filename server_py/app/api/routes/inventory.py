from datetime import date
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.api.deprecation import log_deprecated_route
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.user import User
from app.schemas.inventory import InventoryBuy, InventoryRead, InventoryUpdate

router = APIRouter()
DEPRECATION_REMOVAL_DATE = date(2026, 6, 1)


def to_inventory_read(entry: InventoryItem) -> InventoryRead:
    return InventoryRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        memberId=entry.member_id,
        itemId=entry.item_id,
        quantity=entry.quantity,
        isEquipped=entry.is_equipped,
        notes=entry.notes,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


@router.get("/{campaign_id}/inventory", response_model=list[InventoryRead])
def list_inventory(
    campaign_id: str,
    memberId: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    target_member_id = member.id
    if member.role_mode == RoleMode.GM and memberId:
        target_member_id = memberId
    statement = select(InventoryItem).where(
        InventoryItem.campaign_id == campaign_id,
        InventoryItem.member_id == target_member_id,
    )
    entries = session.exec(statement).all()
    return [to_inventory_read(entry) for entry in entries]


@router.post(
    "/{campaign_id}/inventory/buy",
    response_model=InventoryRead,
    status_code=201,
    deprecated=True,
)
def buy_item(
    campaign_id: str,
    payload: InventoryBuy,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/sessions/{session_id}/shop/buy."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/inventory/buy",
        new_path="/api/sessions/{session_id}/shop/buy",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    active = session.exec(
        select(CampaignSession).where(
            CampaignSession.campaign_id == campaign_id,
            CampaignSession.status == SessionStatus.ACTIVE,
        )
    ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    item = session.exec(select(Item).where(Item.id == payload.itemId)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Item does not belong to campaign")
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    existing = session.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == campaign_id,
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

    entry = InventoryItem(
        id=str(uuid4()),
        campaign_id=campaign_id,
        member_id=member.id,
        item_id=payload.itemId,
        quantity=payload.quantity,
        is_equipped=False,
        notes=None,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_inventory_read(entry)


@router.patch("/{campaign_id}/inventory/{inv_id}", response_model=InventoryRead)
def update_inventory(
    campaign_id: str,
    inv_id: str,
    payload: InventoryUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    entry = session.exec(
        select(InventoryItem).where(
            InventoryItem.id == inv_id, InventoryItem.campaign_id == campaign_id
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if member.role_mode != RoleMode.GM and entry.member_id != member.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if payload.quantity is not None:
        if payload.quantity < 1:
            raise HTTPException(status_code=400, detail="Invalid quantity")
        entry.quantity = payload.quantity
    if payload.isEquipped is not None:
        entry.is_equipped = payload.isEquipped
    if payload.notes is not None:
        entry.notes = payload.notes
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_inventory_read(entry)


@router.delete("/{campaign_id}/inventory/{inv_id}", status_code=204)
def delete_inventory(
    campaign_id: str,
    inv_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    entry = session.exec(
        select(InventoryItem).where(
            InventoryItem.id == inv_id, InventoryItem.campaign_id == campaign_id
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if member.role_mode != RoleMode.GM and entry.member_id != member.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    session.delete(entry)
    session.commit()
    return None
