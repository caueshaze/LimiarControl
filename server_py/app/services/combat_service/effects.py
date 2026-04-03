from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.combat import (
    CombatApplyEffectRequest,
    CombatConsumeReactionRequest,
    CombatRemoveEffectRequest,
    CombatReactionRequestRequest,
    CombatReactionResolveRequest,
)

from .exceptions import CombatServiceError


class CombatEffectsMixin:

    # ---- helpers ----

    @classmethod
    def _get_participant_effects(cls, participant: dict) -> list[dict]:
        effects = participant.get("active_effects")
        return effects if isinstance(effects, list) else []

    @classmethod
    def _set_participant_effects(cls, participant: dict, effects: list[dict]) -> None:
        participant["active_effects"] = effects

    @classmethod
    def _sum_numeric_effects(cls, participant: dict, kind: str) -> int:
        total = 0
        for effect in cls._get_participant_effects(participant):
            if effect.get("kind") == kind:
                val = effect.get("numeric_value")
                if isinstance(val, int):
                    total += val
        return total

    @classmethod
    def _has_effect_kind(cls, participant: dict, kind: str) -> bool:
        return any(
            e.get("kind") == kind
            for e in cls._get_participant_effects(participant)
        )

    @classmethod
    def _consume_first_effect(cls, participant: dict, kind: str) -> dict | None:
        """Remove and return the first effect of the given kind. Used for one-shot effects like Help."""
        effects = cls._get_participant_effects(participant)
        for i, e in enumerate(effects):
            if e.get("kind") == kind:
                removed = effects.pop(i)
                cls._set_participant_effects(participant, effects)
                return removed
        return None

    # ---- turn resources ----

    _DEFAULT_TURN_RESOURCES = {
        "action_used": False,
        "bonus_action_used": False,
        "reaction_used": False,
        "colossus_slayer_used": False,
    }

    @classmethod
    def _get_turn_resources(cls, participant: dict) -> dict:
        resources = participant.get("turn_resources")
        return resources if isinstance(resources, dict) else dict(cls._DEFAULT_TURN_RESOURCES)

    @classmethod
    def _reset_turn_resources(cls, participant: dict) -> None:
        participant["turn_resources"] = dict(cls._DEFAULT_TURN_RESOURCES)
        participant.pop("reaction_request", None)

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
                raise CombatServiceError(
                    f"This entity has already used its {label} this turn.",
                    409,
                )
            return True
        resources[key] = True
        participant["turn_resources"] = resources
        return False

    # ---- public methods ----

    @classmethod
    async def apply_effect(
        cls,
        db: Session,
        session_id: str,
        req: CombatApplyEffectRequest,
    ) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)

        target_p = next(
            (p for p in state.participants if p["id"] == req.target_participant_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Target participant not found in combat", 404)

        if req.kind == "condition" and not req.condition_type:
            raise CombatServiceError("condition_type is required when kind is 'condition'")

        if req.kind in ("temp_ac_bonus", "attack_bonus", "damage_bonus") and req.numeric_value is None:
            raise CombatServiceError(f"numeric_value is required for kind '{req.kind}'")

        if req.duration_type == "rounds" and not req.remaining_rounds:
            raise CombatServiceError("remaining_rounds is required for duration_type 'rounds'")

        # Derive expires_on from duration_type
        expires_on = None
        if req.duration_type == "until_turn_start":
            expires_on = "turn_start"
        elif req.duration_type == "until_turn_end":
            expires_on = "turn_end"
        elif req.duration_type == "rounds":
            expires_on = "turn_start"

        expires_at = req.expires_at_participant_id or req.target_participant_id

        now = datetime.now(timezone.utc).isoformat()
        effect = {
            "id": str(uuid4()),
            "source_participant_id": req.source_participant_id,
            "kind": req.kind,
            "condition_type": req.condition_type if req.kind == "condition" else None,
            "numeric_value": req.numeric_value,
            "duration_type": req.duration_type,
            "remaining_rounds": req.remaining_rounds,
            "expires_on": expires_on,
            "expires_at_participant_id": expires_at,
            "created_at": now,
            "metadata": req.metadata,
            "display_label": req.display_label,
        }

        effects = cls._get_participant_effects(target_p)
        effects.append(effect)
        cls._set_participant_effects(target_p, effects)
        flag_modified(state, "participants")

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        label = cls._effect_label(effect)
        await cls._emit_log(session_id, {
            "message": f"Effect '{label}' applied to {target_p['display_name']}.",
            "source": "effect_applied",
        })
        return state

    @classmethod
    async def remove_effect(
        cls,
        db: Session,
        session_id: str,
        req: CombatRemoveEffectRequest,
    ) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)

        target_p = next(
            (p for p in state.participants if p["id"] == req.target_participant_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Target participant not found in combat", 404)

        effects = cls._get_participant_effects(target_p)
        removed = None
        new_effects = []
        for e in effects:
            if e.get("id") == req.effect_id and removed is None:
                removed = e
            else:
                new_effects.append(e)

        if not removed:
            raise CombatServiceError("Effect not found on this participant", 404)

        cls._set_participant_effects(target_p, new_effects)
        removed_metadata = cls._get_effect_metadata(removed)
        if removed_metadata.get("concentration") is True and isinstance(
            removed_metadata.get("concentration_group"),
            str,
        ):
            cls._remove_effect_group(
                state,
                concentration_group=removed_metadata["concentration_group"],
            )
        flag_modified(state, "participants")

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        label = cls._effect_label(removed)
        await cls._emit_log(session_id, {
            "message": f"Effect '{label}' removed from {target_p['display_name']}.",
            "source": "effect_removed",
        })
        return state

    @classmethod
    async def consume_reaction(
        cls,
        db: Session,
        session_id: str,
        req: CombatConsumeReactionRequest,
        actor_user_id: str,
        is_gm: bool,
    ) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)

        target_p = next(
            (p for p in state.participants if p["id"] == req.participant_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Participant not found in combat", 404)

        if not is_gm and target_p.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("You can only mark your own reaction as used", 403)
        cls._require_actor_status(target_p, ("active",), "Only active participants can use reactions.")

        was_overridden = cls._consume_turn_resource(
            target_p, "reaction", is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )
        flag_modified(state, "participants")

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        log_message = f"{target_p['display_name']} used their reaction."
        if was_overridden:
            log_message = f"[OVERRIDE: Reaction limit ignored] {log_message}"

        await cls._emit_log(session_id, {
            "message": log_message,
            "source": "reaction_consumed",
            "is_override": was_overridden,
            "overridden_resource": "reaction" if was_overridden else None,
        })
        return state

    @classmethod
    async def request_reaction(
        cls,
        db: Session,
        session_id: str,
        req: CombatReactionRequestRequest,
        actor_user_id: str,
    ) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)

        target_p = next(
            (p for p in state.participants if p["id"] == req.actor_participant_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Participant not found in combat", 404)

        if target_p.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("You can only request reaction for your own character", 403)
        cls._require_actor_status(target_p, ("active",), "Only active participants can request reactions.")

        target_p["reaction_request"] = {
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat()
        }

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        await cls._emit_log(session_id, {
            "message": f"{target_p['display_name']} solicitou o uso da Reação e aguarda aprovação do GM.",
            "source": "reaction_requested",
        })
        return state

    @classmethod
    async def resolve_reaction(
        cls,
        db: Session,
        session_id: str,
        req: CombatReactionResolveRequest,
    ) -> CombatState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)

        target_p = next(
            (p for p in state.participants if p["id"] == req.actor_participant_id),
            None,
        )
        if not target_p:
            raise CombatServiceError("Participant not found in combat", 404)

        req_status = target_p.get("reaction_request", {}).get("status")
        if req_status != "pending":
            raise CombatServiceError("No pending reaction request found for this participant", 400)

        if req.decision == "approve":
            was_overridden = cls._consume_turn_resource(
                target_p, "reaction", is_gm=True, override_resource_limit=req.override_resource_limit
            )
            target_p["reaction_request"]["status"] = "approved"
            flag_modified(state, "participants")
            db.add(state)
            db.commit()
            db.refresh(state)
            await cls._emit_state(session_id, state)

            log_msg = f"{target_p['display_name']}'s reaction request was approved and consumed."
            if was_overridden:
                log_msg = f"[OVERRIDE: Reaction limit ignored] {log_msg}"

            await cls._emit_log(session_id, {
                "message": log_msg,
                "source": "reaction_approved",
                "is_override": was_overridden,
                "overridden_resource": "reaction" if was_overridden else None,
            })
            return state

        elif req.decision == "deny":
            target_p["reaction_request"]["status"] = "denied"
            flag_modified(state, "participants")
            db.add(state)
            db.commit()
            db.refresh(state)
            await cls._emit_state(session_id, state)

            await cls._emit_log(session_id, {
                "message": f"{target_p['display_name']}'s reaction request was denied.",
                "source": "reaction_denied",
            })
            return state

        raise CombatServiceError("Invalid decision", 400)

    # ---- expiration (called from lifecycle) ----

    @classmethod
    async def _expire_effects_for_participant(
        cls,
        session_id: str,
        state: CombatState,
        participant_id: str,
        trigger: str,
    ) -> list[dict]:
        """Expire effects that trigger on the given participant's turn phase.

        Returns list of expired effect dicts (annotated with target info) for logging.
        Mutates state.participants in place — caller must flag_modified + commit.
        """
        expired: list[dict] = []
        for p in state.participants:
            effects = cls._get_participant_effects(p)
            if not effects:
                continue
            keep: list[dict] = []
            for e in effects:
                if (
                    e.get("expires_on") == trigger
                    and e.get("expires_at_participant_id") == participant_id
                ):
                    if e.get("duration_type") == "rounds":
                        remaining = e.get("remaining_rounds")
                        if isinstance(remaining, int) and remaining > 1:
                            e["remaining_rounds"] = remaining - 1
                            keep.append(e)
                            continue
                    expired.append({
                        **e,
                        "target_participant_id": p["id"],
                        "target_display_name": p.get("display_name", ""),
                    })
                else:
                    keep.append(e)
            cls._set_participant_effects(p, keep)
        return expired

    # ---- query ----

    @classmethod
    def get_all_effects(cls, state: CombatState) -> list[dict]:
        result = []
        for p in state.participants:
            for e in cls._get_participant_effects(p):
                result.append({
                    **e,
                    "target_participant_id": p["id"],
                    "target_display_name": p.get("display_name", ""),
                })
        return result

    # ---- internal ----

    @classmethod
    def _effect_label(cls, effect: dict) -> str:
        display_label = effect.get("display_label")
        if isinstance(display_label, str) and display_label.strip():
            return display_label.strip()
        kind = effect.get("kind", "effect")
        if kind == "condition":
            return effect.get("condition_type") or "condition"
        val = effect.get("numeric_value")
        if isinstance(val, int):
            sign = "+" if val >= 0 else ""
            return f"{kind} ({sign}{val})"
        return kind
