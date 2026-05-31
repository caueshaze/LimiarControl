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
from app.services.roll_resolution import resolve_ability_check

from .condition_effects_predicates import (
    has_condition_immunity,
    is_reaction_blocked,
    resolve_check_advantage_mode,
)
from .effects_core import CombatEffectsCoreMixin
from .exceptions import CombatServiceError
from .host_protocol import CombatServiceHostProtocol


class CombatEffectsActionsMixin(CombatEffectsCoreMixin, CombatServiceHostProtocol):
    @classmethod
    async def resolve_condition_escape_action(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_participant_id: str | None,
        actor_user_id: str,
        is_gm: bool,
        condition_type: str,
        source_effect_id: str | None = None,
        roll_source: str = "system",
        manual_roll: int | None = None,
        manual_rolls: list[int] | None = None,
        override_resource_limit: bool = False,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)

        actor = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            actor_participant_id,
        )
        cls._require_actor_status(
            actor,
            ("active",),
            "Only active participants can attempt an escape action.",
        )

        normalized_condition = str(condition_type or "").strip().lower()
        if normalized_condition != "restrained":
            raise CombatServiceError("This endpoint currently supports only restrained escapes.", 400)

        candidate_effects: list[dict] = []
        for effect in cls._get_participant_effects(actor):
            if effect.get("kind") != "condition":
                continue
            if str(effect.get("condition_type") or "").strip().lower() != "restrained":
                continue
            metadata = cls._get_effect_metadata(effect)
            if str(metadata.get("source_spell_key") or "").strip().lower() != "entangle":
                continue
            if metadata.get("escape_action") is not True:
                continue
            if isinstance(source_effect_id, str) and source_effect_id.strip():
                if metadata.get("source_effect_id") != source_effect_id.strip():
                    continue
            candidate_effects.append(effect)

        if not candidate_effects:
            raise CombatServiceError(
                "Actor is not restrained by a matching Entangle source.",
                400,
            )

        escape_effect = candidate_effects[0]
        escape_metadata = cls._get_effect_metadata(escape_effect)
        escape_dc = cls._safe_int(escape_metadata.get("escape_check_dc"), 0)
        if escape_dc <= 0:
            raise CombatServiceError("Escape DC is missing or invalid for this condition.", 400)

        # Action cost is consumed only after we confirmed this is a valid escape attempt.
        was_overridden = cls._consume_turn_resource(
            actor,
            "action",
            is_gm=is_gm,
            override_resource_limit=override_resource_limit,
        )

        advantage_mode = resolve_check_advantage_mode(
            actor,
            "strength",
            manual_mode="normal",
        )
        roll_result = resolve_ability_check(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                actor["ref_id"],
                actor["kind"],
                actor["display_name"],
            ),
            "strength",
            advantage_mode=advantage_mode,
            dc=escape_dc,
            roll_source=roll_source,
            manual_roll=manual_roll,
            manual_rolls=manual_rolls,
        )
        cls._apply_roll_dice_modifiers_for_actor(
            db,
            session_id,
            actor_kind=actor["kind"],
            actor_ref_id=actor["ref_id"],
            roll_result=roll_result,
            roll_type="ability",
        )
        roll_result.is_gm_roll = is_gm
        escaped = bool(roll_result.success)

        if escaped:
            remaining = [
                effect
                for effect in cls._get_participant_effects(actor)
                if effect.get("id") != escape_effect.get("id")
            ]
            cls._set_participant_effects(actor, remaining)

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        source_spell_name = escape_metadata.get("source_spell_name") or "Entangle"
        if escaped:
            message = (
                f"{actor['display_name']} usou a ação para escapar de {source_spell_name}: "
                f"teste de Força {roll_result.total} vs DC {escape_dc} (sucesso)."
            )
        else:
            message = (
                f"{actor['display_name']} usou a ação para escapar de {source_spell_name}: "
                f"teste de Força {roll_result.total} vs DC {escape_dc} (falha)."
            )
        if was_overridden:
            message = f"[OVERRIDE: Action limit ignored] {message}"
        await cls._emit_log(
            session_id,
            {
                "message": message,
                "source": "condition_escape",
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )

        return {
            "conditionType": "restrained",
            "sourceSpellKey": "entangle",
            "sourceEffectId": escape_metadata.get("source_effect_id"),
            "escapeCheck": {
                "ability": "strength",
                "dc": escape_dc,
                "success": escaped,
                "total": roll_result.total,
                "rollResult": roll_result,
            },
            "conditionRemoved": escaped,
            "actionConsumed": True,
            "isOverride": was_overridden,
        }

    @classmethod
    async def resolve_condition_wake_action(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_participant_id: str | None,
        target_ref_id: str,
        actor_user_id: str,
        is_gm: bool,
        source_effect_id: str | None = None,
        override_resource_limit: bool = False,
    ) -> dict:
        from app.services.sleep_spell import (
            find_sleep_unconscious_effects,
            remove_sleep_unconscious_instance,
        )

        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)

        actor = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            actor_participant_id,
        )
        cls._require_actor_status(
            actor,
            ("active",),
            "Only active participants can wake a sleeper.",
        )

        target = cls._get_participant_by_ref(state, target_ref_id)
        if target is None:
            raise CombatServiceError("Wake target is not a participant in this combat.", 400)

        candidates = find_sleep_unconscious_effects(target, source_effect_id=source_effect_id)
        candidates = [
            effect
            for effect in candidates
            if cls._get_effect_metadata(effect).get("wakes_on_action") is True
        ]
        if not candidates:
            raise CombatServiceError(
                "Target is not asleep from a matching Sleep source.",
                400,
            )

        wake_effect = candidates[0]

        # Action cost is consumed only after we confirmed a valid wake target.
        was_overridden = cls._consume_turn_resource(
            actor,
            "action",
            is_gm=is_gm,
            override_resource_limit=override_resource_limit,
        )

        removed = remove_sleep_unconscious_instance(target, wake_effect.get("id"))
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        message = (
            f"{actor['display_name']} usou a ação para acordar "
            f"{target['display_name']} do sono mágico."
        )
        if was_overridden:
            message = f"[OVERRIDE: Action limit ignored] {message}"
        await cls._emit_log(
            session_id,
            {
                "message": message,
                "source": "condition_wake",
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )

        return {
            "conditionType": "unconscious",
            "sourceSpellKey": "sleep",
            "sourceEffectId": cls._get_effect_metadata(wake_effect).get("source_effect_id"),
            "targetRefId": target_ref_id,
            "conditionRemoved": removed,
            "actionConsumed": True,
            "isOverride": was_overridden,
        }

    @classmethod
    def _consume_turn_resource(cls, participant: dict, resource: str, *, is_gm: bool = False, override_resource_limit: bool = False) -> bool:
        if resource == "free":
            return False
        if resource == "reaction" and is_reaction_blocked(participant):
            raise CombatServiceError("Reaction is restricted by active effect.", 403)
        resources = cls._get_turn_resources(participant)
        key = f"{resource}_used"
        if key not in resources:
            raise CombatServiceError(f"Unknown action cost: {resource}")
        if resources.get(key):
            label = resource.replace("_", " ")
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
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)
        target = next((participant for participant in state.participants if participant["id"] == req.target_participant_id), None)
        if not target:
            raise CombatServiceError("Target participant not found in combat", 404)
        if req.kind == "condition" and not req.condition_type:
            raise CombatServiceError("condition_type is required when kind is 'condition'")
        if req.kind == "condition" and req.condition_type and has_condition_immunity(target, req.condition_type):
            raise CombatServiceError(f"Target is immune to {req.condition_type}", 409)
        if req.kind in ("temp_ac_bonus", "attack_bonus", "damage_bonus", "size_modifier") and req.numeric_value is None:
            raise CombatServiceError(f"numeric_value is required for kind '{req.kind}'")
        if req.kind == "size_modifier" and req.numeric_value not in (-1, 1):
            raise CombatServiceError("size_modifier numeric_value must be -1 or 1")
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
        if req.kind == "size_modifier":
            from .limiar_map_projection import maybe_sync_conditions_to_limiar_map
            try:
                maybe_sync_conditions_to_limiar_map(session_id, state, raise_on_error=True)
            except Exception as exc:
                effects.pop()
                cls._set_participant_effects(target, effects)
                raise CombatServiceError(f"Could not apply size modifier: {exc}", 409) from exc
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
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
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
        if removed.get("kind") == "size_modifier" or any(e.get("kind") == "size_modifier" for e in removed_effects):
            from .limiar_map_projection import maybe_sync_conditions_to_limiar_map
            maybe_sync_conditions_to_limiar_map(session_id, state)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        await cls._emit_log(session_id, {"message": f"Effect '{cls._effect_label(removed)}' removed from {target['display_name']}.", "source": "effect_removed"})
        if target.get("kind") == "player":
            from .persistent_effects import sync_effect_removal_to_state_json
            removed_effect_id = removed.get("id")
            if removed_effect_id is not None:
                sync_effect_removal_to_state_json(db, session_id, target, removed_effect_id)
        return state

    @classmethod
    async def consume_reaction(cls, db: Session, session_id: str, req: CombatConsumeReactionRequest, actor_user_id: str, is_gm: bool) -> CombatState:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
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
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
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
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
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
