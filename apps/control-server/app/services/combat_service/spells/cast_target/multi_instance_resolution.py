from __future__ import annotations

import logging
from types import SimpleNamespace

from sqlalchemy.orm.attributes import flag_modified

from app.models.inventory import InventoryItem
from app.services.combat_service.sanctuary_guard import break_sanctuary_if_active, resolve_sanctuary_guard
from app.services.magic_item_effects import consume_inventory_item_charge, get_inventory_item_charges_current
from app.services.spell_material_components import SpellMaterialError, consume_spell_material

from ...exceptions import CombatServiceError
from ...targeting_result import TargetingResult

logger = logging.getLogger(__name__)


class CastTargetMultiInstanceResolutionMixin:
    async def _resolve_multi_instance_cast(
        cls, db, session_id, req, state, attacker, attacker_model,
        spell_context, actor_user_id, is_gm, validated_targets,
        *,
        spatial_results_by_target_ref: dict[str, TargetingResult] | None = None,
    ):
        slot_spent = False
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
            attacker, action_cost,
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
        caster_user_id = str(attacker.get("actor_user_id") or attacker.get("ref_id") or "").strip()
        spell_material_config = SimpleNamespace(
            material_component_consumed=bool(spell_context.get("material_component_consumed")),
            consumable_material_options_json=spell_context.get("consumable_material_options_json"),
        )
        try:
            material_result = consume_spell_material(
                db,
                session_id=session_id,
                caster_user_id=caster_user_id,
                spell=spell_material_config,
                consumable_material_key=req.consumable_material_key,
            )
        except SpellMaterialError as exc:
            raise CombatServiceError(exc.detail, exc.status_code) from exc
        spell_context["material_consumed"] = material_result.consumed
        spell_context["material_key"] = material_result.material_key
        spell_context["material_label"] = material_result.material_label
        spell_context["material_quantity"] = (
            material_result.quantity if material_result.required else None
        )
        spell_context["material_inventory_item_id"] = material_result.inventory_item_id

        spell_mode = spell_context["spell_mode"]
        is_hostile = spell_mode in ("spell_attack", "saving_throw", "direct_damage")
        if is_hostile:
            seen = set()
            for vt in validated_targets:
                ref_id = vt["target_ref_id"]
                if ref_id not in seen:
                    cls._assert_hostile_action_allowed(
                        attacker, vt["participant"], action_label="a hostile spell",
                    )
                    seen.add(ref_id)
            # Caster is casting a hostile spell — their own sanctuary ends immediately.
            break_sanctuary_if_active(attacker, state)

        logger.info(
            "[cast_spell] pipeline=multi_instance spell=%s instances=%d session=%s actor=%s",
            spell_context["spell_canonical_key"],
            len(validated_targets),
            session_id,
            attacker.get("ref_id"),
        )

        outcomes = []
        entity_previous_hp_map = {}

        for vt in validated_targets:
            target_p = vt["participant"]

            # For direct single-target hostile spell attacks, check Sanctuary on target.
            if spell_mode == "spell_attack" and cls._is_hostile_team_context(attacker, target_p):
                sanctuary_block = resolve_sanctuary_guard(
                    db=db,
                    session_id=session_id,
                    attacker_participant=attacker,
                    target_participant=target_p,
                )
                if sanctuary_block:
                    outcome = {
                        "is_hit": False,
                        "damage": 0,
                        "is_critical": False,
                        "new_hp": None,
                        "previous_hp": None,
                        "blocked_by": "sanctuary",
                        "retarget_required": True,
                        "save_roll": sanctuary_block["save_roll"],
                        "guard_save_dc": sanctuary_block["guard_save_dc"],
                    }
                    outcome["instance_index"] = vt["instance_index"]
                    outcomes.append(outcome)
                    continue

            if spell_mode == "spell_attack":
                instance_targeting_result = (spatial_results_by_target_ref or {}).get(
                    vt["target_ref_id"]
                )
                outcome = cls._resolve_instance_attack(
                    db, session_id, state, attacker, target_p, spell_context, req, is_gm,
                    targeting_result=instance_targeting_result,
                )
            else:
                outcome = cls._resolve_instance_direct(
                    db, state, attacker, target_p, spell_context, req,
                )
                is_magic_missile = cls._normalize_lookup(spell_context.get("spell_canonical_key")) == "magic missile"
                if is_magic_missile and cls._is_shielded_for_magic_missile(target_p):
                    outcome["damage"] = 0
                    outcome["new_hp"] = None

            outcome["instance_index"] = vt["instance_index"]
            outcomes.append(outcome)

            ref_id = vt["target_ref_id"]
            if ref_id not in entity_previous_hp_map and outcome.get("previous_hp") is not None:
                entity_previous_hp_map[ref_id] = outcome["previous_hp"]

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        player_state_ids = set()
        if slot_spent:
            player_state_ids.add(attacker["ref_id"])

        for outcome in outcomes:
            if outcome["damage"] > 0 or outcome["healing"] > 0:
                if outcome["target_kind"] == "player":
                    player_state_ids.add(outcome["target_ref_id"])

        for player_ref_id in player_state_ids:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, player_ref_id, target_state)

        for ref_id, prev_hp in entity_previous_hp_map.items():
            target_p_entity = next(
                (p for p in state.participants if p["ref_id"] == ref_id), None,
            )
            if target_p_entity and target_p_entity.get("kind") == "session_entity":
                await cls._emit_entity_hp_update(db, session_id, ref_id, prev_hp)

        await cls._emit_state(session_id, state)

        log_message = cls._build_multi_instance_log_message(
            attacker=attacker,
            spell_context=spell_context,
            outcomes=outcomes,
            was_overridden=was_overridden,
            action_cost=action_cost,
        )
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        total_damage = sum(o["damage"] for o in outcomes)
        total_healing = sum(o["healing"] for o in outcomes)
        first_outcome = outcomes[0] if outcomes else None
        per_target_totals: dict[str, dict[str, object]] = {}
        for outcome in outcomes:
            target_ref_id = str(outcome.get("target_ref_id") or "")
            if not target_ref_id:
                continue
            bucket = per_target_totals.setdefault(
                target_ref_id,
                {
                    "target_ref_id": target_ref_id,
                    "target_display_name": outcome.get("target_display_name") or target_ref_id,
                    "target_kind": outcome.get("target_kind") or "session_entity",
                    "instance_count": 0,
                    "damage": 0,
                    "healing": 0,
                },
            )
            bucket["instance_count"] = cls._safe_int(bucket.get("instance_count"), 0) + 1
            bucket["damage"] = cls._safe_int(bucket.get("damage"), 0) + cls._safe_int(outcome.get("damage"), 0)
            bucket["healing"] = cls._safe_int(bucket.get("healing"), 0) + cls._safe_int(outcome.get("healing"), 0)

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_mode,
            "effect_kind": spell_context.get("effect_kind"),
            "damage": total_damage,
            "healing": total_healing,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": None,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": first_outcome["target_display_name"] if first_outcome else "",
            "target_kind": first_outcome["target_kind"] if first_outcome else "session_entity",
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_instance_dice"),
            "effect_bonus": 0,
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "effect_rolls": [],
            "base_effect": None,
            "effect_roll_source": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": len(validated_targets),
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            "effect_instance_count": spell_context.get("effect_instance_count"),
            "effect_instance_dice": spell_context.get("effect_instance_dice"),
            "base_effect_instance_count": spell_context.get("base_effect_instance_count"),
            "effect_instance_outcomes": outcomes,
            "effect_instance_target_totals": list(per_target_totals.values()),
        }

