from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from app.schemas.base_spell import SpellVariant

from ...combat_targeting import get_combat_targeting_service
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol
from ...targeting_intent import SpellCastIntent
from ...targeting_result import TargetingResult
from .helpers import resolve_instance_spatial_error_phrase


if TYPE_CHECKING:
    _CastTargetTargetingValidationBase = CombatServiceHostProtocol
else:
    _CastTargetTargetingValidationBase = object


class CastTargetTargetingValidationMixin(_CastTargetTargetingValidationBase):
    @classmethod
    def _get_spell_variants_map(cls, spell_context: dict) -> dict[str, SpellVariant]:
        variants = cls._normalize_spell_variants(spell_context.get("variant_definitions"))
        return {variant.key: variant for variant in variants}

    @classmethod
    def _participant_display_name(cls, participant: dict | None) -> str:
        if isinstance(participant, dict):
            return participant.get("display_name") or participant.get("ref_id") or "Target"
        return "Target"

    @classmethod
    def _build_variant_summary_for_target(
        cls,
        *,
        participant: dict,
        variant: SpellVariant,
    ) -> dict:
        return {
            "target_ref_id": participant.get("ref_id"),
            "target_participant_id": participant.get("id"),
            "target_display_name": cls._participant_display_name(participant),
            "variant_key": variant.key,
            "variant_label": variant.labelPt or variant.labelEn or variant.key,
            "manual_notes": [
                note.model_dump(mode="json") for note in (variant.manualNotes or [])
            ],
        }

    @classmethod
    def _merge_spell_context_with_variant(
        cls,
        *,
        spell_context: dict,
        variant: SpellVariant,
        participant: dict | None = None,
        target_variant_assignments: list[dict] | None = None,
    ) -> dict:
        merged = dict(spell_context)
        base_effects = list(spell_context.get("effects") or [])
        base_on_end_effects = list(spell_context.get("on_end_effects") or [])
        merged["effects"] = base_effects + [
            effect.model_dump(mode="json") for effect in (variant.effects or [])
        ]
        merged["on_end_effects"] = base_on_end_effects + [
            effect.model_dump(mode="json") for effect in (variant.onEndEffects or [])
        ]
        merged["selected_variant_key"] = variant.key
        merged["selected_variant_label"] = variant.labelPt or variant.labelEn or variant.key
        merged["variant_scope"] = (
            "per_target"
            if isinstance(target_variant_assignments, list) and len(target_variant_assignments) > 1
            else "single_target"
        )
        merged["context_origin"] = spell_context.get("context_origin") or "initial_cast"
        merged["manual_notes_by_target"] = (
            [cls._build_variant_summary_for_target(participant=participant, variant=variant)]
            if isinstance(participant, dict) and variant.manualNotes
            else []
        )
        merged["target_variant_assignments"] = target_variant_assignments
        return merged

    @classmethod
    def _validate_modal_target_variant_assignments(
        cls,
        *,
        req,
        spell_context: dict,
        state,
    ) -> list[dict] | None:
        variant_map = cls._get_spell_variants_map(spell_context)
        raw_assignments = list(getattr(req, "target_variant_assignments", None) or [])
        variant_key = getattr(req, "variant_key", None)

        if not variant_map:
            if raw_assignments or variant_key:
                raise CombatServiceError("This spell does not define variants.", 400)
            return None

        max_targets = cls._safe_int(spell_context.get("max_targets"), 1)
        if raw_assignments:
            if variant_key:
                raise CombatServiceError(
                    "variant_key cannot be combined with target_variant_assignments.",
                    400,
                )
            if len(raw_assignments) < 2:
                raise CombatServiceError(
                    "Single-target modal casts must use variant_key.",
                    400,
                )
            if max_targets > 0 and len(raw_assignments) > max_targets:
                raise CombatServiceError(
                    f"This spell can affect at most {max_targets} targets at this cast level.",
                    400,
                )
            seen_target_ids: set[str] = set()
            validated: list[dict] = []
            for assignment in raw_assignments:
                target_participant_id = assignment.target_participant_id
                if target_participant_id in seen_target_ids:
                    raise CombatServiceError(
                        f"Duplicate target variant assignment for participant {target_participant_id}.",
                        400,
                    )
                participant = cls._find_participant_by_id(state, target_participant_id)
                if participant is None:
                    raise CombatServiceError(
                        f"Unknown target participant '{target_participant_id}'.",
                        400,
                    )
                variant = variant_map.get(assignment.variant_key)
                if variant is None:
                    raise CombatServiceError(
                        f"Unknown spell variant '{assignment.variant_key}' for this spell.",
                        400,
                    )
                seen_target_ids.add(target_participant_id)
                validated.append(
                    {
                        "target_participant_id": target_participant_id,
                        "target_ref_id": participant.get("ref_id"),
                        "participant": participant,
                        "variant": variant,
                        "variant_key": variant.key,
                        "variant_label": variant.labelPt or variant.labelEn or variant.key,
                    }
                )
            return validated

        if not isinstance(variant_key, str) or not variant_key.strip():
            raise CombatServiceError(
                "This spell requires choosing a variant before casting.",
                400,
            )
        variant = variant_map.get(variant_key.strip())
        if variant is None:
            raise CombatServiceError(
                f"Unknown spell variant '{variant_key}' for this spell.",
                400,
            )
        return None

    @classmethod
    def _validate_modal_variant_spatial_targets(
        cls,
        *,
        db,
        state,
        attacker: dict,
        spell_context: dict,
        assignments: list[dict],
        session_id: str,
    ) -> dict[str, TargetingResult]:
        from . import get_combat_targeting_service as _get_targeting_service

        targeting_service = _get_targeting_service(state.use_map)
        results_by_participant_id: dict[str, TargetingResult] = {}

        for assignment in assignments:
            participant = assignment["participant"]
            target_ref_id = assignment["target_ref_id"]
            intent = SpellCastIntent(
                session_id=session_id,
                action_id=f"targeting-variant:{participant.get('id')}",
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
                reason = cls._map_spell_rejection_reason(
                    diag.primary_failure() if diag else None
                )
                actor_user_id = attacker.get("actor_user_id")
                cls._record_spell_cast_rejected_activity(
                    db,
                    session_id=session_id,
                    actor_user_id=actor_user_id if isinstance(actor_user_id, str) else "",
                    actor_ref_id=attacker["ref_id"],
                    actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                    spell_context=spell_context,
                    reason=reason,
                    target_ref_id=target_ref_id,
                    target_display_name=cls._participant_display_name(participant),
                )
                raise CombatServiceError(
                    f"Target {cls._participant_display_name(participant)} { resolve_instance_spatial_error_phrase(result) }.",
                    400,
                )
            results_by_participant_id[participant["id"]] = result

        return results_by_participant_id

    @classmethod
    def _validate_instance_targets(cls, *, req, spell_context, state):
        raw = getattr(req, "effect_instance_targets", None)
        instance_count = spell_context.get("effect_instance_count", 1)
        if not raw:
            if isinstance(instance_count, int) and instance_count > 1:
                spell_key = cls._normalize_lookup(spell_context.get("spell_canonical_key"))
                if spell_key in {"magic missile", "scorching ray"}:
                    raise CombatServiceError(
                        "This spell requires effect_instance_targets for every instance.",
                        400,
                    )
            return None

        instance_count = spell_context.get("effect_instance_count", 1)
        if instance_count <= 1:
            raise CombatServiceError(
                "effect_instance_targets is only supported for multi-instance spells.", 400
            )

        indices = set()
        for t in raw:
            idx = t.instance_index
            if idx < 1 or idx > instance_count:
                raise CombatServiceError(
                    f"Instance index {idx} is out of range (1..{instance_count}).", 400
                )
            if idx in indices:
                raise CombatServiceError(
                    f"Duplicate instance index: {idx}.", 400
                )
            indices.add(idx)

        missing = set(range(1, instance_count + 1)) - indices
        if missing:
            sorted_missing = sorted(missing)
            raise CombatServiceError(
                f"Missing instance target assignments: {', '.join(str(m) for m in sorted_missing)}.", 400
            )

        participants_by_ref = {p["ref_id"]: p for p in state.participants}
        validated = []
        for t in raw:
            participant = participants_by_ref.get(t.target_ref_id)
            if participant is None:
                raise CombatServiceError(
                    f"Invalid target_ref_id for instance {t.instance_index}: {t.target_ref_id}.", 400
                )
            validated.append({
                "instance_index": t.instance_index,
                "target_ref_id": t.target_ref_id,
                "participant": participant,
            })

        return validated

    @classmethod
    def _validate_instance_spatial_targets(
        cls,
        *,
        db,
        state,
        attacker: dict,
        spell_context: dict,
        validated_targets: list[dict],
        session_id: str,
    ) -> dict[str, TargetingResult]:
        """Validate range/LoS/LoE for each unique targetRefId before consuming any resources.

        Deduplicates validation by targetRefId — each unique target is validated once.
        Raises CombatServiceError with instance_index and reason on first failure.
        Returns a dict of TargetingResult keyed by target_ref_id so that cover metadata
        can be reused downstream (e.g. in _resolve_instance_attack) without re-validating.
        """
        from . import get_combat_targeting_service as _get_targeting_service

        targeting_service = _get_targeting_service(state.use_map)

        unique_ref_to_first_instance: dict[str, int] = {}
        for vt in validated_targets:
            ref_id = vt["target_ref_id"]
            if ref_id not in unique_ref_to_first_instance:
                unique_ref_to_first_instance[ref_id] = vt["instance_index"]

        results_by_ref: dict[str, TargetingResult] = {}

        for target_ref_id, first_instance_index in unique_ref_to_first_instance.items():
            intent = SpellCastIntent(
                session_id=session_id,
                action_id=f"targeting-instance:{first_instance_index}",
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
                participant = next(
                    (vt["participant"] for vt in validated_targets if vt["target_ref_id"] == target_ref_id),
                    None,
                )
                target_label = (participant or {}).get("display_name") or target_ref_id
                reason = cls._map_spell_rejection_reason(
                    result.diagnostics.primary_failure() if result.diagnostics else None
                )
                actor_user_id = attacker.get("actor_user_id")
                cls._record_spell_cast_rejected_activity(
                    db,
                    session_id=session_id,
                    actor_user_id=actor_user_id if isinstance(actor_user_id, str) else "",
                    actor_ref_id=attacker["ref_id"],
                    actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                    spell_context=spell_context,
                    reason=reason,
                    target_ref_id=target_ref_id,
                    target_display_name=target_label,
                    instance_index=first_instance_index,
                )
                reason_phrase = resolve_instance_spatial_error_phrase(result)
                raise CombatServiceError(
                    f"Instance {first_instance_index} target {target_label} {reason_phrase}.",
                    status_code=400,
                )

            results_by_ref[target_ref_id] = result

        return results_by_ref
