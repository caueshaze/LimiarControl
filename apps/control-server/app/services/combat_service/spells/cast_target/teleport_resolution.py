from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.spell_material_components import MaterialConsumptionResult, SpellMaterialError, validate_spell_material
from app.integrations import LimiarMapClientError

from ...exceptions import CombatServiceError


class CastTargetTeleportResolutionMixin:
    @classmethod
    async def _resolve_teleport_spell(
        cls, db, session_id, req, state, attacker, attacker_model, spell_context, actor_user_id, is_gm
    ):
        if req.anchor_cell is None:
            raise CombatServiceError("Teleport spells require a destination point.", 400)
        if not state.use_map:
            raise CombatServiceError("Teleport spells require a tactical map.", 400)

        destination_cell = {"x": req.anchor_cell.x, "y": req.anchor_cell.y}
        client = cls._build_limiar_map_client()
        try:
            movement = client.move_combatant(
                session_id=session_id,
                action_id=f"teleport:{uuid4()}",
                combatant_id=attacker["ref_id"],
                destination_cell=destination_cell,
            )
        except LimiarMapClientError as exc:
            raise CombatServiceError(f"Teleport is unavailable: {exc}", 503) from exc

        if not movement.is_valid:
            raise CombatServiceError(movement.reason or "Invalid teleport destination.", 400)

        slot_spent = False
        material_result = MaterialConsumptionResult(
            required=False,
            consumed=False,
            material_key=None,
            material_label=None,
            quantity=0,
            inventory_item_id=None,
        )
        spell_material_config = SimpleNamespace(
            material_component_consumed=bool(spell_context.get("material_component_consumed")),
            consumable_material_options_json=spell_context.get("consumable_material_options_json"),
        )
        caster_user_id = str(attacker.get("actor_user_id") or attacker.get("ref_id") or "").strip()
        try:
            material_result = validate_spell_material(
                db,
                session_id=session_id,
                caster_user_id=caster_user_id,
                spell=spell_material_config,
                consumable_material_key=req.consumable_material_key,
            )
        except SpellMaterialError as exc:
            raise CombatServiceError(exc.detail, exc.status_code) from exc
        action_cost = spell_context.get("action_cost") or "bonus_action"
        was_overridden = cls._consume_turn_resource(
            attacker, action_cost, is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )
        if isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)
        log_message = (
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} e se teleportou para "
            f"({destination_cell['x']}, {destination_cell['y']})."
        )
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_and_persist_log(
            db, session_id, actor_user_id, attacker.get("display_name"),
            {"message": log_message, "actorUserId": actor_user_id, "source": "gm_override" if is_gm else "player_turn"},
        )
        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": "teleport",
            "effect_kind": None,
            "damage": 0,
            "healing": 0,
            "damage_type": None,
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": attacker.get("display_name"),
            "target_kind": attacker.get("kind"),
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": False,
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [attacker["ref_id"]],
            "affected_cells": [destination_cell],
            "area_target_outcomes": [],
            "target_count": 1,
            "destination_cell": destination_cell,
        }
