from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.combat_service.condition_effects_predicates import is_reaction_blocked

from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _CastTargetResourceConsumptionBase = CombatServiceHostProtocol
else:
    _CastTargetResourceConsumptionBase = object


class CastTargetResourceConsumptionMixin(_CastTargetResourceConsumptionBase):
    @classmethod
    def _ensure_turn_resource_available(
        cls,
        participant: dict,
        resource: str,
        *,
        is_gm: bool = False,
        override_resource_limit: bool = False,
    ) -> None:
        if resource == "free":
            return
        if resource == "reaction" and is_reaction_blocked(participant):
            raise CombatServiceError("Reaction is restricted by active effect.", 403)
        resources = cls._get_turn_resources(participant)
        key = f"{resource}_used"
        if key not in resources:
            raise CombatServiceError(f"Unknown action cost: {resource}")
        if resources.get(key):
            label = resource.replace("_", " ")
            if is_gm and override_resource_limit:
                return
            raise CombatServiceError(
                f"Your {label} has already been used this turn.",
                403,
            )

    @classmethod
    def _ensure_player_spell_slot_available(
        cls,
        attacker_model,
        slot_level: int,
    ) -> None:
        data = cls._as_dict(getattr(attacker_model, "state_json", None))
        spellcasting = cls._as_dict(data.get("spellcasting"))
        slots = cls._as_dict(spellcasting.get("slots"))
        lvl_key = str(slot_level)
        slot_data = cls._as_dict(slots.get(lvl_key)) or {"used": 0, "max": 0}
        if cls._safe_int(slot_data.get("used"), 0) >= cls._safe_int(
            slot_data.get("max"), 0
        ):
            raise CombatServiceError("No spell slots of this level remaining", 400)

    @classmethod
    def _validate_feather_fall_trigger_context(
        cls,
        *,
        req,
        spell_context: dict,
        targets: list[dict],
    ) -> None:
        spell_key = cls._normalize_lookup(spell_context.get("spell_canonical_key"))
        if spell_key not in {"feather_fall", "feather fall"}:
            return

        reaction_trigger = cls._normalize_lookup(getattr(req, "reaction_trigger", None))
        if reaction_trigger != "fall":
            raise CombatServiceError(
                "Queda Suave exige reaction_trigger='fall'.",
                400,
            )
        falling_target_ref_ids = getattr(req, "falling_target_ref_ids", None)
        if not isinstance(falling_target_ref_ids, list) or not falling_target_ref_ids:
            raise CombatServiceError(
                "Queda Suave exige falling_target_ref_ids no evento de reação.",
                400,
            )
        falling_set = {
            ref_id.strip()
            for ref_id in falling_target_ref_ids
            if isinstance(ref_id, str) and ref_id.strip()
        }
        if not falling_set:
            raise CombatServiceError(
                "Queda Suave exige falling_target_ref_ids no evento de reação.",
                400,
            )
        target_set = {
            (participant.get("ref_id") or "").strip()
            for participant in targets
            if isinstance(participant, dict)
        }
        if not target_set.issubset(falling_set):
            raise CombatServiceError(
                "Os alvos de Queda Suave devem estar no evento de queda.",
                400,
            )
