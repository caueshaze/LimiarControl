from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.item import Item
from app.models.purchase_event import PurchaseEvent
from app.models.roll_event import RollEvent
from app.models.session import Session
from app.models.session_command_event import SessionCommandEvent
from app.models.user import User
from app.schemas.session import (
    ActivityEvent,
    CombatActivityEvent,
    ConsumableActivityEvent,
    EntityActivityEvent,
    HitDiceActivityEvent,
    LevelUpActivityEvent,
    PlayerHpActivityEvent,
    PurchaseActivityEvent,
    RestActivityEvent,
    RewardActivityEvent,
    RollActivityEvent,
    RollRequestActivityEvent,
    RollResolvedActivityEvent,
    ShopActivityEvent,
)
from .shop import _format_cp_label, _price_to_cp

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
        select(PurchaseEvent, User, Item)
        .outerjoin(User, PurchaseEvent.user_id == User.id)
        .outerjoin(Item, PurchaseEvent.item_id == Item.id)
        .where(PurchaseEvent.session_id == session_id)
        .order_by(PurchaseEvent.created_at)
    ).all()
    for purchase, purchase_user, purchase_item in purchases:
        events.append(PurchaseActivityEvent(
            userId=purchase.user_id,
            username=purchase_user.username if purchase_user else None,
            displayName=purchase_user.display_name if purchase_user else None,
            action="bought",
            itemName=purchase.item_name,
            quantity=purchase.quantity,
            amountLabel=_format_cp_label(_price_to_cp(purchase_item.price if purchase_item else None, purchase.quantity)),
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
        if command.command_type == "shop_sale":
            events.append(PurchaseActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                action="sold",
                itemName=str(payload.get("itemName") or "Item"),
                quantity=int(payload.get("quantity", 1) or 1),
                amountLabel=payload.get("amountLabel") if isinstance(payload.get("amountLabel"), str) else None,
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
                rollType=payload.get("rollType") if isinstance(payload.get("rollType"), str) else None,
                ability=payload.get("ability") if isinstance(payload.get("ability"), str) else None,
                skill=payload.get("skill") if isinstance(payload.get("skill"), str) else None,
                dc=payload.get("dc") if isinstance(payload.get("dc"), int) else None,
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
        if command.command_type in ("start_short_rest", "start_long_rest", "end_rest"):
            rest_type = payload.get("restType") if isinstance(payload.get("restType"), str) else None
            if command.command_type == "start_short_rest":
                action = "short_started"
            elif command.command_type == "start_long_rest":
                action = "long_started"
            elif rest_type == "long_rest":
                action = "long_ended"
            else:
                action = "short_ended"
            events.append(RestActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                action=action,
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue
        if command.command_type in ("grant_currency", "grant_item", "grant_xp"):
            if command.command_type == "grant_currency":
                action = "currency"
            elif command.command_type == "grant_item":
                action = "item"
            else:
                action = "xp"
            events.append(RewardActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                action=action,
                targetUserId=payload.get("targetUserId") if isinstance(payload.get("targetUserId"), str) else None,
                targetDisplayName=payload.get("targetDisplayName") if isinstance(payload.get("targetDisplayName"), str) else None,
                amountLabel=payload.get("amountLabel") if isinstance(payload.get("amountLabel"), str) else None,
                itemName=payload.get("itemName") if isinstance(payload.get("itemName"), str) else None,
                quantity=payload.get("quantity") if isinstance(payload.get("quantity"), int) else None,
                currentXp=payload.get("currentXp") if isinstance(payload.get("currentXp"), int) else None,
                nextLevelThreshold=payload.get("nextLevelThreshold") if isinstance(payload.get("nextLevelThreshold"), int) else None,
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue
        if command.command_type in ("level_up_requested", "level_up_approved", "level_up_denied"):
            if command.command_type == "level_up_requested":
                action = "requested"
            elif command.command_type == "level_up_approved":
                action = "approved"
            else:
                action = "denied"
            events.append(LevelUpActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                action=action,
                targetUserId=payload.get("targetUserId") if isinstance(payload.get("targetUserId"), str) else None,
                targetDisplayName=payload.get("targetDisplayName") if isinstance(payload.get("targetDisplayName"), str) else None,
                level=int(payload.get("level", 1) or 1),
                experiencePoints=int(payload.get("experiencePoints", 0) or 0),
                pendingLevelUp=bool(payload.get("pendingLevelUp", False)),
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue
        if command.command_type == "hit_dice_used":
            events.append(HitDiceActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                roll=int(payload.get("roll", 0) or 0),
                healingApplied=int(payload.get("healingApplied", 0) or 0),
                currentHp=int(payload.get("currentHp", 0) or 0),
                maxHp=payload.get("maxHp") if isinstance(payload.get("maxHp"), int) else None,
                hitDiceRemaining=int(payload.get("hitDiceRemaining", 0) or 0),
                hitDiceTotal=int(payload.get("hitDiceTotal", 0) or 0),
                hitDieType=str(payload.get("hitDieType") or ""),
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue
        if command.command_type == "use_consumable":
            target_kind = payload.get("targetKind")
            events.append(ConsumableActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                itemName=payload.get("itemName") if isinstance(payload.get("itemName"), str) else "Consumable",
                targetUserId=payload.get("targetUserId") if isinstance(payload.get("targetUserId"), str) else None,
                targetDisplayName=payload.get("targetDisplayName") if isinstance(payload.get("targetDisplayName"), str) else None,
                targetKind=target_kind if target_kind in {"player", "session_entity"} else "player",
                healingApplied=int(payload.get("healingApplied", 0) or 0),
                newHp=payload.get("newHp") if isinstance(payload.get("newHp"), int) else None,
                maxHp=payload.get("maxHp") if isinstance(payload.get("maxHp"), int) else None,
                remainingQuantity=payload.get("remainingQuantity") if isinstance(payload.get("remainingQuantity"), int) else None,
                effectDice=payload.get("effectDice") if isinstance(payload.get("effectDice"), str) else None,
                effectRolls=payload.get("effectRolls") if isinstance(payload.get("effectRolls"), list) else [],
                effectRollSource=payload.get("effectRollSource") if payload.get("effectRollSource") in {"system", "manual"} else None,
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue
        if command.command_type == "player_hp_updated":
            delta = payload.get("delta") if isinstance(payload.get("delta"), int) else None
            if delta is not None and delta < 0:
                action = "damaged"
            elif delta is not None and delta > 0:
                action = "healed"
            else:
                action = "hp_set"
            events.append(PlayerHpActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                action=action,
                targetUserId=payload.get("targetUserId") if isinstance(payload.get("targetUserId"), str) else None,
                targetDisplayName=payload.get("targetDisplayName") if isinstance(payload.get("targetDisplayName"), str) else None,
                currentHp=payload.get("currentHp") if isinstance(payload.get("currentHp"), int) else None,
                previousHp=payload.get("previousHp") if isinstance(payload.get("previousHp"), int) else None,
                delta=abs(delta) if delta is not None else None,
                maxHp=payload.get("maxHp") if isinstance(payload.get("maxHp"), int) else None,
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
        if command.command_type == "roll_resolved":
            events.append(RollResolvedActivityEvent(
                userId=command.user_id,
                username=command_user.username if command_user else None,
                displayName=actor_name,
                rollType=payload.get("roll_type") or "ability",
                actorName=payload.get("actor_display_name") or actor_name or "",
                actorKind=payload.get("actor_kind") or "player",
                ability=payload.get("ability"),
                skill=payload.get("skill"),
                rolls=payload.get("rolls") if isinstance(payload.get("rolls"), list) else [],
                selectedRoll=int(payload.get("selected_roll", 0) or 0),
                total=int(payload.get("total", 0) or 0),
                modifierUsed=int(payload.get("modifier_used", 0) or 0),
                advantageMode=payload.get("advantage_mode") or "normal",
                dc=payload.get("dc") if isinstance(payload.get("dc"), int) else None,
                targetAc=payload.get("target_ac") if isinstance(payload.get("target_ac"), int) else None,
                success=payload.get("success") if isinstance(payload.get("success"), bool) else None,
                isGmRoll=bool(payload.get("is_gm_roll", False)),
                timestamp=command.created_at,
                sessionOffsetSeconds=offset(command.created_at),
            ))
            continue

    events.sort(key=lambda e: e.timestamp)
    return events
