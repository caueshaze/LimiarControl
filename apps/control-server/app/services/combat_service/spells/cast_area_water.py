"""Per-spell area-cast handler extracted from cast_area.py (mixin).

Composed into CombatService via CastAreaMixin; methods resolve through the MRO.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session
from app.models.combat import CombatState
from app.schemas.combat import CombatCastSpellRequest
from app.services.create_or_destroy_water import (normalize_water_payload, resolve_cube_side_meters, resolve_water_amount, select_obscurement_effects_in_cells)
from ..exceptions import CombatServiceError
from ..limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map
from ..host_protocol import CombatServiceHostProtocol

if TYPE_CHECKING:
    _AreaMixinBase = CombatServiceHostProtocol
else:
    _AreaMixinBase = object


class CreateOrDestroyWaterAreaMixin(_AreaMixinBase):
    @classmethod
    async def _cast_create_or_destroy_water(
        cls,
        db: Session,
        session_id: str,
        *,
        req: CombatCastSpellRequest,
        attacker: dict,
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
        spell_context: dict[str, Any],
        area_spec: dict[str, int | str],
        targeting_result,
        was_overridden: bool,
    ) -> dict[str, Any]:
        has_anchor = req.anchor_cell is not None or req.origin_cell is not None
        try:
            payload = normalize_water_payload(
                getattr(req, "water_payload", None), has_anchor=has_anchor
            )
        except ValueError as exc:
            raise CombatServiceError(str(exc), 400) from exc

        mode = payload["mode"]
        target_kind = payload["target_kind"]
        slot_level = cls._safe_int(spell_context.get("slot_level"), 1) or 1
        gallons, liters = resolve_water_amount(slot_level)
        cube_side = resolve_cube_side_meters(slot_level)

        environment_effects: dict[str, Any] = {}
        amount = None
        area = None
        removed_fog_effect_ids: list[str] = []

        if target_kind == "container":
            amount = {"gallons": gallons, "liters": liters}
            environment_effects = {
                "create_water": mode == "create",
                "destroy_water": mode == "destroy",
            }
        else:  # area
            area = {"shape": "cube", "side_meters": cube_side}
            if mode == "create":
                environment_effects = {
                    "rain": True,
                    "extinguishes_exposed_flames": True,
                }
            else:  # destroy / area -> destroy fog
                environment_effects = {"destroy_fog": True}
                cells = targeting_result.spatial_metadata.affected_cells
                obscurement_effects = select_obscurement_effects_in_cells(state, cells)
                removed_fog_effect_ids = [
                    e["id"] for e in obscurement_effects if isinstance(e.get("id"), str)
                ]
                groups = {
                    e["concentration_group"]
                    for e in obscurement_effects
                    if e.get("concentration_group")
                }
                ungrouped_ids = {
                    e["id"]
                    for e in obscurement_effects
                    if not e.get("concentration_group") and isinstance(e.get("id"), str)
                }
                for group in groups:
                    cls._remove_effect_group(state, concentration_group=group)
                if ungrouped_ids:
                    state.active_area_effects = [
                        e
                        for e in (state.active_area_effects or [])
                        if e.get("id") not in ungrouped_ids
                    ]
                if removed_fog_effect_ids:
                    flag_modified(state, "participants")
                    flag_modified(state, "active_area_effects")
                    maybe_sync_active_area_effects_to_limiar_map(session_id, state)

        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)

        if target_kind == "container":
            detail = (
                f"criou {liters} L de água limpa"
                if mode == "create"
                else f"destruiu até {liters} L de água"
            )
        elif mode == "create":
            detail = f"fez chover em um cubo de {cube_side} m, apagando chamas expostas"
        else:
            detail = f"dissipou névoa em um cubo de {cube_side} m"
        log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']}: {detail}."
        action_cost = spell_context.get("action_cost") or "action"
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
            "action_kind": "utility",
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
            "target_display_name": "Environment",
            "target_kind": "session_entity",
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "material_consumed": bool(spell_context.get("material_consumed")),
            "material_key": spell_context.get("material_key"),
            "material_label": spell_context.get("material_label"),
            "material_quantity": spell_context.get("material_quantity"),
            "material_inventory_item_id": spell_context.get("material_inventory_item_id"),
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": area_spec["shape"],
            "affected_target_ref_ids": [],
            "affected_cells": list(targeting_result.spatial_metadata.affected_cells),
            "area_target_outcomes": [],
            "target_count": 0,
            "active_area_effect": None,
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "concentration_group": None,
            "mode": mode,
            "target_kind": target_kind,
            "amount": amount,
            "area": area,
            "environment_effects": environment_effects,
            "removed_fog_effect_ids": removed_fog_effect_ids,
        }
