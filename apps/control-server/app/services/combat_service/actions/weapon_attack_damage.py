from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.roll import RollResult
from app.services.combat_service.sanctuary_guard import break_sanctuary_if_active

from ..exceptions import CombatServiceError
from ..host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _WeaponAttackDamageBase = CombatServiceHostProtocol
else:
    _WeaponAttackDamageBase = object


class WeaponAttackDamageMixin(_WeaponAttackDamageBase):
    @classmethod
    async def attack_damage(cls, db, session_id: str, req, actor_user_id: str, is_gm: bool):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
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

        target_ref_id = pending_attack.get("target_ref_id")
        target_kind = pending_attack.get("target_kind")
        target_display_name = pending_attack.get("target_display_name") or "Target"
        if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
            raise CombatServiceError("Pending damage roll is missing target information.", 400)
        target_participant = cls._get_participant_by_ref(state, target_ref_id)
        attacker_model, *_ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        attacker_data = cls._as_dict(attacker_model.state_json)
        target_current_hp, target_max_hp = cls._get_target_hp_snapshot(db, session_id, target_ref_id, target_kind)
        
        import uuid
        components = []
        
        components.append({
            "id": str(uuid.uuid4()),
            "kind": "base_weapon",
            "source_key": pending_attack.get("weapon_item_id"),
            "source_label": pending_attack.get("weapon_name") or "Ataque",
            "dice": pending_attack.get("damage_dice") or "unarmed",
            "rolls": damage_rolls,
            "operation": "add",
            "signed_total": base_damage,
            "damage_type": pending_attack.get("damage_type"),
            "doubled_on_critical": bool(pending_attack.get("is_critical")),
            "minimum_total_damage": None,
        })
        
        if damage_bonus != 0:
            components.append({
                "id": str(uuid.uuid4()),
                "kind": "ability_modifier",
                "source_key": None,
                "source_label": "Modificador",
                "dice": None,
                "rolls": [],
                "operation": "add" if damage_bonus >= 0 else "subtract",
                "signed_total": damage_bonus,
                "damage_type": pending_attack.get("damage_type"),
                "doubled_on_critical": False,
                "minimum_total_damage": None,
            })

        min_damage = 1

        for effect in cls._get_participant_effects(attacker):
            if effect.get("kind") == "damage_bonus" and isinstance(effect.get("numeric_value"), int):
                val = effect["numeric_value"]
                if val != 0:
                    components.append({
                        "id": str(uuid.uuid4()),
                        "kind": "flat_modifier",
                        "source_key": effect.get("id"),
                        "source_label": cls._effect_label(effect),
                        "dice": None,
                        "rolls": [],
                        "operation": "add" if val >= 0 else "subtract",
                        "signed_total": val,
                        "damage_type": pending_attack.get("damage_type"),
                        "doubled_on_critical": False,
                        "minimum_total_damage": None,
                    })
            elif effect.get("kind") == "modify_weapon_damage":
                params = effect.get("metadata", {}).get("declarative_effect", {}).get("params", {})
                dice = params.get("dice")
                operation = params.get("operation") or "add"
                min_total = params.get("minimum_total_damage")
                
                if isinstance(min_total, int):
                    min_damage = max(min_damage, min_total)

                if dice:
                    rolls, total = cls._resolve_damage_roll(dice, critical=bool(pending_attack.get("is_critical")), roll_source=req.roll_source)
                    signed_total = total if operation == "add" else -total
                    components.append({
                        "id": str(uuid.uuid4()),
                        "kind": "weapon_damage_modifier",
                        "source_key": effect.get("id"),
                        "source_label": cls._effect_label(effect),
                        "dice": dice,
                        "rolls": rolls,
                        "operation": operation,
                        "signed_total": signed_total,
                        "damage_type": pending_attack.get("damage_type"),
                        "doubled_on_critical": bool(pending_attack.get("is_critical")),
                        "minimum_total_damage": min_total,
                    })

        turn_resources = cls._get_turn_resources(attacker)
        is_weapon_attack = pending_attack.get("is_weapon_attack") is True
        
        hunters_mark_effect = cls._get_hunters_mark_effect_for_target(attacker, target_participant_id=target_participant.get("id", "") if target_participant else "") if is_weapon_attack else None
        if hunters_mark_effect is not None:
            hm_rolls, hm_damage = cls._resolve_damage_roll("1d6", critical=bool(pending_attack.get("is_critical")), roll_source="system")
            components.append({
                "id": str(uuid.uuid4()),
                "kind": "extra_damage",
                "source_key": "hunters_mark",
                "source_label": "Hunter's Mark",
                "dice": "1d6",
                "rolls": hm_rolls,
                "operation": "add",
                "signed_total": hm_damage,
                "damage_type": pending_attack.get("damage_type"),
                "doubled_on_critical": bool(pending_attack.get("is_critical")),
                "minimum_total_damage": None,
            })

        can_use_colossus_slayer = cls._player_has_colossus_slayer(attacker_data) and target_current_hp is not None and target_max_hp is not None and target_current_hp < target_max_hp and not turn_resources.get("colossus_slayer_used")
        if can_use_colossus_slayer:
            slayer_rolls, slayer_damage = cls._resolve_damage_roll("1d8", critical=bool(pending_attack.get("is_critical")), roll_source="system")
            components.append({
                "id": str(uuid.uuid4()),
                "kind": "extra_damage",
                "source_key": "colossus_slayer",
                "source_label": "Assassino de Colossos",
                "dice": "1d8",
                "rolls": slayer_rolls,
                "operation": "add",
                "signed_total": slayer_damage,
                "damage_type": pending_attack.get("damage_type"),
                "doubled_on_critical": bool(pending_attack.get("is_critical")),
                "minimum_total_damage": None,
            })
            turn_resources["colossus_slayer_used"] = True
            attacker["turn_resources"] = turn_resources

        total_before_minimum = sum(c["signed_total"] for c in components)
        minimum_applied = min_damage if total_before_minimum < min_damage else None
        final_damage = max(min_damage, total_before_minimum)

        damage_breakdown = {
            "total_before_minimum": total_before_minimum,
            "minimum_applied": minimum_applied,
            "total": final_damage,
            "components": components,
        }

        extra_damage_rolls = []
        extra_damage_label = ""
        for c in components:
            if c["kind"] in ("extra_damage", "weapon_damage_modifier", "flat_modifier"):
                extra_damage_rolls.extend(c["rolls"])
                op_sign = "+" if c["signed_total"] >= 0 else "-"
                extra_damage_label += f" {c['source_label']}: {op_sign}{abs(c['signed_total'])}."
        new_hp = effect_msg = previous_hp = concentration_check = None
        effect_msg = ""
        if final_damage > 0:
            new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                db,
                target_ref_id,
                target_kind,
                final_damage,
                damage_type=pending_attack.get("damage_type"),
                is_magical_damage=bool(pending_attack.get("is_magical_damage")),
                is_crit=bool(pending_attack.get("is_critical")),
                state=state,
                attacker_participant_id=attacker.get("id"),
                **cls._build_concentration_roll_kwargs(req.concentration_roll_source, req.concentration_manual_roll),
            )
        rider_result = await cls.resolve_next_weapon_hit_riders(
            db,
            session_id,
            state=state,
            attacker=attacker,
            target_participant=target_participant,
            is_weapon_attack=is_weapon_attack,
        )
        rider_log_suffix = str(rider_result.get("log_suffix") or "")
        roll_result = RollResult.model_validate(pending_attack.get("roll_result")) if isinstance(pending_attack.get("roll_result"), dict) else None
        cls._clear_participant_pending_attack(attacker)
        # Attacker dealt damage — their own sanctuary ends.
        if final_damage > 0:
            break_sanctuary_if_active(attacker, state)
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        if final_damage > 0 and target_kind == "player":
            target_state, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
            await cls._emit_player_state_update(db, session_id, target_ref_id, target_state)
        elif final_damage > 0 and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_ref_id, previous_hp)
        await cls._emit_state(session_id, state)
        concentration_summary = f" {concentration_check['summary_text']}" if isinstance(concentration_check, dict) and isinstance(concentration_check.get("summary_text"), str) else ""
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker["display_name"], {"message": f"{attacker['display_name']} rolled damage with {pending_attack.get('weapon_name') or 'Attack'} against {target_display_name}: {final_damage} damage.{extra_damage_label}{effect_msg}{rider_log_suffix}{concentration_summary}", "actorUserId": actor_user_id, "source": "gm_override" if is_gm else "player_turn"})
        return {
            "roll": cls._safe_int(pending_attack.get("roll"), 0),
            "is_hit": True,
            "is_critical": bool(pending_attack.get("is_critical")),
            "target_ac": cls._safe_int(pending_attack.get("target_ac"), 10),
            "target_kind": "session_entity" if target_kind == "entity" else target_kind,
            "weapon_name": pending_attack.get("weapon_name") or "Attack",
            "damage": final_damage,
            "new_hp": new_hp,
            "damage_dice": pending_attack.get("damage_dice") or "",
            "damage_rolls": damage_rolls,
            "extra_damage_rolls": extra_damage_rolls,
            "extra_damage": sum(extra_damage_rolls),
            "extra_damage_label": extra_damage_label,
            "damage_breakdown": damage_breakdown,
            "base_damage": base_damage,
            "damage_bonus": damage_bonus,
            "attack_bonus": cls._safe_int(pending_attack.get("attack_bonus"), 0),
            "roll_result": roll_result,
            "target_display_name": target_display_name,
            "damage_type": pending_attack.get("damage_type"),
            "is_magical_damage": bool(pending_attack.get("is_magical_damage")),
            "pending_attack_id": None,
            "damage_roll_required": False,
            "damage_roll_source": req.roll_source,
            "concentration_check": concentration_check,
        }
