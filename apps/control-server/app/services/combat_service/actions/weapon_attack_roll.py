from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from app.schemas.roll import RollActorStats
from app.services.combat_service.condition_effects import get_attack_auto_crit, resolve_attack_advantage
from app.services.combat_service.cover_modifiers import cover_label, resolve_cover_modifier
from app.services.combat_service.visibility import resolve_target_visibility

from ..exceptions import CombatServiceError
from ..reach import resolve_weapon_attack_kind
from ..targeting_intent import WeaponAttackIntent
from ..targeting_requirements import resolve_weapon_targeting_requirements

logger = logging.getLogger(__name__)


class WeaponAttackRollMixin:
    @classmethod
    async def attack(cls, db, session_id: str, req, actor_user_id: str, is_gm: bool):
        from . import weapon_attacks as weapon_attacks_module

        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(state, actor_user_id, is_gm, req.actor_participant_id)
        cls._require_actor_status(attacker, ("active",), "You can only attack when active.")
        cls._require_action_capable(attacker)
        if attacker["kind"] != "player":
            raise CombatServiceError("Use entity actions for session entities.")
        attacker_model, *_ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        attacker_data = cls._as_dict(attacker_model.state_json)
        if cls._as_dict(attacker_data.get("wildShape")).get("active"):
            raise CombatServiceError("Cannot use weapon attacks while in Wild Shape. Use wild-shape-attack instead.", 400)
        attack_context = cls._build_player_attack_context(db, session_id, attacker["ref_id"], attacker_data, req.weapon_item_id)
        targeting_intent = WeaponAttackIntent(
            session_id=session_id,
            action_id=f"targeting:{uuid4()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=req.target_ref_id,
            weapon_item_id=req.weapon_item_id,
            weapon_canonical_key=attack_context.get("weapon_canonical_key"),
            range_meters=attack_context.get("range_meters"),
            range_long_meters=attack_context.get("range_long_meters"),
            weapon_range_type=attack_context.get("weapon_range_type"),
            has_reach=bool(attack_context.get("has_reach")),
            requires_sight=resolve_weapon_targeting_requirements().requires_target_sight,
            requires_effect=resolve_weapon_targeting_requirements().requires_target_effect,
        )
        targeting_result = weapon_attacks_module.get_combat_targeting_service(state.use_map).validate(targeting_intent, state)
        if not targeting_result.is_valid:
            diag = targeting_result.diagnostics
            logger.info("[attack] targeting failed session=%s actor=%s target=%s | %s", session_id, attacker.get("ref_id"), req.target_ref_id, diag.compact_log() if diag else targeting_result.failure_reason)
            raise CombatServiceError(targeting_result.failure_reason or "Target not found in combat")
        target = next((participant for participant in state.participants if participant["ref_id"] == targeting_result.validated_primary_target_ref_id), None)
        if not target:
            raise CombatServiceError("Target not found in combat")
        target_kind = "session_entity" if target.get("kind") == "entity" else target.get("kind")
        cls._assert_hostile_action_allowed(attacker, target, action_label="an attack")
        was_overridden = cls._consume_turn_resource(attacker, "action", is_gm=is_gm, override_resource_limit=req.override_resource_limit)
        cls._clear_participant_pending_attack(attacker)
        _, target_ac, *_ = cls._get_stats(db, target["ref_id"], target["kind"], session_id)
        target_ac = (target_ac or 10) + cls._sum_numeric_effects(target, "temp_ac_bonus")
        cover = targeting_result.spatial_metadata.cover
        target_ac += resolve_cover_modifier(cover)
        attack_context["attack_bonus"] += cls._sum_numeric_effects(attacker, "attack_bonus")
        attack_kind = resolve_weapon_attack_kind(
            weapon_range_type=attack_context.get("weapon_range_type"),
            range_meters=attack_context.get("range_meters"),
            range_long_meters=attack_context.get("range_long_meters"),
            has_reach=bool(attack_context.get("has_reach")),
            distance_meters=targeting_result.spatial_metadata.distance_meters,
        )
        adv_ctx = resolve_attack_advantage(attacker, target, attack_kind)
        vis_ctx = resolve_target_visibility(attacker, target, has_line_of_sight=bool(targeting_result.spatial_metadata.has_line_of_sight or True))
        has_adv = req.has_advantage or cls._has_effect_kind(attacker, "advantage_on_attacks") or bool(adv_ctx.advantage_sources)
        has_dis = req.has_disadvantage or cls._has_effect_kind(attacker, "disadvantage_on_attacks") or cls._has_effect_kind(target, "dodging") or bool(adv_ctx.disadvantage_sources) or bool(targeting_result.spatial_metadata.is_in_long_range) or not vis_ctx.is_directly_visible
        if not req.has_advantage and cls._has_effect_kind(attacker, "advantage_on_attacks"):
            cls._consume_first_effect(attacker, "advantage_on_attacks")
        adv_mode = "advantage" if (has_adv and not has_dis) else ("disadvantage" if (has_dis and not has_adv) else "normal")
        roll_result = weapon_attacks_module.resolve_attack_base(
            RollActorStats(display_name=attacker["display_name"], abilities={}, actor_kind="player", actor_ref_id=attacker["ref_id"]),
            advantage_mode=adv_mode,
            bonus_override=attack_context["attack_bonus"],
            target_ac=target_ac,
            roll_source=req.roll_source,
            manual_roll=req.manual_roll,
            manual_rolls=req.manual_rolls,
        )
        roll_result.is_gm_roll = is_gm
        roll_result.roll_source = req.roll_source
        is_crit = roll_result.selected_roll == 20
        is_fail = roll_result.selected_roll == 1
        atk_roll = roll_result.total
        is_hit = bool(roll_result.success)
        auto_crit_source = get_attack_auto_crit(attacker, target, attack_kind) if is_hit and not is_crit else ""
        if auto_crit_source:
            is_crit = True
        pending_attack_id = None
        if is_hit:
            pending_attack_id = cls._create_pending_attack(
                state,
                attacker,
                {
                    "type": "player_attack",
                    "target_ref_id": target["ref_id"],
                    "target_kind": target_kind,
                    "target_display_name": target["display_name"],
                    "target_ac": target_ac,
                    "weapon_name": attack_context["name"],
                    "damage_dice": attack_context["damage_dice"],
                    "damage_bonus": attack_context["damage_bonus"],
                    "attack_bonus": attack_context["attack_bonus"],
                    "damage_type": attack_context.get("damage_type"),
                    "inventory_item_id": attack_context.get("inventory_item_id"),
                    "is_weapon_attack": attack_context.get("inventory_item_id") != "unarmed",
                    "is_critical": is_crit,
                    "roll_result": roll_result.model_dump(mode="json"),
                    "roll": atk_roll,
                },
            )
        else:
            flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        hit_text = "HIT" if is_hit else "MISSED"
        if is_crit:
            hit_text = "CRITICALLY HIT" + (f" (auto-crit: {auto_crit_source})" if auto_crit_source else "")
        if is_fail:
            hit_text = "CRITICALLY MISSED"
        if was_overridden:
            hit_text = f"[OVERRIDE: Action limit ignored] {hit_text}"
        cover_text = f", {cover_label(cover)}" if cover_label(cover) else ""
        adv_text = f" [{adv_ctx.describe()}]" if (adv_ctx.advantage_sources or adv_ctx.disadvantage_sources) else ""
        vis_text = f" [Target not directly visible: {vis_ctx.describe()}]" if not vis_ctx.is_directly_visible else ""
        await cls._emit_log(
            session_id,
            {
                "message": f"{attacker['display_name']} {hit_text} {target['display_name']} (AC {target_ac}{cover_text}) with {attack_context['name']} and roll {atk_roll}{adv_text}{vis_text}.{(' Damage roll pending.' if is_hit else '')}",
                "actorUserId": actor_user_id,
                "source": "gm_override" if is_gm else "player_turn",
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )
        return {
            "roll": atk_roll,
            "is_hit": is_hit,
            "damage": 0,
            "is_critical": is_crit,
            "new_hp": None,
            "roll_result": roll_result,
            "target_ac": target_ac,
            "target_display_name": target["display_name"],
            "target_kind": target_kind,
            "weapon_name": attack_context["name"],
            "damage_dice": attack_context["damage_dice"],
            "damage_bonus": attack_context["damage_bonus"],
            "attack_bonus": attack_context["attack_bonus"],
            "damage_type": attack_context.get("damage_type"),
            "pending_attack_id": pending_attack_id,
            "damage_roll_required": is_hit,
        }
