from __future__ import annotations

from typing import TYPE_CHECKING

from ...combat_targeting import get_combat_targeting_service
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol
from ...targeting_intent import SpellCastIntent
from ...targeting_result import TargetingResult
from .helpers import resolve_instance_spatial_error_phrase


if TYPE_CHECKING:
    _CastTargetPlainMultiTargetValidationBase = CombatServiceHostProtocol
else:
    _CastTargetPlainMultiTargetValidationBase = object


class CastTargetPlainMultiTargetValidationMixin(_CastTargetPlainMultiTargetValidationBase):
    @classmethod
    def _validate_plain_multi_target_refs(
        cls,
        *,
        req,
        spell_context: dict,
        state,
    ) -> list[dict] | None:
        """Return resolved participant list or None if not applicable.

        Raises CombatServiceError on invalid requests.
        """
        ref_ids = getattr(req, "target_ref_ids", None)
        if ref_ids is None:
            return None
        if len(ref_ids) == 0:
            raise CombatServiceError(
                "This cast requires at least 1 target.",
                400,
            )

        # Mutual exclusion with other targeting fields
        if (
            getattr(req, "target_ref_id", None)
            or getattr(req, "target_variant_assignments", None)
            or getattr(req, "effect_instance_targets", None)
        ):
            raise CombatServiceError(
                "target_ref_ids cannot be combined with target_ref_id, "
                "target_variant_assignments, or effect_instance_targets.",
                400,
            )

        # Spell must be configured for multi-target
        effective_max = spell_context.get("max_targets")
        if not isinstance(effective_max, int):
            raise CombatServiceError(
                "This spell is not configured for multi-target casting.", 400
            )

        # Duplicate check
        if len(ref_ids) != len(set(ref_ids)):
            raise CombatServiceError("Duplicate target IDs are not allowed.", 400)

        # Count check (against resolved effective_max_targets)
        if len(ref_ids) > effective_max:
            raise CombatServiceError(
                f"This cast allows at most {effective_max} target(s); "
                f"{len(ref_ids)} were provided.",
                400,
            )

        # Resolve each ref_id to a participant
        resolved: list[dict] = []
        for ref_id in ref_ids:
            participant = next(
                (p for p in state.participants if p.get("ref_id") == ref_id),
                None,
            )
            if participant is None:
                raise CombatServiceError(
                    f"Target '{ref_id}' not found in combat.", 400
                )
            resolved.append(participant)

        return resolved

    @classmethod
    def _validate_plain_multi_target_spatial(
        cls,
        *,
        db,
        state,
        attacker: dict,
        spell_context: dict,
        targets: list[dict],
        session_id: str,
    ) -> dict[str, "TargetingResult"]:
        """Fan out spatial validation (range, LoS, LoE) for each plain target.

        Runs before resource consumption.  Raises CombatServiceError if any
        target fails.  Mirrors _validate_modal_variant_spatial_targets.
        """
        from . import get_combat_targeting_service as _get_targeting_service

        targeting_service = _get_targeting_service(state.use_map)
        results: dict[str, "TargetingResult"] = {}

        for participant in targets:
            target_ref_id = participant.get("ref_id", "")
            intent = SpellCastIntent(
                session_id=session_id,
                action_id=f"targeting-plain:{participant.get('id')}",
                actor_ref_id=attacker["ref_id"],
                actor_kind=attacker["kind"],
                requested_target_ref_id=target_ref_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                spell_mode=spell_context["spell_mode"],
                target_type=spell_context.get("target_type"),
                selection_type=spell_context.get("selection_type"),
                attack_type=spell_context.get("attack_type"),
                range_kind=spell_context.get("range_kind"),
                area_shape=spell_context.get("area_shape"),
                range_meters=spell_context.get("range_meters"),
                requires_sight=bool(spell_context.get("requires_target_sight")),
                requires_effect=bool(spell_context.get("requires_target_effect")),
            )
            result = targeting_service.validate(intent, state)
            if not result.is_valid:
                diag = result.diagnostics
                actor_user_id = attacker.get("actor_user_id")
                cls._record_spell_cast_rejected_activity(
                    db,
                    session_id=session_id,
                    actor_user_id=actor_user_id if isinstance(actor_user_id, str) else "",
                    actor_ref_id=attacker["ref_id"],
                    actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                    spell_context=spell_context,
                    reason=cls._map_spell_rejection_reason(
                        diag.primary_failure() if diag else None
                    ),
                    target_ref_id=target_ref_id,
                    target_display_name=cls._participant_display_name(participant),
                )
                raise CombatServiceError(
                    f"Target {cls._participant_display_name(participant)} "
                    f"{resolve_instance_spatial_error_phrase(result)}.",
                    400,
                )
            results[participant["id"]] = result

        return results
