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
    CombatResolveSpellEffectRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
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
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.schemas.roll import RollActorStats, RollResult

from .exceptions import CombatServiceError, _parse_dice, _roll_dice_expression


class CombatPlayerActionMixin:

    @classmethod
    async def attack(
        cls,
        db: Session,
        session_id: str,
        req: CombatAttackRequest,
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
        cls._require_actor_status(attacker, ("active",), "You can only attack when active.")
        if attacker["kind"] != "player":
            raise CombatServiceError("Use entity actions for session entities.")
        cls._clear_participant_pending_attack(attacker)

        attacker_model, _, _, _, _, _ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        attacker_data = cls._as_dict(attacker_model.state_json)
        attack_context = cls._build_player_attack_context(
            db,
            session_id,
            attacker["ref_id"],
            attacker_data,
            req.weapon_item_id,
        )
        damage_dice = attack_context["damage_dice"]

        target_p = next((p for p in state.participants if p["ref_id"] == req.target_ref_id), None)
        if not target_p:
            raise CombatServiceError("Target not found in combat")

        _, target_ac, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
        target_ac = target_ac or 10
        adv_mode = "advantage" if (req.has_advantage and not req.has_disadvantage) else (
            "disadvantage" if (req.has_disadvantage and not req.has_advantage) else "normal"
        )
        roll_result = resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
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

        pending_attack_id = None
        if is_hit:
            pending_attack_id = cls._create_pending_attack(
                state,
                attacker,
                {
                    "type": "player_attack",
                    "target_ref_id": target_p["ref_id"],
                    "target_kind": target_p["kind"],
                    "target_display_name": target_p["display_name"],
                    "target_ac": target_ac,
                    "weapon_name": attack_context["name"],
                    "damage_dice": damage_dice,
                    "damage_bonus": attack_context["damage_bonus"],
                    "attack_bonus": attack_context["attack_bonus"],
                    "damage_type": attack_context.get("damage_type"),
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
        
        source = "gm_override" if is_gm else "player_turn"
        hit_text = "HIT" if is_hit else "MISSED"
        if is_crit:
            hit_text = "CRITICALLY HIT"
        if is_fail:
            hit_text = "CRITICALLY MISSED"
        message_suffix = " Damage roll pending." if is_hit else ""
        
        await cls._emit_log(session_id, {
            "message": (
                f"{attacker['display_name']} {hit_text} {target_p['display_name']} "
                f"(AC {target_ac}) with {attack_context['name']} and roll {atk_roll}.{message_suffix}"
            ),
            "actorUserId": actor_user_id,
            "source": source
        })
        return {
            "roll": atk_roll,
            "is_hit": is_hit,
            "damage": 0,
            "is_critical": is_crit,
            "new_hp": None,
            "roll_result": roll_result,
            "target_ac": target_ac,
            "target_display_name": target_p["display_name"],
            "target_kind": target_p["kind"],
            "weapon_name": attack_context["name"],
            "damage_dice": damage_dice,
            "damage_bonus": attack_context["damage_bonus"],
            "attack_bonus": attack_context["attack_bonus"],
            "damage_type": attack_context.get("damage_type"),
            "pending_attack_id": pending_attack_id,
            "damage_roll_required": is_hit,
        }

    @classmethod
    async def attack_damage(
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
        cls._require_actor_status(attacker, ("active",), "You can only roll damage when active.")
        if attacker["kind"] != "player":
            raise CombatServiceError("Use entity actions for session entities.")

        pending_attack = cls._require_pending_attack(
            attacker,
            req.pending_attack_id,
            expected_type="player_attack",
        )
        damage_dice = pending_attack.get("damage_dice") or "unarmed"
        damage_rolls, base_damage = cls._resolve_damage_roll(
            damage_dice,
            critical=bool(pending_attack.get("is_critical")),
            roll_source=req.roll_source,
            manual_rolls=req.manual_rolls,
        )
        damage_bonus = cls._safe_int(pending_attack.get("damage_bonus"), 0)
        damage = max(1, base_damage + damage_bonus)
        target_ref_id = pending_attack.get("target_ref_id")
        target_kind = pending_attack.get("target_kind")
        target_display_name = pending_attack.get("target_display_name") or "Target"
        if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
            raise CombatServiceError("Pending damage roll is missing target information.", 400)

        new_hp = None
        effect_msg = ""
        previous_hp = None
        if damage > 0:
            new_hp, effect_msg, previous_hp = cls._apply_damage_to_target(
                db,
                target_ref_id,
                target_kind,
                damage,
                bool(pending_attack.get("is_critical")),
                state,
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

        source = "gm_override" if is_gm else "player_turn"
        await cls._emit_log(session_id, {
            "message": (
                f"{attacker['display_name']} rolled damage with {pending_attack.get('weapon_name') or 'Attack'} "
                f"against {target_display_name}: {damage} damage.{effect_msg}"
            ),
            "actorUserId": actor_user_id,
            "source": source,
        })

        return {
            "roll": cls._safe_int(pending_attack.get("roll"), 0),
            "is_hit": True,
            "damage": damage,
            "is_critical": bool(pending_attack.get("is_critical")),
            "new_hp": new_hp,
            "roll_result": roll_result,
            "target_ac": cls._safe_int(pending_attack.get("target_ac"), 10),
            "target_display_name": target_display_name,
            "target_kind": target_kind,
            "weapon_name": pending_attack.get("weapon_name") or "Attack",
            "damage_dice": damage_dice,
            "damage_bonus": damage_bonus,
            "attack_bonus": cls._safe_int(pending_attack.get("attack_bonus"), 0),
            "damage_type": pending_attack.get("damage_type"),
            "pending_attack_id": None,
            "damage_roll_required": False,
            "damage_rolls": damage_rolls,
            "base_damage": base_damage,
            "damage_roll_source": req.roll_source,
        }

    @classmethod
    def _consume_player_spell_slot(cls, attacker_model: SessionState, slot_level: int) -> None:
        data = cls._as_dict(attacker_model.state_json)
        spellcasting = cls._as_dict(data.get("spellcasting"))
        slots = cls._as_dict(spellcasting.get("slots"))
        lvl_key = str(slot_level)
        slot_data = cls._as_dict(slots.get(lvl_key))
        if not slot_data:
            slot_data = {"used": 0, "max": 0}
        if slot_data.get("used", 0) >= slot_data.get("max", 0):
            raise CombatServiceError("No spell slots of this level remaining")
        slot_data["used"] = cls._safe_int(slot_data.get("used"), 0) + 1
        slots[lvl_key] = slot_data
        spellcasting["slots"] = slots
        data["spellcasting"] = spellcasting
        attacker_model.state_json = finalize_session_state_data(data)
        flag_modified(attacker_model, "state_json")

    @classmethod
    def _resolve_player_spell_context(
        cls,
        db: Session,
        session_id: str,
        attacker: dict,
        attacker_model: SessionState,
        req: CombatCastSpellRequest,
    ) -> dict:
        attacker_data = cls._as_dict(attacker_model.state_json)
        requested_canonical_key = (
            req.spell_canonical_key.strip()
            if isinstance(req.spell_canonical_key, str) and req.spell_canonical_key.strip()
            else (
                req.spell_id.strip()
                if isinstance(req.spell_id, str) and req.spell_id.strip()
                else None
            )
        )
        if not requested_canonical_key:
            raise CombatServiceError("Spell canonical key is required.", 400)

        catalog_spell = cls._get_spell_catalog_entry_for_session(db, session_id, requested_canonical_key)
        spell_name = (
            getattr(catalog_spell, "name_pt", None)
            or getattr(catalog_spell, "name_en", None)
            or requested_canonical_key
        )
        player_spell = cls._resolve_player_spell_entry(
            attacker_data,
            spell_canonical_key=getattr(catalog_spell, "canonical_key", None) or requested_canonical_key,
            spell_name=spell_name,
        )

        spell_level = cls._safe_int(player_spell.get("level"), getattr(catalog_spell, "level", 0))
        if spell_level > 0 and player_spell.get("prepared") is False:
            raise CombatServiceError("Spell is not prepared.", 400)

        _, _, _, _, prof_bonus, spell_mod = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        catalog_mode = getattr(catalog_spell, "automation_kind", None)
        catalog_save_ability = cls._normalize_ability_name(getattr(catalog_spell, "saving_throw", None))
        legacy_mode = "heal" if req.is_heal else ("spell_attack" if req.is_attack else None)
        spell_mode = req.spell_mode or (
            catalog_mode
            if isinstance(catalog_mode, str)
            and catalog_mode in ("spell_attack", "saving_throw", "direct_damage", "heal")
            else None
        ) or legacy_mode or ("saving_throw" if catalog_save_ability else None)
        if spell_mode not in ("spell_attack", "saving_throw", "direct_damage", "heal"):
            raise CombatServiceError("Spell cast mode is required for this spell.", 400)
        if spell_mode == "direct_damage" and catalog_save_ability:
            raise CombatServiceError(
                "This spell is structured as a saving throw spell. "
                "direct_damage is only allowed as an explicit fallback for spells without attack/save automation.",
                400,
            )

        slot_level = None
        if spell_level > 0:
            slot_level = req.slot_level or spell_level
            if slot_level < spell_level:
                raise CombatServiceError("Spell slot level cannot be lower than the spell level.", 400)

        legacy_expression = (
            req.dice_expression.strip()
            if isinstance(req.dice_expression, str) and req.dice_expression.strip()
            else None
        )

        effect_kind = "healing" if spell_mode == "heal" else "damage"
        effect_dice = None
        effect_bonus = 0
        damage_type = None
        save_ability = None
        save_dc = None
        attack_bonus = None

        if spell_mode == "heal":
            effect_dice = getattr(catalog_spell, "heal_dice", None)
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.heal_dice or (legacy_expression if req.is_heal else None)
            effect_bonus = getattr(catalog_spell, "heal_bonus", None)
            if not isinstance(effect_bonus, int):
                effect_bonus = req.heal_bonus if isinstance(req.heal_bonus, int) else 0
        else:
            effect_dice = getattr(catalog_spell, "damage_dice", None)
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.damage_dice or (legacy_expression if not req.is_heal else None)
            effect_bonus = getattr(catalog_spell, "damage_bonus", None)
            if not isinstance(effect_bonus, int):
                effect_bonus = req.damage_bonus if isinstance(req.damage_bonus, int) else 0
            damage_type = cls._normalize_damage_type(
                getattr(catalog_spell, "damage_type", None) or req.damage_type
            )
            if not damage_type:
                raise CombatServiceError("Spell damage type is missing a structured value.", 400)

        if isinstance(effect_dice, str):
            effect_dice = effect_dice.strip() or None
        if effect_dice:
            count, sides, _ = _parse_dice(effect_dice)
            if count <= 0 or sides <= 0:
                raise CombatServiceError("Spell effect dice must use a valid dice expression.", 400)
        elif effect_bonus <= 0:
            raise CombatServiceError("Spell effect is missing structured dice or a fixed bonus.", 400)

        if spell_mode == "spell_attack":
            attack_bonus = getattr(catalog_spell, "spell_attack_bonus", None)
            if not isinstance(attack_bonus, int):
                attack_bonus = req.spell_attack_bonus if isinstance(req.spell_attack_bonus, int) else None
            if not isinstance(attack_bonus, int):
                attack_bonus = spell_mod + prof_bonus
        elif spell_mode == "saving_throw":
            save_ability = cls._normalize_ability_name(req.save_ability or catalog_save_ability)
            save_dc = getattr(catalog_spell, "save_dc", None)
            if not isinstance(save_dc, int):
                save_dc = req.save_dc if isinstance(req.save_dc, int) else None
            if not isinstance(save_dc, int):
                save_dc = 8 + prof_bonus + spell_mod
            if not save_ability or save_dc <= 0:
                raise CombatServiceError("Saving throw spells require save ability and save DC.", 400)

        return {
            "spell_name": spell_name,
            "spell_canonical_key": getattr(catalog_spell, "canonical_key", None) or requested_canonical_key,
            "spell_mode": spell_mode,
            "effect_kind": effect_kind,
            "effect_dice": effect_dice,
            "effect_bonus": effect_bonus,
            "damage_type": damage_type,
            "save_ability": save_ability,
            "save_dc": save_dc,
            "attack_bonus": attack_bonus,
            "slot_level": slot_level,
        }

    @classmethod
    def _apply_spell_effect(
        cls,
        db: Session,
        state: CombatState,
        target_ref_id: str,
        target_kind: str,
        effect_kind: str,
        amount: int,
        *,
        is_critical: bool = False,
    ) -> tuple[int | None, str, int | None]:
        if amount <= 0:
            return None, "", None
        if effect_kind == "healing":
            return cls._apply_healing_to_target(db, target_ref_id, target_kind, amount, state)
        return cls._apply_damage_to_target(db, target_ref_id, target_kind, amount, is_critical, state)

    @classmethod
    async def cast_spell(cls, db: Session, session_id: str, req: CombatCastSpellRequest, actor_user_id: str, is_gm: bool):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            req.actor_participant_id,
        )
        cls._require_actor_status(attacker, ("active",), "You can only cast a spell when active.")
        if attacker["kind"] != "player":
            raise CombatServiceError("Only players can use this spell casting flow.", 400)

        had_pending = isinstance(attacker.get("pending_attack"), dict)
        cls._clear_participant_pending_attack(attacker)
        if had_pending:
            flag_modified(state, "participants")

        attacker_model, _, _, _, _, _ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        spell_context = cls._resolve_player_spell_context(
            db,
            session_id,
            attacker,
            attacker_model,
            req,
        )

        target_p = next((p for p in state.participants if p["ref_id"] == req.target_ref_id), None)
        if not target_p:
            raise CombatServiceError("Target not found in combat")

        slot_spent = False
        if isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        roll_result = None
        target_ac = None
        roll_total = None
        is_critical = False
        is_hit = None
        is_saved = None
        pending_spell_id = None
        damage = 0
        healing = 0
        new_hp = None
        effect_msg = ""
        previous_hp = None
        source = "gm_override" if is_gm else "player_turn"

        effect_roll_required = spell_context["effect_dice"] is not None
        spell_mode = spell_context["spell_mode"]
        effect_kind = spell_context["effect_kind"]
        effect_bonus = cls._safe_int(spell_context.get("effect_bonus"), 0)

        if spell_mode == "spell_attack":
            _, target_ac, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
            adv_mode = "advantage" if (req.has_advantage and not req.has_disadvantage) else (
                "disadvantage" if (req.has_disadvantage and not req.has_advantage) else "normal"
            )
            roll_result = resolve_attack_base(
                RollActorStats(
                    display_name=attacker["display_name"],
                    abilities={},
                    actor_kind="player",
                    actor_ref_id=attacker["ref_id"],
                ),
                advantage_mode=adv_mode,
                bonus_override=cls._safe_int(spell_context.get("attack_bonus"), 0),
                target_ac=target_ac or 10,
                roll_source=req.roll_source,
                manual_roll=req.manual_roll,
                manual_rolls=req.manual_rolls,
            )
            roll_result.is_gm_roll = is_gm
            roll_result.roll_source = req.roll_source
            roll_total = roll_result.total
            is_critical = roll_result.selected_roll == 20
            is_hit = bool(roll_result.success)
            if is_hit and effect_roll_required:
                pending_spell_id = cls._create_pending_spell_effect(
                    state,
                    attacker,
                    {
                        "spell_name": spell_context["spell_name"],
                        "spell_canonical_key": spell_context["spell_canonical_key"],
                        "action_kind": spell_mode,
                        "effect_kind": effect_kind,
                        "effect_dice": spell_context["effect_dice"],
                        "effect_bonus": effect_bonus,
                        "damage_type": spell_context.get("damage_type"),
                        "target_ref_id": target_p["ref_id"],
                        "target_kind": target_p["kind"],
                        "target_display_name": target_p["display_name"],
                        "target_ac": target_ac or 10,
                        "save_ability": spell_context.get("save_ability"),
                        "save_dc": spell_context.get("save_dc"),
                        "is_critical": is_critical,
                        "roll": roll_total,
                        "roll_result": roll_result.model_dump(mode="json"),
                    },
                )
            elif is_hit:
                amount = max(0, effect_bonus)
                new_hp, effect_msg, previous_hp = cls._apply_spell_effect(
                    db,
                    state,
                    target_p["ref_id"],
                    target_p["kind"],
                    effect_kind,
                    amount,
                    is_critical=is_critical,
                )
                if effect_kind == "healing":
                    healing = amount
                else:
                    damage = amount
            else:
                flag_modified(state, "participants")
        elif spell_mode == "saving_throw":
            roll_result = resolve_saving_throw(
                cls._build_roll_actor_stats_for_save(
                    db,
                    session_id,
                    target_p["ref_id"],
                    target_p["kind"],
                    target_p["display_name"],
                ),
                ability=spell_context["save_ability"],
                dc=cls._safe_int(spell_context.get("save_dc"), 0),
            )
            roll_result.is_gm_roll = is_gm
            roll_total = roll_result.total
            is_saved = bool(roll_result.success)
            if not is_saved and effect_roll_required:
                pending_spell_id = cls._create_pending_spell_effect(
                    state,
                    attacker,
                    {
                        "spell_name": spell_context["spell_name"],
                        "spell_canonical_key": spell_context["spell_canonical_key"],
                        "action_kind": spell_mode,
                        "effect_kind": effect_kind,
                        "effect_dice": spell_context["effect_dice"],
                        "effect_bonus": effect_bonus,
                        "damage_type": spell_context.get("damage_type"),
                        "target_ref_id": target_p["ref_id"],
                        "target_kind": target_p["kind"],
                        "target_display_name": target_p["display_name"],
                        "save_ability": spell_context.get("save_ability"),
                        "save_dc": spell_context.get("save_dc"),
                        "is_critical": False,
                        "roll": roll_total,
                        "roll_result": roll_result.model_dump(mode="json"),
                    },
                )
            elif not is_saved:
                amount = max(0, effect_bonus)
                new_hp, effect_msg, previous_hp = cls._apply_spell_effect(
                    db,
                    state,
                    target_p["ref_id"],
                    target_p["kind"],
                    effect_kind,
                    amount,
                )
                if effect_kind == "healing":
                    healing = amount
                else:
                    damage = amount
            else:
                flag_modified(state, "participants")
        else:
            if effect_roll_required:
                pending_spell_id = cls._create_pending_spell_effect(
                    state,
                    attacker,
                    {
                        "spell_name": spell_context["spell_name"],
                        "spell_canonical_key": spell_context["spell_canonical_key"],
                        "action_kind": spell_mode,
                        "effect_kind": effect_kind,
                        "effect_dice": spell_context["effect_dice"],
                        "effect_bonus": effect_bonus,
                        "damage_type": spell_context.get("damage_type"),
                        "target_ref_id": target_p["ref_id"],
                        "target_kind": target_p["kind"],
                        "target_display_name": target_p["display_name"],
                        "save_ability": spell_context.get("save_ability"),
                        "save_dc": spell_context.get("save_dc"),
                        "is_critical": False,
                        "roll": None,
                        "roll_result": None,
                    },
                )
            else:
                amount = max(0, effect_bonus)
                new_hp, effect_msg, previous_hp = cls._apply_spell_effect(
                    db,
                    state,
                    target_p["ref_id"],
                    target_p["kind"],
                    effect_kind,
                    amount,
                )
                if effect_kind == "healing":
                    healing = amount
                else:
                    damage = amount

        db.add(state)
        db.commit()
        db.refresh(state)

        player_state_ids_to_emit = set()
        if slot_spent:
            player_state_ids_to_emit.add(attacker["ref_id"])
        if (damage > 0 or healing > 0) and target_p["kind"] == "player":
            player_state_ids_to_emit.add(target_p["ref_id"])

        for player_ref_id in player_state_ids_to_emit:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, player_ref_id, target_state)
        if (damage > 0 or healing > 0) and target_p["kind"] == "session_entity" and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_p["ref_id"], previous_hp)
        await cls._emit_state(session_id, state)

        if spell_mode == "spell_attack":
            if is_hit:
                log_message = (
                    f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"{roll_total} total vs AC {target_ac or 10} - acerto."
                )
                if pending_spell_id:
                    log_message += " Efeito pendente."
                elif damage > 0:
                    log_message += f" {damage} de dano de {spell_context.get('damage_type') or 'energia'}{effect_msg}"
                elif healing > 0:
                    log_message += f" {healing} HP restaurados{effect_msg}"
            else:
                log_message = (
                    f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"{roll_total} total vs AC {target_ac or 10} - errou."
                )
        elif spell_mode == "saving_throw":
            save_text = "passou" if is_saved else "falhou"
            log_message = (
                f"{attacker['display_name']} lancou {spell_context['spell_name']} em {target_p['display_name']}: "
                f"alvo {save_text} no save de {spell_context['save_ability']} contra CD {spell_context['save_dc']}."
            )
            if pending_spell_id:
                log_message += " Efeito pendente."
            elif damage > 0:
                log_message += f" {damage} de dano de {spell_context.get('damage_type') or 'energia'}{effect_msg}"
        elif effect_kind == "healing":
            log_message = (
                f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}."
            )
            if pending_spell_id:
                log_message += " Cura pendente."
            else:
                log_message += f" {healing} HP restaurados{effect_msg}"
        else:
            log_message = (
                f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}."
            )
            if pending_spell_id:
                log_message += " Dano pendente."
            else:
                log_message += f" {damage} de dano de {spell_context.get('damage_type') or 'energia'}{effect_msg}"

        await cls._emit_log(session_id, {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": source,
        })
        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_mode,
            "effect_kind": effect_kind,
            "damage": damage,
            "healing": healing,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": is_critical,
            "is_hit": is_hit,
            "is_saved": is_saved,
            "new_hp": new_hp,
            "roll": roll_total,
            "roll_result": roll_result,
            "target_ac": target_ac,
            "target_display_name": target_p["display_name"],
            "target_kind": target_p["kind"],
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": effect_bonus,
            "pending_spell_id": pending_spell_id,
            "effect_roll_required": bool(pending_spell_id),
        }

    @classmethod
    async def cast_spell_effect(
        cls,
        db: Session,
        session_id: str,
        req: CombatResolveSpellEffectRequest,
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
        cls._require_actor_status(attacker, ("active",), "You can only resolve spell effects when active.")
        if attacker["kind"] != "player":
            raise CombatServiceError("Only players can use this spell casting flow.", 400)

        pending_spell = cls._require_pending_spell_effect(attacker, req.pending_spell_id)
        effect_kind = pending_spell.get("effect_kind") or "damage"
        effect_dice = pending_spell.get("effect_dice")
        effect_bonus = cls._safe_int(pending_spell.get("effect_bonus"), 0)
        roll_result_data = pending_spell.get("roll_result")
        roll_result = RollResult.model_validate(roll_result_data) if isinstance(roll_result_data, dict) else None
        target_ref_id = pending_spell.get("target_ref_id")
        target_kind = pending_spell.get("target_kind")
        target_display_name = pending_spell.get("target_display_name") or "Target"
        if not isinstance(target_ref_id, str) or not isinstance(target_kind, str):
            raise CombatServiceError("Pending spell effect is missing target information.", 400)

        effect_rolls: list[int] = []
        base_effect = 0
        if isinstance(effect_dice, str) and effect_dice.strip():
            effect_rolls, base_effect = cls._resolve_damage_roll(
                effect_dice,
                critical=bool(pending_spell.get("is_critical")) and effect_kind == "damage",
                roll_source=req.roll_source,
                manual_rolls=req.manual_rolls,
            )
        amount = max(0, base_effect + effect_bonus)
        new_hp = None
        effect_msg = ""
        previous_hp = None
        if amount > 0:
            new_hp, effect_msg, previous_hp = cls._apply_spell_effect(
                db,
                state,
                target_ref_id,
                target_kind,
                effect_kind,
                amount,
                is_critical=bool(pending_spell.get("is_critical")),
            )

        cls._clear_participant_pending_attack(attacker)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        if amount > 0 and target_kind == "player":
            target_state, *_ = cls._get_stats(db, target_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, target_ref_id, target_state)
        elif amount > 0 and target_kind == "session_entity" and previous_hp != new_hp:
            await cls._emit_entity_hp_update(db, session_id, target_ref_id, previous_hp)
        await cls._emit_state(session_id, state)

        amount_label = "HP restaurados" if effect_kind == "healing" else f"de dano de {pending_spell.get('damage_type') or 'energia'}"
        await cls._emit_log(session_id, {
            "message": (
                f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                f"{target_display_name}: {amount} {amount_label}{effect_msg}"
            ),
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
        })

        return {
            "spell_name": pending_spell.get("spell_name") or "Spell",
            "spell_canonical_key": pending_spell.get("spell_canonical_key"),
            "action_kind": pending_spell.get("action_kind") or "direct_damage",
            "effect_kind": effect_kind,
            "damage": amount if effect_kind != "healing" else 0,
            "healing": amount if effect_kind == "healing" else 0,
            "damage_type": pending_spell.get("damage_type"),
            "is_critical": bool(pending_spell.get("is_critical")),
            "is_hit": True if pending_spell.get("action_kind") == "spell_attack" else None,
            "is_saved": False if pending_spell.get("action_kind") == "saving_throw" else None,
            "new_hp": new_hp,
            "roll": cls._safe_int(pending_spell.get("roll"), 0) if pending_spell.get("roll") is not None else None,
            "roll_result": roll_result,
            "target_ac": cls._safe_optional_int(pending_spell.get("target_ac")),
            "target_display_name": target_display_name,
            "target_kind": target_kind,
            "save_ability": pending_spell.get("save_ability"),
            "save_dc": cls._safe_optional_int(pending_spell.get("save_dc")),
            "effect_dice": effect_dice,
            "effect_bonus": effect_bonus,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "effect_rolls": effect_rolls,
            "base_effect": base_effect,
            "effect_roll_source": req.roll_source,
        }
