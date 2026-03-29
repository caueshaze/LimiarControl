from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.session import SessionStatus
from app.schemas.session_consumable import (
    SessionHealingConsumableTargetRead,
    SessionUseConsumableRead,
    SessionUseConsumableRequest,
)
from app.services.healing_consumables import (
    HealingConsumableError,
    apply_healing_outside_combat,
    build_consumable_used_payload,
    consume_inventory_item,
    get_session_entry,
    list_healing_consumable_targets,
    publish_consumable_used_realtime,
    record_consumable_used_activity,
    require_valid_healing_target,
    resolve_healing_consumable,
    roll_healing_consumable,
)

from ._shared import get_or_create_session_runtime
from .state_common import publish_state_update

router = APIRouter()


def _require_active_non_combat_session(session_id: str, session: DbSession):
    session_entry = get_session_entry(session, session_id)
    if session_entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    runtime = get_or_create_session_runtime(session_id, session)
    if runtime.combat_active:
        raise HTTPException(status_code=400, detail="Healing consumables are unavailable during combat")

    return session_entry


@router.get(
    "/sessions/{session_id}/consumables/healing-targets",
    response_model=list[SessionHealingConsumableTargetRead],
)
def list_session_healing_consumable_targets(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _require_active_non_combat_session(session_id, session)
    try:
        require_valid_healing_target(
            session,
            session_entry=session_entry,
            actor_user_id=user.id,
            target_user_id=user.id,
        )
        targets = list_healing_consumable_targets(
            session,
            session_entry=session_entry,
            actor_user_id=user.id,
        )
    except HealingConsumableError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    return [
        SessionHealingConsumableTargetRead(
            playerUserId=target.player_user_id,
            displayName=target.display_name,
            currentHp=target.current_hp,
            maxHp=target.max_hp,
            isSelf=target.is_self,
        )
        for target in targets
    ]


@router.post(
    "/sessions/{session_id}/consumables/use",
    response_model=SessionUseConsumableRead,
)
async def use_session_healing_consumable(
    session_id: str,
    payload: SessionUseConsumableRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    session_entry = _require_active_non_combat_session(session_id, session)
    target_user_id = payload.targetPlayerUserId or user.id

    try:
        context = resolve_healing_consumable(
            session,
            session_entry=session_entry,
            actor_user_id=user.id,
            inventory_item_id=payload.inventoryItemId,
        )
        target_member = require_valid_healing_target(
            session,
            session_entry=session_entry,
            actor_user_id=user.id,
            target_user_id=target_user_id,
        )
        healing_roll = roll_healing_consumable(
            context.item,
            roll_source=payload.rollSource,
            manual_rolls=payload.manualRolls,
        )
        application = apply_healing_outside_combat(
            session,
            session_entry=session_entry,
            target_user_id=target_user_id,
            amount=healing_roll.total_healing,
        )
        remaining_quantity = consume_inventory_item(session, context.inventory_item)
    except HealingConsumableError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error

    timestamp = datetime.now(timezone.utc)
    event_payload = build_consumable_used_payload(
        context=context,
        target_kind="player",
        target_ref_id=target_user_id,
        target_user_id=target_user_id,
        target_display_name=target_member.display_name,
        healing=healing_roll.total_healing,
        new_hp=application.new_hp,
        previous_hp=application.previous_hp,
        max_hp=application.max_hp,
        remaining_quantity=remaining_quantity,
        roll=healing_roll,
        timestamp=timestamp,
    )
    record_consumable_used_activity(
        session,
        context=context,
        payload=event_payload,
        created_at=timestamp,
    )
    session.commit()
    session.refresh(application.state_model)

    await publish_state_update(
        session_entry,
        target_user_id,
        application.state_model.updated_at or application.state_model.created_at or timestamp,
        application.state_model.state_json if isinstance(application.state_model.state_json, dict) else None,
    )
    await publish_consumable_used_realtime(
        session_entry,
        payload=event_payload,
        timestamp=timestamp,
    )

    return SessionUseConsumableRead(
        sessionId=session_id,
        campaignId=session_entry.campaign_id,
        partyId=session_entry.party_id,
        actorUserId=user.id,
        targetPlayerUserId=target_user_id,
        inventoryItemId=context.inventory_item.id,
        itemId=context.item.id,
        itemName=context.item.name,
        targetDisplayName=application.target_display_name,
        healingApplied=healing_roll.total_healing,
        newHp=application.new_hp,
        maxHp=application.max_hp,
        remainingQuantity=remaining_quantity,
        effectDice=healing_roll.effect_dice,
        effectBonus=healing_roll.effect_bonus,
        effectRolls=healing_roll.effect_rolls,
        effectRollSource=healing_roll.roll_source,
    )
