from __future__ import annotations

from .cover_modifiers import cover_label
from .host_protocol import CombatServiceHostProtocol


class CombatNpcActionCommitMixin(CombatServiceHostProtocol):
    @classmethod
    async def _commit_npc_action_result(
        cls,
        db,
        session_id: str,
        actor_user_id: str,
        *,
        state,
        attacker: dict,
        resolved_action: dict,
        action_cost: str,
        was_overridden: bool,
        result: dict,
    ) -> dict:
        target_p = result["target_p"]
        db.add(state)
        db.commit()
        db.refresh(state)
        if target_p and result["new_hp"] is not None and target_p["kind"] == "player":
            target_state, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
            await cls._emit_player_state_update(db, session_id, target_p["ref_id"], target_state)
        elif target_p and result["previous_hp"] is not None and result["previous_hp"] != result["new_hp"]:
            await cls._emit_entity_hp_update(db, session_id, target_p["ref_id"], result["previous_hp"])
        await cls._emit_state(session_id, state)
        await cls._emit_and_persist_log(
            db, session_id, actor_user_id, attacker.get("display_name"),
            {
                "message": cls._build_npc_log_message(
                    attacker=attacker,
                    resolved_action=resolved_action,
                    result=result,
                    action_cost=action_cost,
                    was_overridden=was_overridden,
                ).strip(),
                "actorUserId": actor_user_id,
                "source": "gm_override",
                "is_override": was_overridden,
                "overridden_resource": action_cost if was_overridden else None,
            },
        )
        return cls._build_npc_action_response(result)

    @classmethod
    def _build_npc_log_message(
        cls,
        *,
        attacker: dict,
        resolved_action: dict,
        result: dict,
        action_cost: str,
        was_overridden: bool,
    ) -> str:
        target_p = result["target_p"]
        action_kind = result["action_kind"]
        action_name = result["action_name"]
        damage_type = result["damage_type"]
        if action_kind in ("weapon_attack", "spell_attack"):
            cover_text = f" ({cover_label(result['cover'])})" if result["cover"] and cover_label(result["cover"]) else ""
            adv_ctx = result["adv_ctx"]
            vis_ctx = result["vis_ctx"]
            hit_text = "HIT" if result["is_hit"] else "MISSED"
            adv_text = f" [{adv_ctx.describe()}]" if adv_ctx and (adv_ctx.advantage_sources or adv_ctx.disadvantage_sources) else ""
            vis_text = f" [Target not directly visible: {vis_ctx.describe()}]" if vis_ctx and not vis_ctx.is_directly_visible else ""
            if result["is_critical"]:
                hit_text = "CRITICALLY HIT" + (f" (auto-crit: {result['auto_crit_source']})" if result["auto_crit_source"] else "")
            log_message = (
                f"{attacker['display_name']} used {action_name} on {target_p['display_name'] if target_p else 'no target'}: "
                f"{hit_text} (roll {result['roll_total']} vs AC {result['target_ac'] or 10}{cover_text}){adv_text}{vis_text}"
            )
            if result["pending_attack_id"]:
                log_message += ". Damage roll pending."
            elif result["is_hit"] and result["damage"] > 0:
                log_message += f" for {result['damage']} {damage_type or ''} damage".replace("  ", " ")
            log_message += result["effect_msg"]
        elif action_kind == "saving_throw":
            cover_text = f" ({cover_label(result['cover'])})" if result["cover"] and cover_label(result["cover"]) else ""
            save_mod = result["save_mod"]
            save_mod_text = (
                f" [auto-fail: {save_mod.auto_fail_source}]"
                if save_mod and save_mod.auto_fail
                else (f" [{', '.join(save_mod.disadvantage_sources)}]" if save_mod and save_mod.disadvantage_sources else "")
            )
            target_name = target_p["display_name"] if target_p else "Target"
            log_message = (
                f"{attacker['display_name']} used {action_name} on {target_name}: "
                f"waiting for {target_name}'s {resolved_action.get('saveAbility')} "
                f"save against DC {result['save_dc_base']}{cover_text}{save_mod_text}"
            )
            if result["pending_save_id"]:
                log_message += ". Save roll pending."
            elif result["is_saved"] and result["save_success_outcome"] == "half_damage":
                rolled_damage_total = max(0, (result["base_damage"] or 0) + cls._safe_int(result["damage_bonus"], 0))
                log_message += f" and took half damage: {result['damage']} {damage_type or ''} damage (rolled {rolled_damage_total})".replace("  ", " ")
            elif not result["is_saved"] and result["damage"] > 0:
                log_message += f" and took {result['damage']} {damage_type or ''} damage".replace("  ", " ")
            elif result["is_saved"]:
                log_message += " and took no damage"
            log_message += result["effect_msg"]
        elif action_kind == "heal":
            log_message = (
                f"{attacker['display_name']} used {action_name} on "
                f"{target_p['display_name'] if target_p else attacker['display_name']}, healing {result['healing']} HP{result['effect_msg']}"
            )
        else:
            description = resolved_action.get("description") if isinstance(resolved_action.get("description"), str) else ""
            log_message = f"{attacker['display_name']} used {action_name}."
            if description:
                log_message += f" {description}"
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        if isinstance(result["concentration_check"], dict) and isinstance(result["concentration_check"].get("summary_text"), str):
            log_message = f"{log_message} {result['concentration_check']['summary_text']}".strip()
        return log_message

    @classmethod
    def _build_npc_action_response(cls, result: dict) -> dict:
        target_p = result["target_p"]
        return {
            "action_name": result["action_name"],
            "action_kind": result["action_kind"],
            "damage": result["damage"],
            "damage_type": result["damage_type"],
            "healing": result["healing"],
            "is_critical": result["is_critical"],
            "is_hit": result["is_hit"],
            "is_saved": result["is_saved"],
            "new_hp": result["new_hp"],
            "roll": result["roll_total"],
            "save_dc": result["save_dc"],
            "save_roll": result["save_roll"],
            "save_success_outcome": result["save_success_outcome"],
            "roll_result": result["roll_result"],
            "target_ac": result["target_ac"],
            "target_display_name": target_p["display_name"] if target_p else None,
            "damage_dice": result["damage_dice"],
            "damage_bonus": result["damage_bonus"],
            "attack_bonus": result["attack_bonus"],
            "pending_attack_id": result["pending_attack_id"],
            "pending_save_id": result["pending_save_id"],
            "damage_roll_required": bool(result["pending_attack_id"]),
            "damage_rolls": result["damage_rolls"],
            "base_damage": result["base_damage"],
            "damage_roll_source": result["damage_roll_source"],
            "concentration_check": result["concentration_check"],
        }
