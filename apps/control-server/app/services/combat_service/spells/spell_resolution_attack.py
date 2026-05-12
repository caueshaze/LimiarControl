from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified

from app.schemas.roll import RollActorStats
from app.services.combat_service.condition_effects import resolve_attack_advantage, resolve_spell_attack_kind
from app.services.combat_service.cover_modifiers import resolve_cover_modifier
from app.services.combat_service.visibility import resolve_target_visibility
from app.services.roll_resolution import resolve_attack_base

from .spell_resolution_common import SpellResolutionCommonMixin, SpellResolutionResult


class SpellResolutionAttackMixin(SpellResolutionCommonMixin):
    @classmethod
    def _resolve_spell_attack(
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
        targeting_result,
    ) -> SpellResolutionResult:
        result = SpellResolutionResult()
        _, base_ac, *_ = cls._get_stats(
            db,
            target_p["ref_id"],
            target_p["kind"],
            session_id,
            combat_state=state,
        )
        result.cover = targeting_result.spatial_metadata.cover
        result.cover_modifier = resolve_cover_modifier(result.cover)
        result.base_ac = base_ac if base_ac is not None else 10
        result.target_ac = result.base_ac + result.cover_modifier
        result.adv_ctx = resolve_attack_advantage(attacker, target_p, resolve_spell_attack_kind())
        result.vis_ctx = resolve_target_visibility(attacker, target_p, has_line_of_sight=bool(targeting_result.spatial_metadata.has_line_of_sight or True))
        has_adv = req.has_advantage or bool(result.adv_ctx.advantage_sources)
        has_dis = req.has_disadvantage or bool(result.adv_ctx.disadvantage_sources) or not result.vis_ctx.is_directly_visible
        adv_mode = "advantage" if (has_adv and not has_dis) else ("disadvantage" if (has_dis and not has_adv) else "normal")
        result.roll_result = resolve_attack_base(
            RollActorStats(display_name=attacker["display_name"], abilities={}, actor_kind="player", actor_ref_id=attacker["ref_id"]),
            advantage_mode=adv_mode,
            bonus_override=cls._safe_int(spell_context.get("attack_bonus"), 0),
            target_ac=result.target_ac or 10,
            roll_source=req.roll_source,
            manual_roll=req.manual_roll,
            manual_rolls=req.manual_rolls,
        )
        result.roll_result.is_gm_roll = is_gm
        result.roll_result.roll_source = req.roll_source
        if result.adv_ctx.consumed_effect_ids_on_roll:
            cls._consume_effect_ids(target_p, result.adv_ctx.consumed_effect_ids_on_roll)
        result.roll_total = result.roll_result.total
        result.is_critical = result.roll_result.selected_roll == 20
        result.is_hit = bool(result.roll_result.success)
        if result.is_hit and effect_roll_required:
            result.pending_spell_id = cls._create_pending_spell_effect(
                state,
                attacker,
                cls._build_pending_spell_payload(
                    spell_context,
                    target_p,
                    action_kind=spell_mode,
                    effect_kind=effect_kind,
                    effect_bonus=effect_bonus,
                    is_critical=result.is_critical,
                    roll_total=result.roll_total,
                    roll_result=result.roll_result,
                    target_ac=result.target_ac or 10,
                ),
            )
        elif result.is_hit:
            amount = max(0, effect_bonus)
            result.new_hp, result.effect_msg, result.previous_hp, result.concentration_check = cls._apply_spell_effect(
                db,
                state,
                target_p["ref_id"],
                target_p["kind"],
                effect_kind,
                amount,
                damage_type=spell_context.get("damage_type"),
                is_critical=result.is_critical,
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
                attacker_participant_id=attacker.get("id"),
            )
            if effect_kind == "healing":
                result.healing = amount
            else:
                result.damage = amount
        else:
            flag_modified(state, "participants")
        return result
