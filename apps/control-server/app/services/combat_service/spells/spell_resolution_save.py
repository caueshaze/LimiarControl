from __future__ import annotations

from app.services.combat_service.cover_modifiers import resolve_cover_save_dc
from app.services.combat_service.condition_effects_saves import modify_saving_throw

from .spell_resolution_common import SpellResolutionCommonMixin, SpellResolutionResult


class SpellResolutionSaveMixin(SpellResolutionCommonMixin):
    @classmethod
    def _resolve_saving_throw_spell(
        cls,
        db,
        session_id: str,
        *,
        state,
        attacker: dict,
        target_p: dict,
        spell_context: dict,
        req,
        is_gm: bool,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        effect_roll_required: bool,
        save_success_outcome: str | None,
        targeting_result,
    ) -> SpellResolutionResult:
        from . import cast_target as cast_target_module

        result = SpellResolutionResult()
        result.cover = targeting_result.spatial_metadata.cover
        result.base_save_dc = cls._safe_int(spell_context.get("save_dc"), 0)
        result.effective_dc, result.cover_modifier = resolve_cover_save_dc(
            result.base_save_dc,
            result.cover,
            spell_context.get("cover_applies_to_save"),
            spell_context.get("save_ability"),
        )

        save_mod = modify_saving_throw(
            target_p,
            spell_context["save_ability"],
            source_participant=attacker,
        )
        result.roll_result = cast_target_module.resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(db, session_id, target_p["ref_id"], target_p["kind"], target_p["display_name"]),
            ability=spell_context["save_ability"],
            advantage_mode=save_mod.result,
            dc=result.effective_dc,
        )
        result.roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(result.roll_result.check_modifier_sources or []),
        ]
        cls._apply_roll_bonus_dice_to_roll_result(
            participant=target_p,
            roll_result=result.roll_result,
            roll_type="save",
        )
        result.roll_result.is_gm_roll = is_gm
        result.roll_total = result.roll_result.total
        result.is_saved = bool(result.roll_result.success)
        if effect_roll_required and (not result.is_saved or save_success_outcome == "half_damage"):
            result.pending_spell_id = cls._create_pending_spell_effect(
                state,
                attacker,
                cls._build_pending_spell_payload(
                    spell_context,
                    target_p,
                    action_kind=spell_mode,
                    effect_kind=effect_kind,
                    effect_bonus=effect_bonus,
                    save_success_outcome=save_success_outcome,
                    is_saved=result.is_saved,
                    roll_total=result.roll_total,
                    roll_result=result.roll_result,
                    effective_dc=result.effective_dc,
                ),
            )
        elif not result.is_saved or save_success_outcome == "half_damage":
            result.rolled_effect_total = max(0, effect_bonus)
            amount = cls._resolve_save_damage_amount(result.rolled_effect_total, is_saved=result.is_saved, save_success_outcome=save_success_outcome)
            result.new_hp, result.effect_msg, result.previous_hp, result.concentration_check = cls._apply_spell_effect(
                db,
                state,
                target_p["ref_id"],
                target_p["kind"],
                effect_kind,
                amount,
                damage_type=spell_context.get("damage_type"),
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
                attacker_participant_id=attacker.get("id"),
            )
            if effect_kind == "healing":
                result.healing = amount
            else:
                result.damage = amount
        else:
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(state, "participants")
        return result

    @classmethod
    def _resolve_direct_effect_spell(
        cls,
        db,
        state,
        *,
        attacker: dict,
        target_p: dict,
        spell_context: dict,
        req,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        effect_roll_required: bool,
    ) -> SpellResolutionResult:
        result = SpellResolutionResult()
        if effect_roll_required:
            result.pending_spell_id = cls._create_pending_spell_effect(
                state,
                attacker,
                cls._build_pending_spell_payload(spell_context, target_p, action_kind=spell_mode, effect_kind=effect_kind, effect_bonus=effect_bonus),
            )
        else:
            amount = max(0, effect_bonus)
            result.new_hp, result.effect_msg, result.previous_hp, result.concentration_check = cls._apply_spell_effect(
                db,
                state,
                target_p["ref_id"],
                target_p["kind"],
                effect_kind,
                amount,
                damage_type=spell_context.get("damage_type"),
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
                attacker_participant_id=attacker.get("id"),
            )
            if effect_kind == "healing":
                result.healing = amount
            else:
                result.damage = amount
        return result
