from __future__ import annotations

from app.schemas.roll import RollResult

from ..exceptions import CombatServiceError


class WeaponAttackDamageMixin:
    @classmethod
    async def attack_damage(cls, db, session_id: str, req, actor_user_id: str, is_gm: bool):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(state, actor_user_id, is_gm, req.actor_participant_id)
        cls._require_actor_status(attacker, ("active",), "You can only roll damage when active.")
        if attacker["kind"] != "player":
            raise CombatServiceError("Use entity actions for session entities.")
        pending_attack = cls._require_pending_attack(attacker, req.pending_attack_id, expected_type="player_attack")
        damage_rolls, base_damage = cls._resolve_damage_roll(
            pending_attack.get("damage_dice") or "unarmed",
            critical=bool(pending_attack.get("is_critical")),
            roll_source=req.roll_source,
            manual_rolls=req.manual_rolls,
        )
        damage_bonus = cls._safe_int(pending_attack.get("damage_bonus"), 0)
        effect_damage_bonus = cls._sum_numeric_effects(attacker, "damage_bonus")
        damage = max(1, base_damage + damage_bonus + effect_damage_bonus)
        target_ref_id = pending_attack.get("target_ref_id")
        target_kind = pending_attack.get("target_kind")
        target_display_name = pending_attack.get("target_display_name") or "Target"
        if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
            raise CombatServiceError("Pending damage roll is missing target information.", 400)
        target_participant = cls._get_participant_by_ref(state, target_ref_id)
        attacker_model, *_ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        attacker_data = cls._as_dict(attacker_model.state_json)
        target_current_hp, target_max_hp = cls._get_target_hp_snapshot(db, session_id, target_ref_id, target_kind)
        extra_damage = 0
        extra_damage_rolls: list[int] = []
        extra_damage_label = ""
        turn_resources = cls._get_turn_resources(attacker)
        is_weapon_attack = pending_attack.get("is_weapon_attack") is True
        hunters_mark_effect = cls._get_hunters_mark_effect_for_target(attacker, target_participant_id=target_participant.get("id", "") if target_participant else "") if is_weapon_attack else None
        if hunters_mark_effect is not None:
            hm_rolls, hm_damage = cls._resolve_damage_roll("1d6", roll_source="system")
            extra_damage += hm_damage
            extra_damage_rolls.extend(hm_rolls)
            extra_damage_label += " Hunter's Mark: +1d6."
        can_use_colossus_slayer = cls._player_has_colossus_slayer(attacker_data) and target_current_hp is not None and target_max_hp is not None and target_current_hp < target_max_hp and not turn_resources.get("colossus_slayer_used")
        if can_use_colossus_slayer:
            slayer_rolls, slayer_damage = cls._resolve_damage_roll("1d8", roll_source="system")
            extra_damage_rolls.extend(slayer_rolls)
            extra_damage += slayer_damage
            turn_resources["colossus_slayer_used"] = True
            attacker["turn_resources"] = turn_resources
            extra_damage_label += " Assassino de Colossos: +1d8."
        new_hp = effect_msg = previous_hp = concentration_check = None
        effect_msg = ""
        if damage > 0:
            new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                db,
                target_ref_id,
                target_kind,
                damage + extra_damage,
                damage_type=pending_attack.get("damage_type"),
                is_crit=bool(pending_attack.get("is_critical")),
                state=state,
                **cls._build_concentration_roll_kwargs(req.concentration_roll_source, req.concentration_manual_roll),
            )
        roll_result = RollResult.model_validate(pending_attack.get("roll_result")) if isinstance(pending_attack.get("roll_result"), dict) else None
        cls._clear_participant_pending_attack(attacker)
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        if damage > 0 and target_kind == "player":
            target_state, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
            await cls._emit_player_state_update(db, session_id, target_ref_id, target_state)
        elif damage > 0 and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_ref_id, previous_hp)
        await cls._emit_state(session_id, state)
        concentration_summary = f" {concentration_check['summary_text']}" if isinstance(concentration_check, dict) and isinstance(concentration_check.get("summary_text"), str) else ""
        await cls._emit_log(session_id, {"message": f"{attacker['display_name']} rolled damage with {pending_attack.get('weapon_name') or 'Attack'} against {target_display_name}: {damage + extra_damage} damage.{extra_damage_label}{effect_msg}{concentration_summary}", "actorUserId": actor_user_id, "source": "gm_override" if is_gm else "player_turn"})
        return {
            "roll": cls._safe_int(pending_attack.get("roll"), 0),
            "is_hit": True,
            "is_critical": bool(pending_attack.get("is_critical")),
            "target_ac": cls._safe_int(pending_attack.get("target_ac"), 10),
            "target_kind": "session_entity" if target_kind == "entity" else target_kind,
            "weapon_name": pending_attack.get("weapon_name") or "Attack",
            "damage": damage + extra_damage,
            "new_hp": new_hp,
            "damage_dice": pending_attack.get("damage_dice") or "",
            "damage_rolls": damage_rolls,
            "extra_damage_rolls": extra_damage_rolls,
            "base_damage": base_damage,
            "damage_bonus": damage_bonus,
            "attack_bonus": cls._safe_int(pending_attack.get("attack_bonus"), 0),
            "extra_damage": extra_damage,
            "roll_result": roll_result,
            "target_display_name": target_display_name,
            "damage_type": pending_attack.get("damage_type"),
            "pending_attack_id": None,
            "damage_roll_required": False,
            "damage_roll_source": req.roll_source,
            "concentration_check": concentration_check,
        }
