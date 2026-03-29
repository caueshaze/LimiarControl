from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.campaign_member import CampaignMember
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
from app.services.draconic_ancestry import resolve_elemental_affinity
from app.services.magic_item_effects import (
    consume_inventory_item_charge,
    get_magic_item_effect,
    get_inventory_item_charges_current,
    get_magic_item_spell_key,
)
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.schemas.roll import RollActorStats, RollResult

from .exceptions import CombatServiceError, _parse_dice


class CombatPlayerActionMixin:

    @classmethod
    def _resolve_player_inventory_spell_item(
        cls,
        db: Session,
        session_id: str,
        *,
        player_user_id: str,
        inventory_item_id: str,
    ) -> tuple[InventoryItem, Item, dict]:
        session_entry = db.exec(
            select(CampaignSession).where(CampaignSession.id == session_id)
        ).first()
        if not session_entry:
            raise CombatServiceError("Session not found.", 404)

        member = db.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.user_id == player_user_id,
            )
        ).first()
        if not member or not member.id:
            raise CombatServiceError("Campaign member not found for this player.", 400)

        inventory_entry = db.exec(
            select(InventoryItem).where(
                InventoryItem.id == inventory_item_id,
                InventoryItem.campaign_id == session_entry.campaign_id,
                InventoryItem.member_id == member.id,
            )
        ).first()
        if not inventory_entry:
            raise CombatServiceError("Magic item not found in the player's inventory.", 404)
        if session_entry.party_id is not None and inventory_entry.party_id not in (None, session_entry.party_id):
            raise CombatServiceError("Magic item is not available in this session party.", 400)

        item = db.exec(
            select(Item).where(
                Item.id == inventory_entry.item_id,
                Item.campaign_id == session_entry.campaign_id,
            )
        ).first()
        if not item:
            raise CombatServiceError("Catalog item for the magic item was not found.", 404)

        effect = get_magic_item_effect(item)
        if not effect or effect.get("type") != "cast_spell":
            raise CombatServiceError("This item cannot cast a spell.", 400)

        return inventory_entry, item, effect

    @classmethod
    def _get_target_hp_snapshot(
        cls,
        db: Session,
        session_id: str,
        target_ref_id: str,
        target_kind: str,
    ) -> tuple[int | None, int | None]:
        target_model, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
        if target_kind == "player":
            data = cls._as_dict(target_model.state_json)
            return (
                cls._safe_int(data.get("currentHP"), 0),
                cls._safe_int(data.get("maxHP"), 0),
            )

        npc = db.exec(
            select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)
        ).first()
        max_hp = npc.max_hp if npc and npc.max_hp is not None else 0
        current_hp = target_model.current_hp if target_model.current_hp is not None else max_hp
        return current_hp, max_hp

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

        # Wild Shape: regular weapon attacks are replaced by natural attacks
        attacker_model, _, _, _, _, _ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        attacker_data = cls._as_dict(attacker_model.state_json)
        if cls._as_dict(attacker_data.get("wildShape")).get("active"):
            raise CombatServiceError(
                "Cannot use weapon attacks while in Wild Shape. Use wild-shape-attack instead.", 400
            )

        was_overridden = cls._consume_turn_resource(
            attacker, "action", is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )
        cls._clear_participant_pending_attack(attacker)
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
        cls._assert_hostile_action_allowed(
            attacker,
            target_p,
            action_label="an attack",
        )

        _, target_ac, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
        target_ac = target_ac or 10
        target_ac += cls._sum_numeric_effects(target_p, "temp_ac_bonus")
        attack_context["attack_bonus"] += cls._sum_numeric_effects(attacker, "attack_bonus")
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
        
        source = "gm_override" if is_gm else "player_turn"
        hit_text = "HIT" if is_hit else "MISSED"
        if is_crit:
            hit_text = "CRITICALLY HIT"
        if is_fail:
            hit_text = "CRITICALLY MISSED"
        message_suffix = " Damage roll pending." if is_hit else ""
        
        if was_overridden:
            hit_text = f"[OVERRIDE: Action limit ignored] {hit_text}"

        await cls._emit_log(session_id, {
            "message": (
                f"{attacker['display_name']} {hit_text} {target_p['display_name']} "
                f"(AC {target_ac}) with {attack_context['name']} and roll {atk_roll}.{message_suffix}"
            ),
            "actorUserId": actor_user_id,
            "source": source,
            "is_override": was_overridden,
            "overridden_resource": "action" if was_overridden else None,
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
        target_current_hp, target_max_hp = cls._get_target_hp_snapshot(
            db,
            session_id,
            target_ref_id,
            target_kind,
        )
        extra_damage = 0
        extra_damage_rolls: list[int] = []
        extra_damage_label = ""
        turn_resources = cls._get_turn_resources(attacker)
        is_weapon_attack = pending_attack.get("is_weapon_attack") is True

        hunters_mark_effect = (
            cls._get_hunters_mark_effect_for_target(
                attacker,
                target_participant_id=target_participant.get("id", "") if target_participant else "",
            )
            if is_weapon_attack
            else None
        )
        if hunters_mark_effect is not None:
            hm_rolls, hm_damage = cls._resolve_damage_roll(
                "1d6",
                roll_source="system",
            )
            extra_damage += hm_damage
            extra_damage_rolls.extend(hm_rolls)
            extra_damage_label += " Hunter's Mark: +1d6."

        can_use_colossus_slayer = (
            cls._player_has_colossus_slayer(attacker_data)
            and target_current_hp is not None
            and target_max_hp is not None
            and target_current_hp < target_max_hp
            and not turn_resources.get("colossus_slayer_used")
        )
        if can_use_colossus_slayer:
            colossus_rolls, colossus_damage = cls._resolve_damage_roll(
                "1d8",
                roll_source="system",
            )
            extra_damage_rolls.extend(colossus_rolls)
            extra_damage += colossus_damage
            turn_resources["colossus_slayer_used"] = True
            attacker["turn_resources"] = turn_resources
            extra_damage_label += " Assassino de Colossos: +1d8."

        new_hp = None
        effect_msg = ""
        previous_hp = None
        concentration_check = None
        if damage > 0:
            new_hp, effect_msg, previous_hp, concentration_check = cls._apply_damage_to_target(
                db,
                target_ref_id,
                target_kind,
                damage + extra_damage,
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

        source = "gm_override" if is_gm else "player_turn"
        concentration_summary = (
            f" {concentration_check['summary_text']}"
            if isinstance(concentration_check, dict)
            and isinstance(concentration_check.get("summary_text"), str)
            else ""
        )
        await cls._emit_log(session_id, {
            "message": (
                f"{attacker['display_name']} rolled damage with {pending_attack.get('weapon_name') or 'Attack'} "
                f"against {target_display_name}: {damage + extra_damage} damage.{extra_damage_label}{effect_msg}"
                f"{concentration_summary}"
            ),
            "actorUserId": actor_user_id,
            "source": source,
        })

        return {
            "roll": cls._safe_int(pending_attack.get("roll"), 0),
            "is_hit": True,
            "damage": damage + extra_damage,
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
            "extra_damage_rolls": extra_damage_rolls,
            "extra_damage": extra_damage,
            "damage_roll_source": req.roll_source,
            "concentration_check": concentration_check,
        }

    @classmethod
    async def wild_shape_attack(
        cls,
        db: Session,
        session_id: str,
        req,  # CombatWildShapeAttackRequest — imported at call site to avoid circular import
        actor_user_id: str,
        is_gm: bool,
    ):
        """Perform a natural weapon attack while in Wild Shape.

        Unlike regular attacks this method builds the attack context from the
        beast catalog instead of the player's inventory.
        """
        from app.services.wild_shape_catalog import get_form

        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state, actor_user_id, is_gm, req.actor_participant_id
        )
        cls._require_actor_status(attacker, ("active",), "You can only attack when active.")
        if attacker["kind"] != "player":
            raise CombatServiceError("Wild Shape attack is only for players.")

        attacker_model, _, str_score, dex_score, prof_bonus, _ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        attacker_data = cls._as_dict(attacker_model.state_json)
        ws = cls._as_dict(attacker_data.get("wildShape"))
        if not ws.get("active"):
            raise CombatServiceError("Not in Wild Shape.", 400)

        form_key = ws.get("formKey")
        form = get_form(form_key) if isinstance(form_key, str) else None
        if form is None:
            raise CombatServiceError(f"Unknown Wild Shape form: {form_key!r}", 400)

        attack_index = cls._safe_int(getattr(req, "attack_index", 0), 0)
        if attack_index < 0 or attack_index >= len(form.natural_attacks):
            raise CombatServiceError(
                f"Invalid attack_index {attack_index} for form {form_key!r} "
                f"(has {len(form.natural_attacks)} natural attack(s))",
                400,
            )
        natural_attack = form.natural_attacks[attack_index]

        was_overridden = cls._consume_turn_resource(
            attacker, "action", is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )
        cls._clear_participant_pending_attack(attacker)

        target_p = next((p for p in state.participants if p["ref_id"] == req.target_ref_id), None)
        if not target_p:
            raise CombatServiceError("Target not found in combat")

        _, target_ac, *_ = cls._get_stats(db, target_p["ref_id"], target_p["kind"], session_id)
        target_ac = target_ac or 10
        target_ac += cls._sum_numeric_effects(target_p, "temp_ac_bonus")

        # Build attack bonus: beast's fixed attack_bonus (includes STR/DEX mod + prof)
        attack_bonus = natural_attack.attack_bonus
        attack_bonus += cls._sum_numeric_effects(attacker, "attack_bonus")

        has_adv = req.has_advantage or cls._has_effect_kind(attacker, "advantage_on_attacks")
        has_dis = req.has_disadvantage or cls._has_effect_kind(attacker, "disadvantage_on_attacks") or cls._has_effect_kind(target_p, "dodging")
        if not req.has_advantage and cls._has_effect_kind(attacker, "advantage_on_attacks"):
            cls._consume_first_effect(attacker, "advantage_on_attacks")
        adv_mode = "advantage" if (has_adv and not has_dis) else (
            "disadvantage" if (has_dis and not has_adv) else "normal"
        )

        roll_result = resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
            advantage_mode=adv_mode,
            bonus_override=attack_bonus,
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
                    "weapon_name": natural_attack.name,
                    "damage_dice": natural_attack.damage_dice,
                    "damage_bonus": natural_attack.damage_bonus,
                    "attack_bonus": attack_bonus,
                    "damage_type": natural_attack.damage_type,
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
        if was_overridden:
            hit_text = f"[OVERRIDE: Action limit ignored] {hit_text}"

        await cls._emit_log(session_id, {
            "message": (
                f"{attacker['display_name']} ({form.display_name}) {hit_text} "
                f"{target_p['display_name']} (AC {target_ac}) "
                f"with {natural_attack.name} and roll {atk_roll}.{message_suffix}"
            ),
            "actorUserId": actor_user_id,
            "source": source,
            "is_override": was_overridden,
            "overridden_resource": "action" if was_overridden else None,
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
            "weapon_name": natural_attack.name,
            "damage_dice": natural_attack.damage_dice,
            "damage_bonus": natural_attack.damage_bonus,
            "attack_bonus": attack_bonus,
            "damage_type": natural_attack.damage_type,
            "pending_attack_id": pending_attack_id,
            "damage_roll_required": is_hit,
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
        inventory_item = None
        source_item = None
        source_kind = "spellcasting"
        source_item_name = None
        ignore_components = False
        no_free_hand_required = False

        if isinstance(req.inventory_item_id, str) and req.inventory_item_id.strip():
            source_kind = "magic_item"
            inventory_item, source_item, magic_effect = cls._resolve_player_inventory_spell_item(
                db,
                session_id,
                player_user_id=str(attacker.get("actor_user_id") or attacker.get("ref_id") or "").strip(),
                inventory_item_id=req.inventory_item_id.strip(),
            )
            requested_canonical_key = get_magic_item_spell_key(source_item)
            if (
                isinstance(req.spell_canonical_key, str)
                and req.spell_canonical_key.strip()
                and requested_canonical_key
                and req.spell_canonical_key.strip().lower() != requested_canonical_key
            ):
                raise CombatServiceError("Selected spell does not match the magic item.", 400)
            source_item_name = source_item.name
            ignore_components = bool(magic_effect.get("ignoreComponents"))
            no_free_hand_required = bool(magic_effect.get("noFreeHandRequired"))
        else:
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
        spell_name = catalog_spell.name_pt or catalog_spell.name_en or requested_canonical_key
        if source_kind == "magic_item":
            player_spell = None
            spell_level = cls._safe_int(
                cls._as_dict(source_item.magic_effect_json).get("castLevel"),
                catalog_spell.level,
            )
        else:
            player_spell = cls._resolve_player_spell_entry(
                attacker_data,
                spell_canonical_key=catalog_spell.canonical_key or requested_canonical_key,
                spell_name=spell_name,
            )

            spell_level = cls._safe_int(player_spell.get("level"), catalog_spell.level)
            if spell_level > 0 and player_spell.get("prepared") is False:
                raise CombatServiceError("Spell is not prepared.", 400)

        _, _, _, _, prof_bonus, spell_mod = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        catalog_resolution = getattr(catalog_spell, "resolution_type", None)
        catalog_spell_mode = cls._map_resolution_type_to_spell_mode(catalog_resolution)
        automation_default_mode = cls._spell_default_mode_override(
            catalog_spell.canonical_key or requested_canonical_key
        )
        requires_effect_payload = cls._spell_requires_effect_payload(
            catalog_spell.canonical_key or requested_canonical_key
        )
        catalog_save_ability = cls._normalize_ability_name(catalog_spell.saving_throw)
        legacy_mode = "heal" if req.is_heal else ("spell_attack" if req.is_attack else None)
        spell_mode = req.spell_mode or automation_default_mode or catalog_spell_mode or legacy_mode or (
            "saving_throw" if catalog_save_ability else None
        )
        if spell_mode not in ("spell_attack", "saving_throw", "direct_damage", "heal", "utility"):
            raise CombatServiceError("Spell cast mode is required for this spell.", 400)
        if spell_mode == "direct_damage" and catalog_save_ability:
            raise CombatServiceError(
                "This spell is structured as a saving throw spell. "
                "direct_damage is only allowed as an explicit fallback for spells without attack/save automation.",
                400,
            )

        slot_level = None
        if spell_level > 0:
            if source_kind == "magic_item":
                slot_level = spell_level
            else:
                slot_level = req.slot_level or spell_level
                if slot_level < spell_level:
                    raise CombatServiceError("Spell slot level cannot be lower than the spell level.", 400)
        action_cost = cls._resolve_spell_action_cost(
            getattr(catalog_spell, "casting_time_type", None)
        )

        legacy_expression = (
            req.dice_expression.strip()
            if isinstance(req.dice_expression, str) and req.dice_expression.strip()
            else None
        )

        effect_kind = None if spell_mode == "utility" else ("healing" if spell_mode == "heal" else "damage")
        effect_dice = None
        effect_bonus = 0
        damage_type = None
        save_ability = None
        save_dc = None
        save_success_outcome = None
        attack_bonus = None

        if spell_mode == "heal":
            effect_dice = catalog_spell.heal_dice
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.heal_dice or (legacy_expression if req.is_heal else None)
            # heal_bonus is derived from the caster, not the spell catalog
            effect_bonus = req.heal_bonus if isinstance(req.heal_bonus, int) else 0
        elif spell_mode != "utility":
            effect_dice = catalog_spell.damage_dice
            if not isinstance(effect_dice, str) or not effect_dice.strip():
                effect_dice = req.damage_dice or (legacy_expression if not req.is_heal else None)
            # damage_bonus is derived from the caster, not the spell catalog
            effect_bonus = req.damage_bonus if isinstance(req.damage_bonus, int) else 0
            should_require_damage_type = bool(
                requires_effect_payload or effect_dice or effect_bonus > 0
            )
            damage_type = cls._normalize_damage_type(
                catalog_spell.damage_type or req.damage_type
            )
            if should_require_damage_type and not damage_type:
                raise CombatServiceError("Spell damage type is missing a structured value.", 400)

        if isinstance(effect_dice, str):
            effect_dice = effect_dice.strip() or None
        if effect_dice:
            count, sides, _ = _parse_dice(effect_dice)
            if count <= 0 or sides <= 0:
                raise CombatServiceError("Spell effect dice must use a valid dice expression.", 400)
        elif spell_mode != "utility" and requires_effect_payload and effect_bonus <= 0:
            raise CombatServiceError("Spell effect is missing structured dice or a fixed bonus.", 400)

        if spell_mode == "spell_attack":
            # spell_attack_bonus is derived from the caster (spell_mod + prof_bonus),
            # not from the spell catalog; the request can override it explicitly.
            attack_bonus = req.spell_attack_bonus if isinstance(req.spell_attack_bonus, int) else None
            if not isinstance(attack_bonus, int):
                attack_bonus = spell_mod + prof_bonus
        elif spell_mode == "saving_throw":
            save_ability = cls._normalize_ability_name(req.save_ability or catalog_save_ability)
            # save_dc is derived from the caster (8 + prof + spell_mod),
            # not from the spell catalog; the request can override it explicitly.
            save_dc = req.save_dc if isinstance(req.save_dc, int) else None
            if not isinstance(save_dc, int):
                save_dc = 8 + prof_bonus + spell_mod
            save_success_outcome = (
                cls._normalize_save_success_outcome(catalog_spell.save_success_outcome)
                or "none"
            )
            if not save_ability or save_dc <= 0:
                raise CombatServiceError("Saving throw spells require save ability and save DC.", 400)

        structured_upcast = cls._get_structured_spell_upcast(
            getattr(catalog_spell, "upcast_json", None)
        )
        upcast_result = cls._apply_structured_spell_upcast(
            spell_level=spell_level,
            slot_level=slot_level,
            effect_kind=effect_kind,
            effect_dice=effect_dice,
            effect_bonus=effect_bonus,
            upcast=structured_upcast,
        )
        effect_dice = upcast_result["effect_dice"] if isinstance(upcast_result.get("effect_dice"), str) or upcast_result.get("effect_dice") is None else effect_dice
        effect_bonus = cls._safe_int(upcast_result.get("effect_bonus"), effect_bonus)
        elemental_affinity = resolve_elemental_affinity(
            attacker_data,
            damage_type,
        )

        return {
            "spell_name": spell_name,
            "spell_canonical_key": catalog_spell.canonical_key or requested_canonical_key,
            "spell_mode": spell_mode,
            "effect_kind": effect_kind,
            "effect_dice": effect_dice,
            "effect_bonus": effect_bonus,
            "damage_type": damage_type,
            "save_ability": save_ability,
            "save_dc": save_dc,
            "save_success_outcome": save_success_outcome,
            "attack_bonus": attack_bonus,
            "slot_level": slot_level,
            "action_cost": action_cost,
            "upcast": structured_upcast,
            "upcast_applied": bool(upcast_result.get("upcast_applied")),
            "upcast_levels": cls._safe_int(upcast_result.get("upcast_levels"), 0),
            "elemental_affinity_eligible": bool(elemental_affinity.get("eligible")),
            "elemental_affinity_damage_type": elemental_affinity.get("damageType"),
            "elemental_affinity_bonus": elemental_affinity.get("bonus"),
            "source_kind": source_kind,
            "source_item_name": source_item_name,
            "inventory_item": inventory_item,
            "inventory_item_id": getattr(inventory_item, "id", None),
            "ignore_components": ignore_components,
            "no_free_hand_required": no_free_hand_required,
            "source_item": source_item,
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
        damage_type: str | None = None,
        is_critical: bool = False,
        concentration_roll_source: str = "system",
        concentration_manual_roll: int | None = None,
    ) -> tuple[int | None, str, int | None, dict | None]:
        if amount <= 0:
            return None, "", None, None
        if effect_kind == "healing":
            new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(
                db,
                target_ref_id,
                target_kind,
                amount,
                state,
            )
            return new_hp, effect_msg, previous_hp, None
        return cls._apply_damage_to_target(
            db,
            target_ref_id,
            target_kind,
            amount,
            damage_type=damage_type,
            is_crit=is_critical,
            state=state,
            **cls._build_concentration_roll_kwargs(
                concentration_roll_source,
                concentration_manual_roll,
            ),
        )

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

        # Wild Shape blocks spellcasting (PHB: beast form cannot cast spells)
        attacker_state_check, *_ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        attacker_data_check = cls._as_dict(attacker_state_check.state_json)
        ws_check = cls._as_dict(attacker_data_check.get("wildShape"))
        if ws_check.get("active"):
            raise CombatServiceError("Cannot cast spells while in Wild Shape.", 400)

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
        is_hostile_spell = spell_context["spell_mode"] in (
            "spell_attack",
            "saving_throw",
            "direct_damage",
        ) or spell_context["spell_canonical_key"] == "hunters_mark"
        if is_hostile_spell:
            cls._assert_hostile_action_allowed(
                attacker,
                target_p,
                action_label="a hostile spell",
            )
        cls._validate_spell_automation_target(
            db,
            session_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            target_participant=target_p,
        )
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(inventory_item, source_item)
            if isinstance(remaining_charges, int) and remaining_charges <= 0:
                raise CombatServiceError("This item has no charges remaining.", 400)
        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )

        slot_spent = False
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            try:
                consume_inventory_item_charge(inventory_item, source_item)
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            db.add(inventory_item)
        elif isinstance(spell_context.get("slot_level"), int):
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
        save_success_outcome = spell_context.get("save_success_outcome")
        rolled_effect_total = None
        summary_text = None
        inventory_refresh_required = spell_context.get("source_kind") == "magic_item"
        custom_log_message = None
        concentration_check = None

        automation_result = await cls._cast_spell_via_automation(
            db,
            session_id,
            attacker=attacker,
            attacker_model=attacker_model,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            req=req,
            state=state,
            spell_context=spell_context,
            target_participant=target_p,
        )
        if automation_result is not None:
            spell_mode = automation_result["action_kind"]
            effect_kind = automation_result["effect_kind"]
            damage = automation_result["damage"]
            healing = automation_result["healing"]
            roll_result = automation_result["roll_result"]
            roll_total = automation_result["roll"]
            target_ac = automation_result["target_ac"]
            is_critical = automation_result["is_critical"]
            is_hit = automation_result["is_hit"]
            is_saved = automation_result["is_saved"]
            new_hp = automation_result["new_hp"]
            pending_spell_id = automation_result["pending_spell_id"]
            effect_roll_required = automation_result["effect_roll_required"]
            summary_text = automation_result.get("summary_text")
            inventory_refresh_required = inventory_refresh_required or bool(
                automation_result.get("inventory_refresh_required")
            )
            custom_log_message = automation_result.get("__log_message")
            automation_player_state_ids = automation_result.get("__player_state_ids_to_emit") or set()
        elif spell_mode == "spell_attack":
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
                        "elemental_affinity_eligible": spell_context.get("elemental_affinity_eligible"),
                        "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
                        "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
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
                new_hp, effect_msg, previous_hp, concentration_check = cls._apply_spell_effect(
                    db,
                    state,
                    target_p["ref_id"],
                    target_p["kind"],
                    effect_kind,
                    amount,
                    damage_type=spell_context.get("damage_type"),
                    is_critical=is_critical,
                    concentration_roll_source=req.concentration_roll_source,
                    concentration_manual_roll=req.concentration_manual_roll,
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
            if effect_roll_required and (not is_saved or save_success_outcome == "half_damage"):
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
                        "elemental_affinity_eligible": spell_context.get("elemental_affinity_eligible"),
                        "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
                        "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
                        "target_ref_id": target_p["ref_id"],
                        "target_kind": target_p["kind"],
                        "target_display_name": target_p["display_name"],
                        "save_ability": spell_context.get("save_ability"),
                        "save_dc": spell_context.get("save_dc"),
                        "save_success_outcome": save_success_outcome,
                        "is_saved": is_saved,
                        "is_critical": False,
                        "roll": roll_total,
                        "roll_result": roll_result.model_dump(mode="json"),
                    },
                )
            elif not is_saved or save_success_outcome == "half_damage":
                rolled_effect_total = max(0, effect_bonus)
                amount = cls._resolve_save_damage_amount(
                    rolled_effect_total,
                    is_saved=is_saved,
                    save_success_outcome=save_success_outcome,
                )
                new_hp, effect_msg, previous_hp, concentration_check = cls._apply_spell_effect(
                    db,
                    state,
                    target_p["ref_id"],
                    target_p["kind"],
                    effect_kind,
                    amount,
                    damage_type=spell_context.get("damage_type"),
                    concentration_roll_source=req.concentration_roll_source,
                    concentration_manual_roll=req.concentration_manual_roll,
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
                        "elemental_affinity_eligible": spell_context.get("elemental_affinity_eligible"),
                        "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
                        "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
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
                new_hp, effect_msg, previous_hp, concentration_check = cls._apply_spell_effect(
                    db,
                    state,
                    target_p["ref_id"],
                    target_p["kind"],
                    effect_kind,
                    amount,
                    damage_type=spell_context.get("damage_type"),
                    concentration_roll_source=req.concentration_roll_source,
                    concentration_manual_roll=req.concentration_manual_roll,
                )
                if effect_kind == "healing":
                    healing = amount
                else:
                    damage = amount

        db.add(state)
        db.commit()
        db.refresh(state)

        player_state_ids_to_emit = set(automation_player_state_ids) if automation_result is not None else set()
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
                if is_saved and save_success_outcome == "half_damage":
                    log_message += " Dano pendente para aplicar metade."
                else:
                    log_message += " Efeito pendente."
            elif effect_kind == "damage":
                if is_saved and save_success_outcome == "half_damage":
                    log_message += (
                        f" Dano rolado {rolled_effect_total or 0}; dano aplicado {damage} de "
                        f"{spell_context.get('damage_type') or 'energia'}{effect_msg}"
                    )
                elif damage > 0:
                    log_message += f" {damage} de dano de {spell_context.get('damage_type') or 'energia'}{effect_msg}"
                else:
                    log_message += " Nenhum dano aplicado."
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

        if isinstance(custom_log_message, str) and custom_log_message.strip():
            log_message = custom_log_message.strip()
        if isinstance(concentration_check, dict) and isinstance(concentration_check.get("summary_text"), str):
            log_message = f"{log_message} {concentration_check['summary_text']}".strip()

        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"

        await cls._emit_log(session_id, {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": source,
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })
        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_mode,
            "effect_kind": effect_kind,
            "damage": damage,
            "healing": healing,
            "damage_type": (
                automation_result.get("damage_type")
                if automation_result is not None
                else spell_context.get("damage_type")
            ),
            "is_critical": is_critical,
            "is_hit": is_hit,
            "is_saved": is_saved,
            "new_hp": new_hp,
            "roll": roll_total,
            "roll_result": roll_result,
            "target_ac": target_ac,
            "target_display_name": (
                automation_result.get("target_display_name")
                if automation_result is not None
                else target_p["display_name"]
            ),
            "target_kind": (
                automation_result.get("target_kind")
                if automation_result is not None
                else target_p["kind"]
            ),
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": save_success_outcome,
            "effect_dice": (
                automation_result.get("effect_dice")
                if automation_result is not None
                else spell_context.get("effect_dice")
            ),
            "effect_bonus": (
                automation_result.get("effect_bonus")
                if automation_result is not None
                else effect_bonus
            ),
            "pending_spell_id": pending_spell_id,
            "effect_roll_required": bool(pending_spell_id),
            "base_effect": (
                automation_result.get("base_effect")
                if automation_result is not None
                else (None if spell_context.get("effect_dice") else 0)
            ),
            "action_cost": action_cost,
            "summary_text": summary_text,
            "inventory_refresh_required": inventory_refresh_required,
            "concentration_check": concentration_check,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
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

        # Wild Shape blocks all spell-related actions
        _ws_model, *_ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        _ws_data = cls._as_dict(_ws_model.state_json)
        if cls._as_dict(_ws_data.get("wildShape")).get("active"):
            raise CombatServiceError("Cannot resolve spell effects while in Wild Shape.", 400)

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
        rolled_effect_total = max(0, base_effect + effect_bonus)
        is_saved = bool(pending_spell.get("is_saved"))
        save_success_outcome = cls._normalize_save_success_outcome(
            pending_spell.get("save_success_outcome")
        )
        amount = (
            cls._resolve_save_damage_amount(
                rolled_effect_total,
                is_saved=is_saved,
                save_success_outcome=save_success_outcome,
            )
            if pending_spell.get("action_kind") == "saving_throw" and effect_kind == "damage"
            else rolled_effect_total
        )
        new_hp = None
        effect_msg = ""
        previous_hp = None
        concentration_check = None
        if amount > 0:
            new_hp, effect_msg, previous_hp, concentration_check = cls._apply_spell_effect(
                db,
                state,
                target_ref_id,
                target_kind,
                effect_kind,
                amount,
                damage_type=pending_spell.get("damage_type"),
                is_critical=bool(pending_spell.get("is_critical")),
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
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

        if pending_spell.get("action_kind") == "saving_throw" and effect_kind == "damage":
            save_text = "passou" if is_saved else "falhou"
            if is_saved and save_success_outcome == "half_damage":
                log_text = (
                    f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                    f"{target_display_name}: alvo {save_text} no save de {pending_spell.get('save_ability')} "
                    f"contra CD {pending_spell.get('save_dc')}. Dano rolado {rolled_effect_total}; "
                    f"dano aplicado {amount} de {pending_spell.get('damage_type') or 'energia'}{effect_msg}"
                )
            elif is_saved:
                log_text = (
                    f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                    f"{target_display_name}: alvo {save_text} no save de {pending_spell.get('save_ability')} "
                    f"contra CD {pending_spell.get('save_dc')} e evitou o dano."
                )
            else:
                log_text = (
                    f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                    f"{target_display_name}: alvo {save_text} no save de {pending_spell.get('save_ability')} "
                    f"contra CD {pending_spell.get('save_dc')} e sofreu {amount} de "
                    f"{pending_spell.get('damage_type') or 'energia'}{effect_msg}"
                )
        else:
            amount_label = (
                "HP restaurados"
                if effect_kind == "healing"
                else f"de dano de {pending_spell.get('damage_type') or 'energia'}"
            )
            log_text = (
                f"{attacker['display_name']} resolveu {pending_spell.get('spell_name') or 'magia'} em "
                f"{target_display_name}: {amount} {amount_label}{effect_msg}"
            )
        await cls._emit_log(session_id, {
            "message": (
                f"{log_text} {concentration_check['summary_text']}".strip()
                if isinstance(concentration_check, dict)
                and isinstance(concentration_check.get("summary_text"), str)
                else log_text
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
            "is_saved": is_saved if pending_spell.get("action_kind") == "saving_throw" else None,
            "new_hp": new_hp,
            "roll": cls._safe_int(pending_spell.get("roll"), 0) if pending_spell.get("roll") is not None else None,
            "roll_result": roll_result,
            "target_ac": cls._safe_optional_int(pending_spell.get("target_ac")),
            "target_display_name": target_display_name,
            "target_kind": target_kind,
            "save_ability": pending_spell.get("save_ability"),
            "save_dc": cls._safe_optional_int(pending_spell.get("save_dc")),
            "save_success_outcome": save_success_outcome,
            "effect_dice": effect_dice,
            "effect_bonus": effect_bonus,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "effect_rolls": effect_rolls,
            "base_effect": base_effect,
            "effect_roll_source": req.roll_source,
            "concentration_check": concentration_check,
            "elemental_affinity_eligible": bool(pending_spell.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": pending_spell.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": pending_spell.get("elemental_affinity_bonus"),
        }
