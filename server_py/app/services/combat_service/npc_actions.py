from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatResolveDamageRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.roll import RollActorStats, RollResult
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data

from .exceptions import CombatServiceError, _roll_dice_expression


class CombatNpcActionMixin:

    @classmethod
    async def entity_action(
        cls,
        db: Session,
        session_id: str,
        req: CombatEntityActionRequest,
        actor_user_id: str,
        is_gm: bool,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            req.actor_participant_id,
        )
        if attacker["kind"] != "session_entity":
            raise CombatServiceError("Only session entities can use combat actions.", 400)
        if not is_gm:
            raise CombatServiceError("Only GM can act for NPCs.", 403)
        cls._require_actor_status(attacker, ("active",), "You can only use combat actions when active.")

        _, npc, action = cls._get_combat_action_for_entity(db, attacker["ref_id"], req.combat_action_id)
        resolved_action = cls._resolve_entity_combat_action(db, session_id, npc, action)
        action_cost = resolved_action.get("actionCost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker, action_cost, is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )
        action_name = resolved_action.get("name") if isinstance(resolved_action.get("name"), str) else "Combat Action"
        action_kind = resolved_action.get("kind") if isinstance(resolved_action.get("kind"), str) else "utility"
        damage_type = resolved_action.get("damageType") if isinstance(resolved_action.get("damageType"), str) else None

        target_p = None
        if req.target_ref_id:
            target_p = next((p for p in state.participants if p["ref_id"] == req.target_ref_id), None)
            if not target_p:
                raise CombatServiceError("Target not found in combat")

        if action_kind != "utility" and not target_p:
            raise CombatServiceError("This combat action requires a target")
        if action_kind in ("weapon_attack", "spell_attack", "saving_throw"):
            cls._assert_hostile_action_allowed(
                attacker,
                target_p,
                action_label="a hostile action",
            )

        roll_total = None
        save_roll = None
        save_dc = None
        is_hit = None
        is_saved = None
        is_critical = False
        damage = 0
        healing = 0
        new_hp = None
        previous_hp = None
        effect_msg = ""
        concentration_check = None
        roll_result = None
        target_ac = None
        attack_bonus = None
        damage_dice = None
        damage_bonus = None
        pending_attack_id = None
        damage_rolls: list[int] = []
        base_damage = None
        damage_roll_source = None
        save_success_outcome = None

        if action_kind in ("weapon_attack", "spell_attack"):
            cls._clear_participant_pending_attack(attacker)
            _, target_ac, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
            target_ac = (target_ac or 10) + cls._sum_numeric_effects(target_p, "temp_ac_bonus")
            attack_bonus = cls._safe_int(
                resolved_action.get("spellAttackBonus")
                if action_kind == "spell_attack"
                else resolved_action.get("toHitBonus"),
                0,
            )
            attack_bonus += cls._sum_numeric_effects(attacker, "attack_bonus")
            damage_dice = resolved_action.get("damageDice") if isinstance(resolved_action.get("damageDice"), str) else None
            damage_bonus = cls._safe_int(resolved_action.get("damageBonus"), 0)
            has_adv = req.has_advantage or cls._has_effect_kind(attacker, "advantage_on_attacks")
            has_dis = req.has_disadvantage or cls._has_effect_kind(attacker, "disadvantage_on_attacks") or cls._has_effect_kind(target_p, "dodging")
            # Consume advantage_on_attacks (Help) after first use
            if not req.has_advantage and cls._has_effect_kind(attacker, "advantage_on_attacks"):
                cls._consume_first_effect(attacker, "advantage_on_attacks")
            adv_mode = "advantage" if (has_adv and not has_dis) else (
                "disadvantage" if (has_dis and not has_adv) else "normal"
            )
            roll_result = resolve_attack_base(
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
            is_fail = roll_result.selected_roll == 1
            roll_total = roll_result.total
            is_hit = bool(roll_result.success)
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
                        "roll": roll_total,
                    },
                )
            else:
                flag_modified(state, "participants")
        elif action_kind == "saving_throw":
            ability_name = cls._normalize_ability_name(resolved_action.get("saveAbility"))
            save_dc = cls._safe_int(resolved_action.get("saveDc"), 0)
            damage_dice = resolved_action.get("damageDice") if isinstance(resolved_action.get("damageDice"), str) else None
            damage_bonus = cls._safe_int(resolved_action.get("damageBonus"), 0)
            save_success_outcome = (
                cls._normalize_save_success_outcome(resolved_action.get("saveSuccessOutcome"))
                or "none"
            )
            if not ability_name or save_dc <= 0:
                raise CombatServiceError("Saving throw actions require save ability and save DC.")
            roll_result = resolve_saving_throw(
                cls._build_roll_actor_stats_for_save(
                    db,
                    session_id,
                    target_p["ref_id"],
                    target_p["kind"],
                    target_p["display_name"],
                ),
                ability=ability_name,
                dc=save_dc,
            )
            roll_result.is_gm_roll = is_gm
            save_roll = roll_result.total
            is_saved = bool(roll_result.success)
            damage_rolls, resolved_base_damage = cls._resolve_damage_roll(
                damage_dice or "",
                roll_source="system",
            )
            base_damage = resolved_base_damage
            damage_roll_source = "system"
            rolled_damage_total = max(
                0,
                resolved_base_damage + damage_bonus,
            )
            damage = cls._resolve_save_damage_amount(
                rolled_damage_total,
                is_saved=is_saved,
                save_success_outcome=save_success_outcome,
            )
            if damage > 0:
                new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                    db,
                    target_p["ref_id"],
                    target_p["kind"],
                    damage,
                    damage_type=damage_type,
                    is_crit=False,
                    state=state,
                    **cls._build_concentration_roll_kwargs(
                        req.concentration_roll_source,
                        req.concentration_manual_roll,
                    ),
                )
        elif action_kind == "heal":
            healing = max(
                0,
                _roll_dice_expression(resolved_action.get("healDice") or "")
                + cls._safe_int(resolved_action.get("healBonus"), 0),
            )
            if healing > 0:
                new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(
                    db,
                    target_p["ref_id"],
                    target_p["kind"],
                    healing,
                    state,
                )
        elif action_kind != "utility":
            raise CombatServiceError("Unsupported combat action kind.")

        db.add(state)
        db.commit()
        db.refresh(state)

        if target_p and new_hp is not None and target_p["kind"] == "player":
            target_state, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
            await cls._emit_player_state_update(db, session_id, target_p["ref_id"], target_state)
        elif target_p and previous_hp is not None and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_p["ref_id"], previous_hp)
        await cls._emit_state(session_id, state)

        if action_kind in ("weapon_attack", "spell_attack"):
            hit_text = "HIT" if is_hit else "MISSED"
            if is_critical:
                hit_text = "CRITICALLY HIT"
            damage_text = (
                f" for {damage} {damage_type or ''} damage".replace("  ", " ").strip()
                if is_hit and damage > 0
                else ""
            )
            target_text = target_p["display_name"] if target_p else "no target"
            log_message = f"{attacker['display_name']} used {action_name} on {target_text}: {hit_text} (roll {roll_total})"
            if pending_attack_id:
                log_message += ". Damage roll pending."
            elif damage_text:
                log_message += f" {damage_text}"
            log_message += effect_msg
        elif action_kind == "saving_throw":
            target_text = target_p["display_name"] if target_p else "no target"
            save_text = "SUCCEEDED" if is_saved else "FAILED"
            log_message = (
                f"{attacker['display_name']} used {action_name} on {target_text}: "
                f"{target_text} {save_text} the {resolved_action.get('saveAbility')} save "
                f"({save_roll} vs DC {save_dc})"
            )
            if is_saved and save_success_outcome == "half_damage":
                rolled_damage_total = max(0, (base_damage or 0) + cls._safe_int(damage_bonus, 0))
                log_message += (
                    f" and took half damage: {damage} {damage_type or ''} damage "
                    f"(rolled {rolled_damage_total})"
                ).replace("  ", " ")
            elif not is_saved and damage > 0:
                log_message += f" and took {damage} {damage_type or ''} damage".replace("  ", " ")
            elif is_saved:
                log_message += " and took no damage"
            log_message += effect_msg
        elif action_kind == "heal":
            target_text = target_p["display_name"] if target_p else attacker["display_name"]
            log_message = f"{attacker['display_name']} used {action_name} on {target_text}, healing {healing} HP{effect_msg}"
        else:
            description = resolved_action.get("description") if isinstance(resolved_action.get("description"), str) else ""
            log_message = f"{attacker['display_name']} used {action_name}."
            if description:
                log_message += f" {description}"

        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        if isinstance(concentration_check, dict) and isinstance(concentration_check.get("summary_text"), str):
            log_message = f"{log_message} {concentration_check['summary_text']}".strip()

        await cls._emit_log(session_id, {
            "message": log_message.strip(),
            "actorUserId": actor_user_id,
            "source": "gm_override",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        return {
            "action_name": action_name,
            "action_kind": action_kind,
            "damage": damage,
            "damage_type": damage_type,
            "healing": healing,
            "is_critical": is_critical,
            "is_hit": is_hit,
            "is_saved": is_saved,
            "new_hp": new_hp,
            "roll": roll_total,
            "save_dc": save_dc,
            "save_roll": save_roll,
            "save_success_outcome": save_success_outcome,
            "roll_result": roll_result,
            "target_ac": target_ac,
            "target_display_name": target_p["display_name"] if target_p else None,
            "damage_dice": damage_dice,
            "damage_bonus": damage_bonus,
            "attack_bonus": attack_bonus,
            "pending_attack_id": pending_attack_id,
            "damage_roll_required": bool(pending_attack_id),
            "damage_rolls": damage_rolls,
            "base_damage": base_damage,
            "damage_roll_source": damage_roll_source,
            "concentration_check": concentration_check,
        }

    @classmethod
    async def entity_action_damage(
        cls,
        db: Session,
        session_id: str,
        req: CombatResolveDamageRequest,
        actor_user_id: str,
        is_gm: bool,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            req.actor_participant_id,
        )
        if attacker["kind"] != "session_entity":
            raise CombatServiceError("Only session entities can use combat actions.", 400)
        if not is_gm:
            raise CombatServiceError("Only GM can act for NPCs.", 403)
        cls._require_actor_status(attacker, ("active",), "You can only roll damage when active.")

        pending_attack = cls._require_pending_attack(
            attacker,
            req.pending_attack_id,
            expected_type="entity_attack",
        )
        damage_dice = pending_attack.get("damage_dice") or ""
        damage_rolls, base_damage = cls._resolve_damage_roll(
            damage_dice,
            critical=bool(pending_attack.get("is_critical")),
            roll_source=req.roll_source,
            manual_rolls=req.manual_rolls,
        )
        damage_bonus = cls._safe_int(pending_attack.get("damage_bonus"), 0)
        effect_damage_bonus = cls._sum_numeric_effects(attacker, "damage_bonus")
        damage = max(0, base_damage + damage_bonus + effect_damage_bonus)
        target_ref_id = pending_attack.get("target_ref_id")
        target_kind = pending_attack.get("target_kind")
        target_display_name = pending_attack.get("target_display_name") or "Target"
        if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
            raise CombatServiceError("Pending damage roll is missing target information.", 400)

        new_hp = None
        previous_hp = None
        effect_msg = ""
        concentration_check = None
        if damage > 0:
            new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                db,
                target_ref_id,
                target_kind,
                damage,
                damage_type=pending_attack.get("damage_type"),
                is_crit=bool(pending_attack.get("is_critical")),
                state=state,
                **cls._build_concentration_roll_kwargs(
                    req.concentration_roll_source,
                    req.concentration_manual_roll,
                ),
            )

        roll_result_data = pending_attack.get("roll_result")
        roll_result = RollResult.model_validate(roll_result_data) if isinstance(roll_result_data, dict) else None
        cls._clear_participant_pending_attack(attacker)
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

        concentration_summary = (
            f" {concentration_check['summary_text']}"
            if isinstance(concentration_check, dict)
            and isinstance(concentration_check.get("summary_text"), str)
            else ""
        )
        await cls._emit_log(session_id, {
            "message": (
                f"{attacker['display_name']} used {pending_attack.get('action_name') or 'Combat Action'} on "
                f"{target_display_name} and dealt {damage} damage.{effect_msg}"
                f"{concentration_summary}"
            ),
            "actorUserId": actor_user_id,
            "source": "gm_override",
        })

        return {
            "action_name": pending_attack.get("action_name") or "Combat Action",
            "action_kind": pending_attack.get("action_kind") or "weapon_attack",
            "damage": damage,
            "damage_type": pending_attack.get("damage_type"),
            "healing": 0,
            "is_critical": bool(pending_attack.get("is_critical")),
            "is_hit": True,
            "is_saved": None,
            "new_hp": new_hp,
            "roll": cls._safe_int(pending_attack.get("roll"), 0),
            "save_dc": None,
            "save_roll": None,
            "roll_result": roll_result,
            "target_ac": cls._safe_int(pending_attack.get("target_ac"), 10),
            "target_display_name": target_display_name,
            "damage_dice": damage_dice or None,
            "damage_bonus": damage_bonus,
            "attack_bonus": cls._safe_int(pending_attack.get("attack_bonus"), 0),
            "pending_attack_id": None,
            "damage_roll_required": False,
            "damage_rolls": damage_rolls,
            "base_damage": base_damage,
            "damage_roll_source": req.roll_source,
            "concentration_check": concentration_check,
        }

    @classmethod
    async def death_save(
        cls,
        db: Session,
        session_id: str,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker_p = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            actor_participant_id,
        )
            
        if attacker_p["kind"] != "player":
            raise CombatServiceError("Only players roll Death Saves.")
        cls._require_actor_status(attacker_p, ("downed",), "You can only roll Death Saves when downed.")
            
        target_model, *_ = cls._get_stats(db, attacker_p["ref_id"], attacker_p["kind"], session_id)
        data = cls._as_dict(target_model.state_json)
        death_saves = cls._as_dict(data.get("deathSaves"))
        
        roll = random.randint(1, 20)
        msg = f"rolled a Death Save: {roll}."
        
        auto_proxy_next_turn = True
        if roll == 1:
            death_saves["failures"] += 2
            msg += " CRITICAL FAILURE (2 Fails)!"
        elif roll == 20:
            data["currentHP"] = 1
            msg += " CRITICAL SUCCESS! (Regains 1 HP, Stands Up!)"
            auto_proxy_next_turn = False
        elif roll >= 10:
            death_saves["successes"] += 1
            msg += " (Success!)"
        else:
            death_saves["failures"] += 1
            msg += " (Failure!)"

        data["deathSaves"] = death_saves
        target_model.state_json = finalize_session_state_data(data)
        status = cls._sync_participant_status(db, state, attacker_p["ref_id"], attacker_p["kind"], target_model)
        if status == "dead":
            msg += " THE CHARACTER HAS DIED."
        elif status == "stable":
            msg += " THE CHARACTER IS STABILIZED."
        flag_modified(target_model, "state_json")
        db.add(target_model)
        
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_player_state_update(db, session_id, attacker_p["ref_id"], target_model)
        
        await cls._emit_log(session_id, {
            "message": f"{attacker_p['display_name']} {msg}",
            "actorUserId": actor_user_id,
            "source": "player_turn" if not is_gm else "gm_override"
        })
        
        if auto_proxy_next_turn:
            await cls.next_turn(
                db,
                session_id,
                actor_user_id,
                is_gm,
                actor_participant_id=attacker_p.get("id"),
                skip_turn_end_validation=True,
            )
        else:
            await cls._emit_state(session_id, state)
            
        return {"roll": roll, "status": attacker_p["status"], "death_saves": death_saves}
