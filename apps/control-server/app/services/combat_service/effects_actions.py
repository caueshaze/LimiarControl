from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.combat import (
    CombatApplyEffectRequest,
    CombatConsumeReactionRequest,
    CombatReactionRequestRequest,
    CombatReactionResolveRequest,
    CombatRemoveEffectRequest,
)

from .effects_core import CombatEffectsCoreMixin
from .exceptions import CombatServiceError


class CombatEffectsActionsMixin(CombatEffectsCoreMixin):
    @classmethod
    def _consume_turn_resource(cls, participant: dict, cost: str, *, is_gm: bool = False, override_resource_limit: bool = False) -> bool:
        if cost == "free":
            return False
        resources = cls._get_turn_resources(participant)
        key = f"{cost}_used"
        if key not in resources:
            raise CombatServiceError(f"Unknown action cost: {cost}")
        if resources.get(key):
            label = cost.replace("_", " ")
            if not is_gm:
                raise CombatServiceError(f"Your {label} has already been used this turn.", 403)
            if not override_resource_limit:
                raise CombatServiceError(f"This entity has already used its {label} this turn.", 409)
            return True
        resources[key] = True
        participant["turn_resources"] = resources
        return False

    @classmethod
    async def apply_effect(cls, db: Session, session_id: str, req: CombatApplyEffectRequest) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        target = next((participant for participant in state.participants if participant["id"] == req.target_participant_id), None)
        if not target:
            raise CombatServiceError("Target participant not found in combat", 404)
        if req.kind == "condition" and not req.condition_type:
            raise CombatServiceError("condition_type is required when kind is 'condition'")
        if req.kind in ("temp_ac_bonus", "attack_bonus", "damage_bonus") and req.numeric_value is None:
            raise CombatServiceError(f"numeric_value is required for kind '{req.kind}'")
        if req.duration_type == "rounds" and not req.remaining_rounds:
            raise CombatServiceError("remaining_rounds is required for duration_type 'rounds'")
        expires_on = "turn_start" if req.duration_type in ("until_turn_start", "rounds") else ("turn_end" if req.duration_type == "until_turn_end" else None)
        effect = {
            "id": str(uuid4()),
            "source_participant_id": req.source_participant_id,
            "kind": req.kind,
            "condition_type": req.condition_type if req.kind == "condition" else None,
            "numeric_value": req.numeric_value,
            "duration_type": req.duration_type,
            "remaining_rounds": req.remaining_rounds,
            "expires_on": expires_on,
            "expires_at_participant_id": req.expires_at_participant_id or req.target_participant_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": req.metadata,
            "display_label": req.display_label,
        }
        effects = cls._get_participant_effects(target)
        effects.append(effect)
        cls._set_participant_effects(target, effects)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(session_id, {"message": f"Effect '{cls._effect_label(effect)}' applied to {target['display_name']}.", "source": "effect_applied"})
        return state

    @classmethod
    async def remove_effect(cls, db: Session, session_id: str, req: CombatRemoveEffectRequest) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        target = next((participant for participant in state.participants if participant["id"] == req.target_participant_id), None)
        if not target:
            raise CombatServiceError("Target participant not found in combat", 404)
        removed = None
        keep = []
        for effect in cls._get_participant_effects(target):
            if effect.get("id") == req.effect_id and removed is None:
                removed = effect
            else:
                keep.append(effect)
        if not removed:
            raise CombatServiceError("Effect not found on this participant", 404)
        cls._set_participant_effects(target, keep)
        removed_effects = [removed]
        removed_metadata = cls._get_effect_metadata(removed)
        if removed_metadata.get("concentration") is True and isinstance(removed_metadata.get("concentration_group"), str):
            group_result = cls._remove_effect_group(state, concentration_group=removed_metadata["concentration_group"])
            removed_effects.extend(group_result["removed_effects"])
            cls._sync_area_effects_if_changed(session_id, state, group_result["removed_area_effects"])
        cls._execute_on_end_effects_for_removed(
            state=state,
            removed_effects=removed_effects,
        )
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(session_id, {"message": f"Effect '{cls._effect_label(removed)}' removed from {target['display_name']}.", "source": "effect_removed"})
        if target.get("kind") == "player":
            from .persistent_effects import sync_effect_removal_to_state_json
            sync_effect_removal_to_state_json(db, session_id, target, removed.get("id"))
        return state

    @classmethod
    async def consume_reaction(cls, db: Session, session_id: str, req: CombatConsumeReactionRequest, actor_user_id: str, is_gm: bool) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        target = next((participant for participant in state.participants if participant["id"] == req.participant_id), None)
        if not target:
            raise CombatServiceError("Participant not found in combat", 404)
        if not is_gm and target.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("You can only mark your own reaction as used", 403)
        cls._require_actor_status(target, ("active",), "Only active participants can use reactions.")
        was_overridden = cls._consume_turn_resource(target, "reaction", is_gm=is_gm, override_resource_limit=req.override_resource_limit)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        message = f"{target['display_name']} used their reaction."
        if was_overridden:
            message = f"[OVERRIDE: Reaction limit ignored] {message}"
        await cls._emit_log(session_id, {"message": message, "source": "reaction_consumed", "is_override": was_overridden, "overridden_resource": "reaction" if was_overridden else None})
        return state

    @classmethod
    async def request_reaction(cls, db: Session, session_id: str, req: CombatReactionRequestRequest, actor_user_id: str) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        target = next((participant for participant in state.participants if participant["id"] == req.actor_participant_id), None)
        if not target:
            raise CombatServiceError("Participant not found in combat", 404)
        if target.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("You can only request reaction for your own character", 403)
        cls._require_actor_status(target, ("active",), "Only active participants can request reactions.")
        target["reaction_request"] = {"status": "pending", "requested_at": datetime.now(timezone.utc).isoformat()}
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(session_id, {"message": f"{target['display_name']} solicitou o uso da Reação e aguarda aprovação do GM.", "source": "reaction_requested"})
        return state

    @classmethod
    async def resolve_reaction(cls, db: Session, session_id: str, req: CombatReactionResolveRequest) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        target = next((participant for participant in state.participants if participant["id"] == req.actor_participant_id), None)
        if not target:
            raise CombatServiceError("Participant not found in combat", 404)
        req_status = target.get("reaction_request", {}).get("status")
        if req_status != "pending":
            raise CombatServiceError("No pending reaction request found for this participant", 400)
        if req.decision == "approve":
            was_overridden = cls._consume_turn_resource(target, "reaction", is_gm=True, override_resource_limit=req.override_resource_limit)
            target["reaction_request"]["status"] = "approved"
            source = "reaction_approved"
            message = f"{target['display_name']}'s reaction request was approved and consumed."
            if was_overridden:
                message = f"[OVERRIDE: Reaction limit ignored] {message}"
            extra = {"is_override": was_overridden, "overridden_resource": "reaction" if was_overridden else None}
        elif req.decision == "deny":
            target["reaction_request"]["status"] = "denied"
            source = "reaction_denied"
            message = f"{target['display_name']}'s reaction request was denied."
            extra = {}
        else:
            raise CombatServiceError("Invalid decision", 400)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(session_id, {"message": message, "source": source, **extra})
        return state
