from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.purchase_event import PurchaseEvent
from app.models.roll_event import RollEvent
from app.models.session import Session
from app.models.user import User
from app.schemas.session import (
    ActivityEvent,
    PurchaseActivityEvent,
    RollActivityEvent,
)

router = APIRouter()


@router.get("/sessions/{session_id}/activity", response_model=list[ActivityEvent])
def get_session_activity(
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

    started_at = entry.started_at or entry.created_at

    def offset(ts: datetime) -> int:
        if not started_at or not ts:
            return 0
        delta = (ts.replace(tzinfo=None) - started_at.replace(tzinfo=None)).total_seconds()
        return max(0, int(delta))

    events: list[ActivityEvent] = []

    rolls = session.exec(
        select(RollEvent, User)
        .outerjoin(User, RollEvent.user_id == User.id)
        .where(RollEvent.session_id == session_id)
        .order_by(RollEvent.created_at)
    ).all()
    for roll, roll_user in rolls:
        events.append(RollActivityEvent(
            userId=roll.user_id,
            username=roll_user.username if roll_user else None,
            displayName=(roll_user.display_name if roll_user else None) or roll.author_name,
            expression=roll.expression,
            results=roll.results,
            total=roll.total,
            label=roll.label,
            timestamp=roll.created_at,
            sessionOffsetSeconds=offset(roll.created_at),
        ))

    purchases = session.exec(
        select(PurchaseEvent, User)
        .outerjoin(User, PurchaseEvent.user_id == User.id)
        .where(PurchaseEvent.session_id == session_id)
        .order_by(PurchaseEvent.created_at)
    ).all()
    for purchase, purchase_user in purchases:
        events.append(PurchaseActivityEvent(
            userId=purchase.user_id,
            username=purchase_user.username if purchase_user else None,
            displayName=purchase_user.display_name if purchase_user else None,
            itemName=purchase.item_name,
            quantity=purchase.quantity,
            timestamp=purchase.created_at,
            sessionOffsetSeconds=offset(purchase.created_at),
        ))

    events.sort(key=lambda e: e.timestamp)
    return events
