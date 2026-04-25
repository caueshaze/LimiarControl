from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.models.combat import CombatState


def _safe_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _metadata_for_spell(spell_context: dict[str, Any]) -> dict[str, Any]:
    canonical_key = spell_context.get("spell_canonical_key")
    if canonical_key == "fog_cloud":
        return {
            "effect_kind": "obscurement",
            "obscurement": "heavily_obscured",
        }
    if canonical_key == "spike_growth":
        return {
            "effect_kind": "hazard",
            "terrain_effect": "difficult_terrain",
            "movement_damage_dice": "2d4",
            "damage_type": "Piercing",
            "damage_per_meters": 1.5,
        }
    return {"effect_kind": "spell_area"}


def build_persistent_spell_area_effect(
    *,
    state: CombatState,
    attacker: dict[str, Any],
    spell_context: dict[str, Any],
    area_spec: dict[str, Any],
    targeting_result: Any,
    origin_cell: dict[str, int] | None,
    anchor_cell: dict[str, int] | None,
    concentration_group: str | None = None,
) -> dict[str, Any]:
    shape = str(area_spec["shape"])
    size_meters = _safe_float(area_spec.get("size_meters")) or 0.0
    origin = (
        anchor_cell
        if spell_context.get("origin_type") == "selected_point"
        else origin_cell
    ) or anchor_cell
    anchor = anchor_cell or origin_cell
    if origin is None or anchor is None:
        raise ValueError("Persistent area effects require origin and anchor cells.")

    effect: dict[str, Any] = {
        "id": f"area_effect:{uuid4()}",
        "source_spell_canonical_key": spell_context.get("spell_canonical_key"),
        "source_spell_name": spell_context.get("spell_name") or "Spell area",
        "caster_participant_id": attacker["id"],
        "caster_ref_id": attacker.get("ref_id"),
        "caster_character_id": attacker.get("actor_user_id") or attacker.get("ref_id"),
        "origin_point": {"x": int(origin["x"]), "y": int(origin["y"])},
        "anchor_cell": {"x": int(anchor["x"]), "y": int(anchor["y"])},
        "area_shape": shape,
        "size_meters": size_meters,
        "radius_meters": _safe_float(spell_context.get("radius_meters")),
        "length_meters": _safe_float(spell_context.get("length_meters")),
        "side_meters": _safe_float(spell_context.get("side_meters")),
        "affected_cells": list(targeting_result.spatial_metadata.affected_cells),
        "duration": spell_context.get("duration"),
        "concentration_owner_participant_id": attacker["id"]
        if spell_context.get("concentration")
        else None,
        "concentration_owner_ref_id": attacker.get("ref_id")
        if spell_context.get("concentration")
        else None,
        "created_round": state.round,
        "created_turn_index": state.current_turn_index,
        "concentration_group": concentration_group,
    }
    effect.update(_metadata_for_spell(spell_context))
    return effect


def active_area_effects_for_map(state: CombatState) -> list[dict[str, Any]]:
    effects = state.active_area_effects if isinstance(state.active_area_effects, list) else []
    return [
        {
            "id": effect["id"],
            "sourceSpellCanonicalKey": effect.get("source_spell_canonical_key"),
            "sourceSpellName": effect.get("source_spell_name") or "Spell area",
            "casterParticipantId": effect.get("caster_participant_id"),
            "casterRefId": effect.get("caster_ref_id"),
            "casterCharacterId": effect.get("caster_character_id"),
            "originPoint": effect.get("origin_point"),
            "anchorCell": effect.get("anchor_cell"),
            "areaShape": effect.get("area_shape"),
            "sizeMeters": effect.get("size_meters"),
            "radiusMeters": effect.get("radius_meters"),
            "lengthMeters": effect.get("length_meters"),
            "sideMeters": effect.get("side_meters"),
            "affectedCells": effect.get("affected_cells") or [],
            "effectKind": effect.get("effect_kind") or "spell_area",
            "duration": effect.get("duration"),
            "concentrationOwnerParticipantId": effect.get("concentration_owner_participant_id"),
            "concentrationOwnerRefId": effect.get("concentration_owner_ref_id"),
            "createdRound": effect.get("created_round"),
            "createdTurnIndex": effect.get("created_turn_index"),
            "obscurement": effect.get("obscurement"),
            "terrainEffect": effect.get("terrain_effect"),
            "movementDamageDice": effect.get("movement_damage_dice"),
            "damageType": effect.get("damage_type"),
            "damagePerMeters": effect.get("damage_per_meters"),
        }
        for effect in effects
        if isinstance(effect, dict) and isinstance(effect.get("id"), str)
    ]
