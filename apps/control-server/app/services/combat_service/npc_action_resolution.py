from __future__ import annotations

import logging

from sqlalchemy.orm.attributes import flag_modified

from app.schemas.roll import RollActorStats
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.services.combat_service.condition_effects import (
    get_attack_auto_crit,
    modify_saving_throw,
    resolve_attack_advantage,
    resolve_spell_attack_kind,
)
from app.services.combat_service.cover_modifiers import (
    resolve_cover_modifier,
    resolve_cover_save_modifier,
    should_cover_apply_to_save,
)
from app.services.combat_service.visibility import resolve_target_visibility

from .exceptions import CombatServiceError, _roll_dice_expression
from .reach import resolve_weapon_attack_kind

logger = logging.getLogger(__name__)


class CombatNpcActionResolutionMixin:
    @classmethod
    def _resolve_npc_action_result(
        cls,
        db,
        session_id: str,
        req,
        is_gm: bool,
        *,
        state,
        attacker: dict,
        resolved_action: dict,
        action_name: str,
        action_kind: str,
        damage_type: str | None,
        target_p: dict | None,
    ) -> dict:
        from . import npc_actions as npc_actions_module

        context = {
            "action_name": action_name,
            "action_kind": action_kind,
            "damage_type": damage_type,
            "target_p": target_p,
            "roll_total": None,
            "save_roll": None,
            "save_dc": None,
            "is_hit": None,
            "is_saved": None,
            "is_critical": False,
            "damage": 0,
            "healing": 0,
            "new_hp": None,
            "previous_hp": None,
            "effect_msg": "",
            "concentration_check": None,
            "roll_result": None,
            "target_ac": None,
            "attack_bonus": None,
            "damage_dice": None,
            "damage_bonus": None,
            "pending_attack_id": None,
            "damage_rolls": [],
            "base_damage": None,
            "damage_roll_source": None,
            "save_success_outcome": None,
            "cover": None,
            "auto_crit_source": "",
            "adv_ctx": None,
            "vis_ctx": None,
            "save_mod": None,
            "save_dc_base": None,
        }
        if action_kind in ("weapon_attack", "spell_attack", "saving_throw") and target_p:
            targeting_intent = cls._build_npc_targeting_intent(
                session_id, attacker, target_p, action_kind, resolved_action
            )
            targeting_result = npc_actions_module.get_combat_targeting_service(state.use_map).validate(
                targeting_intent, state
            )
            if not targeting_result.is_valid:
                diag = targeting_result.diagnostics
                logger.info(
                    "[entity_action] targeting failed session=%s actor=%s target=%s | %s",
                    session_id,
                    attacker.get("ref_id"),
                    req.target_ref_id,
                    diag.compact_log() if diag else targeting_result.failure_reason,
                )
                raise CombatServiceError(
                    targeting_result.failure_reason or "Targeting validation failed"
                )
            context["cover"] = targeting_result.spatial_metadata.cover
            target_p = next(
                (p for p in state.participants if p["ref_id"] == targeting_result.validated_primary_target_ref_id),
                None,
            )
            if not target_p:
                raise CombatServiceError("Target not found in combat after validation")
            context["target_p"] = target_p
            context["targeting_result"] = targeting_result

        if action_kind in ("weapon_attack", "spell_attack"):
            cls._clear_participant_pending_attack(attacker)
            _, target_ac, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
            target_ac = (target_ac or 10) + cls._sum_numeric_effects(target_p, "temp_ac_bonus")
            if context["cover"]:
                target_ac += resolve_cover_modifier(context["cover"])
            attack_bonus = cls._safe_int(
                resolved_action.get("spellAttackBonus") if action_kind == "spell_attack" else resolved_action.get("toHitBonus"),
                0,
            )
            attack_bonus += cls._sum_numeric_effects(attacker, "attack_bonus")
            damage_dice = resolved_action.get("damageDice") if isinstance(resolved_action.get("damageDice"), str) else None
            damage_bonus = cls._safe_int(resolved_action.get("damageBonus"), 0)
            attack_kind = (
                resolve_weapon_attack_kind(
                    weapon_range_type=resolved_action.get("rangeType"),
                    range_meters=resolved_action.get("rangeMeters"),
                    range_long_meters=resolved_action.get("rangeLongMeters"),
                    has_reach=bool(resolved_action.get("hasReach")),
                    distance_meters=context["targeting_result"].spatial_metadata.distance_meters,
                )
                if action_kind == "weapon_attack"
                else resolve_spell_attack_kind(resolved_action)
            )
            adv_ctx = resolve_attack_advantage(attacker, target_p, attack_kind)
            vis_ctx = resolve_target_visibility(
                attacker,
                target_p,
                has_line_of_sight=bool(context["targeting_result"].spatial_metadata.has_line_of_sight or True) if context.get("targeting_result") else True,
            )
            has_adv = req.has_advantage or cls._has_effect_kind(attacker, "advantage_on_attacks") or bool(adv_ctx.advantage_sources)
            has_dis = (
                req.has_disadvantage
                or cls._has_effect_kind(attacker, "disadvantage_on_attacks")
                or cls._has_effect_kind(target_p, "dodging")
                or bool(adv_ctx.disadvantage_sources)
                or bool(context["targeting_result"].spatial_metadata.is_in_long_range)
                or not vis_ctx.is_directly_visible
            )
            if not req.has_advantage and cls._has_effect_kind(attacker, "advantage_on_attacks"):
                cls._consume_first_effect(attacker, "advantage_on_attacks")
            adv_mode = "advantage" if (has_adv and not has_dis) else ("disadvantage" if (has_dis and not has_adv) else "normal")
            roll_result = npc_actions_module.resolve_attack_base(
                RollActorStats(
                    display_name=attacker["display_name"],
                    abilities={},
                    actor_kind="session_entity",
                    actor_ref_id=attacker["ref_id"],
                ),
                advantage_mode=adv_mode,
                bonus_override=attack_bonus,
                target_ac=target_ac or 10,
                roll_source=req.roll_source,
                manual_roll=req.manual_roll,
                manual_rolls=req.manual_rolls,
            )
            roll_result.is_gm_roll = is_gm
            roll_result.roll_source = req.roll_source
            is_critical = roll_result.selected_roll == 20
            is_hit = bool(roll_result.success)
            auto_crit_source = (
                get_attack_auto_crit(attacker, target_p, attack_kind)
                if is_hit and not is_critical and action_kind == "weapon_attack"
                else ""
            )
            if auto_crit_source:
                is_critical = True
            pending_attack_id = None
            if is_hit:
                pending_attack_id = cls._create_pending_attack(
                    state,
                    attacker,
                    {
                        "type": "entity_attack",
                        "action_name": action_name,
                        "action_kind": action_kind,
                        "target_ref_id": target_p["ref_id"],
                        "target_kind": target_p["kind"],
                        "target_display_name": target_p["display_name"],
                        "target_ac": target_ac or 10,
                        "damage_dice": damage_dice,
                        "damage_bonus": damage_bonus,
                        "damage_type": damage_type,
                        "attack_bonus": attack_bonus,
                        "is_critical": is_critical,
                        "roll_result": roll_result.model_dump(mode="json"),
                        "roll": roll_result.total,
                    },
                )
            else:
                flag_modified(state, "participants")
            context.update(
                {
                    "roll_total": roll_result.total,
                    "roll_result": roll_result,
                    "is_critical": is_critical,
                    "is_hit": is_hit,
                    "target_ac": target_ac,
                    "attack_bonus": attack_bonus,
                    "damage_dice": damage_dice,
                    "damage_bonus": damage_bonus,
                    "pending_attack_id": pending_attack_id,
                    "adv_ctx": adv_ctx,
                    "vis_ctx": vis_ctx,
                    "auto_crit_source": auto_crit_source,
                }
            )
            return context

        if action_kind == "saving_throw":
            ability_name = cls._normalize_ability_name(resolved_action.get("saveAbility"))
            save_dc_base = cls._safe_int(resolved_action.get("saveDc"), 0)
            damage_dice = resolved_action.get("damageDice") if isinstance(resolved_action.get("damageDice"), str) else None
            damage_bonus = cls._safe_int(resolved_action.get("damageBonus"), 0)
            save_success_outcome = cls._normalize_save_success_outcome(resolved_action.get("saveSuccessOutcome")) or "none"
            if not ability_name or save_dc_base <= 0:
                raise CombatServiceError("Saving throw actions require save ability and save DC.")
            effective_dc = max(0, save_dc_base - resolve_cover_save_modifier(context["cover"])) if should_cover_apply_to_save(
                resolved_action.get("coverAppliesToSave"), ability_name
            ) else save_dc_base
            save_mod = modify_saving_throw(target_p, ability_name)
            roll_result = npc_actions_module.resolve_saving_throw(
                cls._build_roll_actor_stats_for_save(
                    db,
                    session_id,
                    target_p["ref_id"],
                    target_p["kind"],
                    target_p["display_name"],
                ),
                ability=ability_name,
                advantage_mode=save_mod.result,
                dc=effective_dc,
                roll_source=req.roll_source,
                manual_roll=req.manual_roll,
            )
            roll_result.is_gm_roll = is_gm
            save_roll = roll_result.total
            is_saved = False if save_mod.auto_fail else bool(roll_result.success)
            damage_rolls, base_damage = cls._resolve_damage_roll(damage_dice or "", roll_source="system")
            damage = cls._resolve_save_damage_amount(
                max(0, base_damage + damage_bonus),
                is_saved=is_saved,
                save_success_outcome=save_success_outcome,
            )
            new_hp = None
            previous_hp = None
            effect_msg = ""
            concentration_check = None
            if damage > 0:
                new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                    db,
                    target_p["ref_id"],
                    target_p["kind"],
                    damage,
                    damage_type=damage_type,
                    is_crit=False,
                    state=state,
                    **cls._build_concentration_roll_kwargs(req.concentration_roll_source, req.concentration_manual_roll),
                )
            context.update(
                {
                    "roll_result": roll_result,
                    "save_roll": save_roll,
                    "save_dc": effective_dc,
                    "save_dc_base": save_dc_base,
                    "is_saved": is_saved,
                    "damage_dice": damage_dice,
                    "damage_bonus": damage_bonus,
                    "damage_rolls": damage_rolls,
                    "base_damage": base_damage,
                    "damage_roll_source": "system",
                    "save_success_outcome": save_success_outcome,
                    "damage": damage,
                    "new_hp": new_hp,
                    "previous_hp": previous_hp,
                    "effect_msg": effect_msg,
                    "concentration_check": concentration_check,
                    "save_mod": save_mod,
                }
            )
            return context

        if action_kind == "heal":
            healing = max(
                0,
                npc_actions_module._roll_dice_expression(resolved_action.get("healDice") or "")
                + cls._safe_int(resolved_action.get("healBonus"), 0),
            )
            if healing > 0:
                new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(
                    db, target_p["ref_id"], target_p["kind"], healing, state
                )
                context.update(
                    {
                        "healing": healing,
                        "new_hp": new_hp,
                        "previous_hp": previous_hp,
                        "effect_msg": effect_msg,
                    }
                )
            return context

        if action_kind != "utility":
            raise CombatServiceError("Unsupported combat action kind.")
        return context
