from __future__ import annotations

from copy import deepcopy
from math import floor
from typing import Any
from uuid import uuid4

from app.models.combat import CombatState
from .exceptions import CombatServiceError

_TRIGGER_VALUES = {"turn_start", "turn_end"}


def _as_anchor_list(state: CombatState) -> list[dict[str, Any]]:
    anchors = getattr(state, "spell_anchors", None)
    return anchors if isinstance(anchors, list) else []


def list_spell_anchors(state: CombatState) -> list[dict[str, Any]]:
    return [deepcopy(anchor) for anchor in _as_anchor_list(state) if isinstance(anchor, dict)]


def _validate_position(position: dict[str, Any]) -> dict[str, int]:
    x = position.get("x")
    y = position.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        raise CombatServiceError("Spell anchor position must use integer x/y coordinates.", 400)
    return {"x": x, "y": y}


def _normalize_anchor(anchor: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(anchor)
    normalized["id"] = str(normalized.get("id") or f"spell_anchor:{uuid4()}")
    normalized["position"] = _validate_position(
        normalized.get("position") if isinstance(normalized.get("position"), dict) else {}
    )
    normalized["source_spell_key"] = str(normalized.get("source_spell_key") or "").strip()
    if not normalized["source_spell_key"]:
        raise CombatServiceError("Spell anchor source_spell_key is required.", 400)
    owner_participant_id = normalized.get("owner_participant_id")
    if not isinstance(owner_participant_id, str) or not owner_participant_id.strip():
        raise CombatServiceError("Spell anchor owner_participant_id is required.", 400)
    normalized["owner_participant_id"] = owner_participant_id
    created_by_participant_id = normalized.get("created_by_participant_id")
    if not isinstance(created_by_participant_id, str) or not created_by_participant_id.strip():
        raise CombatServiceError("Spell anchor created_by_participant_id is required.", 400)
    normalized["created_by_participant_id"] = created_by_participant_id
    normalized["source_spell_name"] = (
        normalized.get("source_spell_name")
        if isinstance(normalized.get("source_spell_name"), str)
        else None
    )
    duration_type = normalized.get("duration_type")
    if duration_type is not None and duration_type != "rounds":
        raise CombatServiceError("Spell anchor duration_type must be 'rounds' when provided.", 400)
    normalized["duration_type"] = "rounds" if duration_type is None else duration_type
    remaining_rounds = normalized.get("remaining_rounds")
    if remaining_rounds is not None and (not isinstance(remaining_rounds, int) or remaining_rounds < 1):
        raise CombatServiceError("Spell anchor remaining_rounds must be a positive integer.", 400)
    normalized["remaining_rounds"] = remaining_rounds
    expires_on = normalized.get("expires_on")
    if expires_on is not None and expires_on not in _TRIGGER_VALUES:
        raise CombatServiceError("Spell anchor expires_on must be turn_start or turn_end.", 400)
    normalized["expires_on"] = expires_on
    expires_at_participant_id = normalized.get("expires_at_participant_id")
    if expires_at_participant_id is not None and not isinstance(expires_at_participant_id, str):
        raise CombatServiceError("Spell anchor expires_at_participant_id must be a string when provided.", 400)
    normalized["expires_at_participant_id"] = expires_at_participant_id
    render_kind = normalized.get("render_kind")
    normalized["render_kind"] = render_kind if isinstance(render_kind, str) and render_kind.strip() else "generic"
    movement = normalized.get("movement")
    if movement is not None:
        if not isinstance(movement, dict):
            raise CombatServiceError("Spell anchor movement must be an object when provided.", 400)
        max_meters = movement.get("max_meters_per_follow_up")
        if max_meters is not None and not isinstance(max_meters, (int, float)):
            raise CombatServiceError("Spell anchor movement.max_meters_per_follow_up must be numeric.", 400)
        normalized["movement"] = {
            "max_meters_per_follow_up": float(max_meters) if isinstance(max_meters, (int, float)) else None
        }
    else:
        normalized["movement"] = None
    metadata = normalized.get("metadata")
    normalized["metadata"] = metadata if isinstance(metadata, dict) else {}
    return normalized


def _map_dimensions_from_selection(battle_map: dict[str, Any] | None) -> tuple[int, int]:
    if not isinstance(battle_map, dict):
        raise CombatServiceError("Battle map is required to validate spell anchors.", 400)
    grid_width = battle_map.get("gridWidth")
    grid_height = battle_map.get("gridHeight")
    if not isinstance(grid_width, int) or not isinstance(grid_height, int):
        raise CombatServiceError("Battle map grid dimensions are required to validate spell anchors.", 400)
    return grid_width, grid_height


def _blocked_cells_from_selection(battle_map: dict[str, Any] | None) -> set[tuple[int, int]]:
    if not isinstance(battle_map, dict):
        return set()
    blocked: set[tuple[int, int]] = set()
    for cell in battle_map.get("blockedCells") or []:
        if isinstance(cell, dict) and isinstance(cell.get("x"), int) and isinstance(cell.get("y"), int):
            blocked.add((cell["x"], cell["y"]))
    for obstacle in battle_map.get("obstacles") or []:
        if not isinstance(obstacle, dict):
            continue
        blocks_effect = obstacle.get("blocksEffect", obstacle.get("blocksTargeting", obstacle.get("blocksSpell", False)))
        blocks_movement = obstacle.get("blocksMovement", False)
        if blocks_effect is not True and blocks_movement is not True:
            continue
        for cell in obstacle.get("cells") or []:
            if isinstance(cell, dict) and isinstance(cell.get("x"), int) and isinstance(cell.get("y"), int):
                blocked.add((cell["x"], cell["y"]))
    return blocked


def _distance_cells(a: dict[str, int], b: dict[str, int]) -> int:
    return max(abs(a["x"] - b["x"]), abs(a["y"] - b["y"]))


def _meters_to_cells(meters: float) -> int:
    return max(0, floor(meters / 1.5))


def validate_spell_anchor_placement(
    *,
    caster_position: dict[str, int],
    target_position: dict[str, int],
    range_meters: float | None,
    requires_point_sight: bool,
    requires_point_effect: bool,
    battle_map: dict[str, Any],
) -> None:
    position = _validate_position(target_position)
    origin = _validate_position(caster_position)
    grid_width, grid_height = _map_dimensions_from_selection(battle_map)
    if position["x"] < 0 or position["y"] < 0 or position["x"] >= grid_width or position["y"] >= grid_height:
        raise CombatServiceError("Spell anchor position must be within battle map bounds.", 400)
    if range_meters is not None:
        max_cells = _meters_to_cells(range_meters)
        if _distance_cells(origin, position) > max_cells:
            raise CombatServiceError("Spell anchor position is out of range.", 400)
    if requires_point_effect or requires_point_sight:
        blocked = _blocked_cells_from_selection(battle_map)
        if (position["x"], position["y"]) in blocked:
            raise CombatServiceError("Spell anchor position is blocked.", 400)


def get_spell_anchor_by_id(state: CombatState, anchor_id: str) -> dict[str, Any] | None:
    return next((deepcopy(anchor) for anchor in _as_anchor_list(state) if isinstance(anchor, dict) and anchor.get("id") == anchor_id), None)


def get_spell_anchors_for_owner(state: CombatState, owner_participant_id: str) -> list[dict[str, Any]]:
    return [
        deepcopy(anchor)
        for anchor in _as_anchor_list(state)
        if isinstance(anchor, dict) and anchor.get("owner_participant_id") == owner_participant_id
    ]


def create_spell_anchor(state: CombatState, *, anchor: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_anchor(anchor)
    anchors = _as_anchor_list(state)
    anchors.append(normalized)
    state.spell_anchors = anchors
    return deepcopy(normalized)


def remove_spell_anchor(state: CombatState, anchor_id: str) -> dict[str, Any] | None:
    anchors = _as_anchor_list(state)
    kept: list[dict[str, Any]] = []
    removed: dict[str, Any] | None = None
    for anchor in anchors:
        if removed is None and isinstance(anchor, dict) and anchor.get("id") == anchor_id:
            removed = deepcopy(anchor)
            continue
        kept.append(anchor)
    state.spell_anchors = kept
    return removed


def move_spell_anchor(
    state: CombatState,
    *,
    anchor_id: str,
    destination: dict[str, int],
    max_movement_meters: float,
    battle_map: dict[str, Any],
) -> dict[str, Any]:
    next_position = _validate_position(destination)
    anchors = _as_anchor_list(state)
    grid_width, grid_height = _map_dimensions_from_selection(battle_map)
    if next_position["x"] < 0 or next_position["y"] < 0 or next_position["x"] >= grid_width or next_position["y"] >= grid_height:
        raise CombatServiceError("Spell anchor destination must be within battle map bounds.", 400)
    blocked = _blocked_cells_from_selection(battle_map)
    if (next_position["x"], next_position["y"]) in blocked:
        raise CombatServiceError("Spell anchor destination is blocked.", 400)
    max_cells = _meters_to_cells(max_movement_meters)
    for anchor in anchors:
        if not isinstance(anchor, dict) or anchor.get("id") != anchor_id:
            continue
        current_position = _validate_position(anchor.get("position") if isinstance(anchor.get("position"), dict) else {})
        if _distance_cells(current_position, next_position) > max_cells:
            raise CombatServiceError("Spell anchor destination is out of movement range.", 400)
        anchor["position"] = next_position
        state.spell_anchors = anchors
        return deepcopy(anchor)
    raise CombatServiceError("Spell anchor not found.", 404)


def tick_spell_anchors_for_turn(
    state: CombatState,
    *,
    participant_id: str,
    trigger: str,
) -> list[dict[str, Any]]:
    anchors = _as_anchor_list(state)
    kept: list[dict[str, Any]] = []
    expired: list[dict[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, dict):
            continue
        if anchor.get("expires_on") == trigger and anchor.get("expires_at_participant_id") == participant_id:
            remaining = anchor.get("remaining_rounds")
            if anchor.get("duration_type") == "rounds" and isinstance(remaining, int) and remaining > 1:
                anchor["remaining_rounds"] = remaining - 1
                kept.append(anchor)
                continue
            expired.append(deepcopy(anchor))
            continue
        kept.append(anchor)
    state.spell_anchors = kept
    return expired


def spell_anchors_for_map(state: CombatState) -> list[dict[str, Any]]:
    anchors = _as_anchor_list(state)
    payload: list[dict[str, Any]] = []
    for anchor in anchors:
        if not isinstance(anchor, dict) or not isinstance(anchor.get("id"), str):
            continue
        payload.append(
            {
                "id": anchor["id"],
                "sourceSpellKey": anchor.get("source_spell_key"),
                "sourceSpellName": anchor.get("source_spell_name"),
                "ownerParticipantId": anchor.get("owner_participant_id"),
                "createdByParticipantId": anchor.get("created_by_participant_id"),
                "position": anchor.get("position"),
                "durationType": anchor.get("duration_type"),
                "remainingRounds": anchor.get("remaining_rounds"),
                "expiresOn": anchor.get("expires_on"),
                "expiresAtParticipantId": anchor.get("expires_at_participant_id"),
                "renderKind": anchor.get("render_kind") or "generic",
                "movement": anchor.get("movement"),
                "metadata": anchor.get("metadata") or {},
            }
        )
    return payload
