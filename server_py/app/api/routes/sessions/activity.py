from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.purchase_event import PurchaseEvent
from app.models.roll_event import RollEvent
from app.models.session import Session
from app.models.session_command_event import SessionCommandEvent
from app.models.user import User
from app.schemas.session import (
    ActivityEvent,
    CombatActivityEvent,
    EntityActivityEvent,
    PurchaseActivityEvent,
    RollActivityEvent,
    RollRequestActivityEvent,
    ShopActivityEvent,
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

    commands = session.exec(
        select(SessionCommandEvent, User)
        .outerjoin(User, SessionCommandEvent.user_id == User.id)
        .where(SessionCommandEvent.session_id == session_id)
        .order_by(SessionCommandEvent.created_at)
    ).all()
    for command, command_user in commands:
        actor_name = (command_user.display_name if command_user else None) or command.actor_name
        payload = command.payload_json if isinstance(command.payload_json, dict) else {}
        if command.command_type in ("open_shop", "close_shop"):
            events.append(ShopActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                action="opened" if command.command_type == "open_shop" else "closed",
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue
        if command.command_type == "request_roll":
            mode = payload.get("mode") if payload.get("mode") in {"advantage", "disadvantage"} else None
            events.append(RollRequestActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                expression=str(payload.get("expression") or "d20"),
                reason=payload.get("reason") if isinstance(payload.get("reason"), str) else None,
                mode=mode,
                targetUserId=payload.get("targetUserId") if isinstance(payload.get("targetUserId"), str) else None,
                targetDisplayName=payload.get("targetDisplayName") if isinstance(payload.get("targetDisplayName"), str) else None,
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue
        if command.command_type in ("start_combat", "end_combat"):
            events.append(CombatActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                action="started" if command.command_type == "start_combat" else "ended",
                note=payload.get("note") if isinstance(payload.get("note"), str) else None,
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue
        if command.command_type in (
            "session_entity_added",
            "session_entity_removed",
            "entity_revealed",
            "entity_hidden",
            "entity_hp_updated",
        ):
            hp_delta = payload.get("hpDelta") if isinstance(payload.get("hpDelta"), int) else None
            if command.command_type == "session_entity_added":
                action = "added"
            elif command.command_type == "session_entity_removed":
                action = "removed"
            elif command.command_type == "entity_revealed":
                action = "revealed"
            elif command.command_type == "entity_hidden":
                action = "hidden"
            elif hp_delta is not None and hp_delta < 0:
                action = "damaged"
            elif hp_delta is not None and hp_delta > 0:
                action = "healed"
            else:
                action = "hp_set"
            events.append(EntityActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                action=action,
                entityName=payload.get("entityName") if isinstance(payload.get("entityName"), str) else "Entity",
                entityCategory=payload.get("entityCategory") if isinstance(payload.get("entityCategory"), str) else None,
                label=payload.get("label") if isinstance(payload.get("label"), str) else None,
                currentHp=payload.get("currentHp") if isinstance(payload.get("currentHp"), int) else None,
                previousHp=payload.get("previousHp") if isinstance(payload.get("previousHp"), int) else None,
                delta=abs(hp_delta) if hp_delta is not None else None,
                maxHp=payload.get("maxHp") if isinstance(payload.get("maxHp"), int) else None,
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue

    events.sort(key=lambda e: e.timestamp)
    return events
