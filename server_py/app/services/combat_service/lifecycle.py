from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel

from .exceptions import CombatServiceError, _roll_dice_expression


class CombatLifecycleMixin:
    _INITIATIVE_SKIPPED_STATUSES = {"dead", "defeated", "stable"}

    @classmethod
    def _participant_requires_initiative(cls, participant: dict) -> bool:
        return participant.get("status") not in cls._INITIATIVE_SKIPPED_STATUSES

    @classmethod
    def _maybe_activate_initiative_order(cls, state: CombatState) -> bool:
        if state.phase not in (CombatPhase.initiative, "initiative"):
            return False

        pending_participants = [
            participant
            for participant in state.participants
            if cls._participant_requires_initiative(participant)
        ]
        if any(participant.get("initiative") is None for participant in pending_participants):
            return False

        state.participants.sort(
            key=lambda participant: participant.get("initiative") or 0,
            reverse=True,
        )
        state.phase = CombatPhase.active
        state.round = 1
        state.current_turn_index = 0
        cls._reset_turn_resources(state.participants[0])
        return True

    @classmethod
    async def apply_initiative_roll(
        cls,
        db: Session,
        session_id: str,
        actor_kind: str,
        actor_ref_id: str,
        initiative: int,
    ) -> CombatState | None:
        state = cls.get_state(db, session_id)
        if not state or state.phase in (CombatPhase.ended, "ended"):
            return state
        if state.phase not in (CombatPhase.initiative, "initiative"):
            return state

        participant = next(
            (
                candidate
                for candidate in state.participants
                if candidate.get("ref_id") == actor_ref_id and candidate.get("kind") == actor_kind
            ),
            None,
        )
        if not participant or not cls._participant_requires_initiative(participant):
            return state

        participant["initiative"] = initiative
        transitioned_to_active = cls._maybe_activate_initiative_order(state)
        flag_modified(state, "participants")

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        if transitioned_to_active and state.participants:
            active_name = state.participants[0]["display_name"]
            await cls._emit_log(session_id, {"message": f"Initiative set! It is now {active_name}'s turn."})

        return state

    @classmethod
    async def start_combat(cls, db: Session, session_id: str, req: CombatStartRequest):
        state = cls.get_state(db, session_id)
        if state:
            db.delete(state)
            db.flush()

        new_state = CombatState(
            session_id=session_id,
            phase=CombatPhase.initiative,
            round=1,
            current_turn_index=0,
            participants=[
                {**p.model_dump(), "status": "active" if p.kind == "player" else ("active" if not getattr(p, "is_defeated", False) else "defeated")}
                for p in req.participants
            ],
        )
        db.add(new_state)
        cls._sync_all_participant_statuses(db, new_state)
        db.commit()
        db.refresh(new_state)
        await cls._emit_state(session_id, new_state)
        await cls._emit_log(session_id, {"message": "Combat started! Roll for initiative."})
        return new_state

    @classmethod
    async def set_initiative(cls, db: Session, session_id: str, req: CombatSetInitiativeRequest):
        state = cls.get_state(db, session_id)
        if not state:
            raise CombatServiceError("Combat not found", 404)
        if state.phase not in (CombatPhase.initiative, "initiative"):
            raise CombatServiceError("Combat is not in initiative phase")

        updates = {i.id: i.initiative for i in req.initiatives}
        for p in state.participants:
            if p["id"] in updates:
                p["initiative"] = updates[p["id"]]

        transitioned_to_active = cls._maybe_activate_initiative_order(state)
        flag_modified(state, "participants")
        
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        
        if transitioned_to_active:
            active_name = state.participants[0]["display_name"] if state.participants else "Unknown"
            await cls._emit_log(session_id, {"message": f"Initiative set! It is now {active_name}'s turn."})
        else:
            await cls._emit_log(session_id, {"message": "Initiative updated."})
        return state

    @classmethod
    async def next_turn(
        cls,
        db: Session,
        session_id: str,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
        skip_turn_end_validation: bool = False,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            actor_participant_id,
        )

        if not is_gm and not skip_turn_end_validation:
            if attacker.get("status") == "downed":
                raise CombatServiceError("You must roll a Death Save before ending your turn.", 403)
            cls._require_actor_status(attacker, ("active",), "You can only end your turn when active.")

        cls._clear_participant_pending_attack(attacker)
        flag_modified(state, "participants")

        if not state.participants:
            raise CombatServiceError("No participants")

        # --- Expire turn_end effects for the outgoing participant ---
        outgoing_p = state.participants[state.current_turn_index]
        expired_end = await cls._expire_effects_for_participant(
            session_id, state, outgoing_p["id"], "turn_end"
        )
        for exp in expired_end:
            label = exp.get("condition_type") or exp.get("kind", "effect")
            await cls._emit_log(session_id, {
                "message": f"Effect '{label}' expired on {exp['target_display_name']} (end of {outgoing_p['display_name']}'s turn).",
                "source": "effect_expired",
            })

        while True:
            state.current_turn_index += 1
            if state.current_turn_index >= len(state.participants):
                state.current_turn_index = 0
                state.round += 1
                await cls._emit_log(session_id, {"message": f"Round {state.round} started!"})
            
            p_status = state.participants[state.current_turn_index].get("status", "active")
            if p_status not in ("dead", "defeated", "stable"):
                break # Valid turn!
            if p_status == "stable":
                # stable ignores turn but stays in order implicitly. We just log skipping it.
                await cls._emit_log(session_id, {"message": f"Turn skipped for stable participant {state.participants[state.current_turn_index]['display_name']}."})
                continue
            # "dead" and "defeated" are completely skipped silently in terms of explicit turn messages, they just pass.

        # --- Expire turn_start effects for the incoming participant ---
        incoming_p = state.participants[state.current_turn_index]
        expired_start = await cls._expire_effects_for_participant(
            session_id, state, incoming_p["id"], "turn_start"
        )
        for exp in expired_start:
            label = exp.get("condition_type") or exp.get("kind", "effect")
            await cls._emit_log(session_id, {
                "message": f"Effect '{label}' expired on {exp['target_display_name']} (start of {incoming_p['display_name']}'s turn).",
                "source": "effect_expired",
            })

        # --- Reset turn resources for the incoming participant ---
        cls._reset_turn_resources(incoming_p)

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        active_p = state.participants[state.current_turn_index]
        active_name = active_p["display_name"]
        
        # Determine specific action required
        if active_p.get("status") == "downed":
            await cls._emit_log(session_id, {"message": f"It is now {active_name}'s turn. They are downed and must roll a Death Save."})
        else:
            await cls._emit_log(session_id, {"message": f"It is now {active_name}'s turn."})
            
        return state

    @classmethod
    async def end_combat(cls, db: Session, session_id: str, is_gm: bool):
        if not is_gm:
            raise CombatServiceError("Only GM can end combat", 403)
        state = cls.get_state(db, session_id)
        if not state:
            raise CombatServiceError("Combat not found", 404)
        
        state.phase = CombatPhase.ended
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(session_id, {"message": "Combat ended."})
        return state
