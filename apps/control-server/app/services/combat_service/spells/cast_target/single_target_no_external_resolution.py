from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm.attributes import flag_modified

from app.models.inventory import InventoryItem
from app.services.magic_item_effects import consume_inventory_item_charge, get_inventory_item_charges_current

from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol
from ..spell_resolution import SpellResolutionResult


if TYPE_CHECKING:
    _CastTargetSingleTargetNoExternalResolutionBase = CombatServiceHostProtocol
else:
    _CastTargetSingleTargetNoExternalResolutionBase = object


class CastTargetSingleTargetNoExternalResolutionMixin(_CastTargetSingleTargetNoExternalResolutionBase):
    @classmethod
    async def _resolve_no_external_target_cast(
        cls, db, session_id, req, state, attacker, attacker_model,
        spell_context, actor_user_id, is_gm,
    ) -> dict[str, Any]:
        slot_spent = False
        is_shield = cls._normalize_lookup(spell_context.get("spell_canonical_key")) == "shield"
        shield_pending_attacker = None
        shield_pending_payload = None
        if is_shield:
            for participant in state.participants:
                pending = participant.get("pending_attack")
                if not isinstance(pending, dict):
                    continue
                if pending.get("target_ref_id") != attacker.get("ref_id"):
                    continue
                if pending.get("type") != "player_attack":
                    continue
                attack_roll = cls._safe_int(pending.get("roll"), 0)
                target_ac = cls._safe_int(pending.get("target_ac"), 10)
                if attack_roll < target_ac:
                    continue
                shield_pending_attacker = participant
                shield_pending_payload = pending
                break
            if shield_pending_payload is None:
                raise CombatServiceError("Shield requires an incoming hit trigger.", 400)
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(
                inventory_item, source_item
            )
            if isinstance(remaining_charges, int) and remaining_charges <= 0:
                raise CombatServiceError("This item has no charges remaining.", 400)
        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
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
        if is_shield:
            cls._upsert_shield_temp_ac_effect(
                attacker,
                source_participant_id=attacker.get("id"),
            )
            pending_options = shield_pending_payload or {}
            pending_roll = cls._safe_int(pending_options.get("roll"), 0)
            _, recalculated_ac, *_ = cls._get_stats(
                db,
                attacker["ref_id"],
                attacker["kind"],
                session_id,
                combat_state=state,
            )
            recalculated_ac = recalculated_ac or 10
            if pending_roll < recalculated_ac:
                if isinstance(shield_pending_attacker, dict):
                    cls._clear_participant_pending_attack(shield_pending_attacker)
                    flag_modified(state, "participants")

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
            target_participant=attacker,
        )
        if automation_result is None:
            automation_result = await cls._cast_spell_via_declarative_effects(
                db,
                session_id,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=attacker,
            )
        if automation_result is not None:
            result = SpellResolutionResult(
                roll_result=automation_result["roll_result"],
                roll_total=automation_result["roll"],
                target_ac=automation_result["target_ac"],
                is_critical=automation_result["is_critical"],
                is_hit=automation_result["is_hit"],
                is_saved=automation_result["is_saved"],
                new_hp=automation_result["new_hp"],
                pending_spell_id=automation_result["pending_spell_id"],
                damage=automation_result["damage"],
                healing=automation_result["healing"],
            )
            return await cls._commit_cast_result(
                db,
                session_id,
                state,
                attacker,
                spell_context,
                {
                    "result": result,
                    "spell_mode": automation_result["action_kind"],
                    "effect_kind": automation_result["effect_kind"],
                    "effect_bonus": cls._safe_int(
                        automation_result.get("effect_bonus"), 0
                    ),
                    "save_success_outcome": spell_context.get("save_success_outcome"),
                    "slot_spent": slot_spent,
                    "inventory_refresh_required": spell_context.get("source_kind") == "magic_item"
                    or bool(automation_result.get("inventory_refresh_required")),
                    "summary_text": automation_result.get("summary_text"),
                    "custom_log_message": automation_result.get("__log_message"),
                    "automation_player_state_ids": automation_result.get("__player_state_ids_to_emit") or set(),
                    "was_overridden": was_overridden,
                    "action_cost": action_cost,
                    "target_p": attacker,
                    "automation_result": automation_result,
                },
                actor_user_id,
                is_gm,
            )

        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)
        log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']}."
        if spell_context.get("effect_timing") == "triggered":
            log_message = f"{log_message} Efeito preparado para gatilho."
        elif spell_context.get("effect_timing") == "persistent":
            log_message = f"{log_message} Efeito persistente iniciado."
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_context["spell_mode"],
            "effect_kind": spell_context["effect_kind"],
            "damage": 0,
            "healing": 0,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": attacker.get("display_name"),
            "target_kind": attacker.get("kind"),
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
            "pending_spell_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": 0,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
        }

    # ------------------------------------------------------------------
    # Plain multi-target automation cast (no variants, no effect instances)
    # ------------------------------------------------------------------
