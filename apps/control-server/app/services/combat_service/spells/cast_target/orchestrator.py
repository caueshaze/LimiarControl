from __future__ import annotations

import logging

from ...exceptions import CombatServiceError
from .plain_multi_target_resolution import CastTargetPlainMultiTargetResolutionMixin

logger = logging.getLogger(__name__)


class CastTargetOrchestratorMixin:
    @classmethod
    async def cast_spell(
        cls,
        db,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool,
    ):
        state, attacker, attacker_model = cls._validate_cast_prerequisites(
            db, session_id, req, actor_user_id, is_gm,
        )
        spell_context = cls._resolve_player_spell_context(
            db, session_id, attacker, attacker_model, req,
        )
        validated_variant_assignments = cls._validate_modal_target_variant_assignments(
            req=req,
            spell_context=spell_context,
            state=state,
        )
        if validated_variant_assignments:
            spatial_results_by_participant_id = cls._validate_modal_variant_spatial_targets(
                db=db,
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                assignments=validated_variant_assignments,
                session_id=session_id,
            )
            return await cls._resolve_modal_multi_target_cast(
                db,
                session_id,
                req,
                state,
                attacker,
                attacker_model,
                spell_context,
                actor_user_id,
                is_gm,
                validated_variant_assignments,
                spatial_results_by_participant_id=spatial_results_by_participant_id,
            )
        validated_plain_targets = cls._validate_plain_multi_target_refs(
            req=req,
            spell_context=spell_context,
            state=state,
        )
        if validated_plain_targets is not None:
            plain_spatial_results = cls._validate_plain_multi_target_spatial(
                db=db,
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                targets=validated_plain_targets,
                session_id=session_id,
            )
            return await cls._resolve_plain_multi_target_automation_cast(
                db,
                session_id,
                req,
                state,
                attacker,
                attacker_model,
                spell_context,
                actor_user_id,
                is_gm,
                validated_plain_targets,
                spatial_results=plain_spatial_results,
            )
        variant_map = cls._get_spell_variants_map(spell_context)
        if variant_map:
            selected_variant_key = spell_context.get("selected_variant_key")
            selected_variant = variant_map.get(selected_variant_key)
            if selected_variant is None:
                raise CombatServiceError(
                    "This spell requires choosing a variant before casting.",
                    400,
                )
            selected_participant = next(
                (
                    participant
                    for participant in state.participants
                    if participant.get("ref_id") == getattr(req, "target_ref_id", None)
                ),
                attacker if spell_context.get("selection_type") in ("self", "none") else None,
            )
            single_target_assignment = (
                [
                    {
                        "target_participant_id": selected_participant.get("id"),
                        "target_display_name": cls._participant_display_name(selected_participant),
                        "variant_key": selected_variant.key,
                        "variant_label": selected_variant.labelPt or selected_variant.labelEn or selected_variant.key,
                        "target_ref_id": selected_participant.get("ref_id"),
                    }
                ]
                if isinstance(selected_participant, dict)
                else None
            )
            spell_context = cls._merge_spell_context_with_variant(
                spell_context=spell_context,
                variant=selected_variant,
                participant=selected_participant,
                target_variant_assignments=single_target_assignment,
            )
        validated_targets = cls._validate_instance_targets(
            req=req, spell_context=spell_context, state=state,
        )
        if validated_targets is not None:
            spatial_results_by_target_ref = cls._validate_instance_spatial_targets(
                db=db,
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                validated_targets=validated_targets,
                session_id=session_id,
            )
            return await cls._resolve_multi_instance_cast(
                db, session_id, req, state, attacker, attacker_model,
                spell_context, actor_user_id, is_gm, validated_targets,
                spatial_results_by_target_ref=spatial_results_by_target_ref,
            )
        area_spell_spec = cls._resolve_supported_area_spell_spec(spell_context)
        if cls._normalize_area_shape(spell_context.get("area_shape")) is not None:
            if area_spell_spec is None:
                raise CombatServiceError(
                    "This area spell is not configured for map targeting yet.", 400,
                )
            logger.info(
                "[cast_spell] pipeline=generic_area spell=%s session=%s actor=%s",
                spell_context["spell_canonical_key"],
                session_id,
                attacker.get("ref_id"),
            )
            return await cls._cast_area_spell(
                db, session_id, req,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spell_spec,
            )

        if spell_context.get("spell_mode") == "teleport":
            return await cls._resolve_teleport_spell(
                db, session_id, req, state, attacker, attacker_model, spell_context, actor_user_id, is_gm
            )

        if spell_context.get("selection_type") in ("none", "self"):
            return await cls._resolve_no_external_target_cast(
                db, session_id, req, state, attacker, attacker_model,
                spell_context, actor_user_id, is_gm,
            )

        resolution = await cls._resolve_cast_resolution(
            db, session_id, req, state, attacker, attacker_model,
            spell_context, actor_user_id, is_gm,
        )
        return await cls._commit_cast_result(
            db, session_id, state, attacker, spell_context,
            resolution, actor_user_id, is_gm,
        )
