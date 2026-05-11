from __future__ import annotations

from typing import Any

from .limiar_map_client_types import (
    LimiarMapClientError,
    LimiarMapObstacleCell,
    LimiarMapObstacleState,
    LimiarMapStateResponse,
    LimiarMapTokenState,
)


def _parse_token_entry(token_payload: dict[str, Any]) -> LimiarMapTokenState:
    token_id = token_payload.get("id")
    controller_type = token_payload.get("controllerType")
    controller_id = token_payload.get("controllerId")
    token_kind = token_payload.get("kind")
    movement_speed_cells = token_payload.get("movementSpeedCells")
    movement_budget = token_payload.get("movementBudget")
    combatant_id = token_payload.get("combatantId")
    position_payload = token_payload.get("position")
    label = token_payload.get("label")
    base_size = token_payload.get("base_size")
    effective_size = token_payload.get("effective_size")
    effective_footprint = token_payload.get("effective_footprint")

    if not isinstance(token_id, str) or not token_id.strip():
        raise LimiarMapClientError(
            "LimiarMap token entry is missing id",
            kind="payload",
        )
    if not isinstance(controller_type, str) or not controller_type.strip():
        raise LimiarMapClientError(
            "LimiarMap token entry is missing controllerType",
            kind="payload",
        )
    if token_kind is not None and not isinstance(token_kind, str):
        raise LimiarMapClientError(
            "LimiarMap token entry has an invalid kind",
            kind="payload",
        )
    if not isinstance(controller_id, str) or not controller_id.strip():
        raise LimiarMapClientError(
            "LimiarMap token entry is missing controllerId",
            kind="payload",
        )
    if not isinstance(movement_speed_cells, int):
        raise LimiarMapClientError(
            "LimiarMap token entry is missing movementSpeedCells",
            kind="payload",
        )
    if not isinstance(movement_budget, int):
        raise LimiarMapClientError(
            "LimiarMap token entry is missing movementBudget",
            kind="payload",
        )
    if combatant_id is not None and not isinstance(combatant_id, str):
        raise LimiarMapClientError(
            "LimiarMap token entry has an invalid combatantId",
            kind="payload",
        )
    if label is not None and not isinstance(label, str):
        raise LimiarMapClientError(
            "LimiarMap token entry has an invalid label",
            kind="payload",
        )
    if base_size is not None and not isinstance(base_size, str):
        raise LimiarMapClientError(
            "LimiarMap token entry has an invalid base_size",
            kind="payload",
        )
    if effective_size is not None and not isinstance(effective_size, str):
        raise LimiarMapClientError(
            "LimiarMap token entry has an invalid effective_size",
            kind="payload",
        )
    parsed_effective_footprint: dict[str, int] | None = None
    if effective_footprint is not None:
        if not isinstance(effective_footprint, dict):
            raise LimiarMapClientError(
                "LimiarMap token entry has an invalid effective_footprint",
                kind="payload",
            )
        width = effective_footprint.get("width")
        height = effective_footprint.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            raise LimiarMapClientError(
                "LimiarMap token entry has an invalid effective_footprint",
                kind="payload",
            )
        parsed_effective_footprint = {"width": width, "height": height}
    position_x: int | None = None
    position_y: int | None = None
    if position_payload is not None:
        if not isinstance(position_payload, dict):
            raise LimiarMapClientError(
                "LimiarMap token entry has an invalid position",
                kind="payload",
            )
        raw_x = position_payload.get("x")
        raw_y = position_payload.get("y")
        if not isinstance(raw_x, int) or not isinstance(raw_y, int):
            raise LimiarMapClientError(
                "LimiarMap token entry has an invalid position",
                kind="payload",
            )
        position_x = raw_x
        position_y = raw_y

    return LimiarMapTokenState(
        token_id=token_id,
        kind=token_kind,
        controller_type=controller_type,
        controller_id=controller_id,
        movement_speed_cells=movement_speed_cells,
        combatant_id=combatant_id,
        movement_budget=movement_budget,
        label=label,
        position_x=position_x,
        position_y=position_y,
        base_size=base_size,
        effective_size=effective_size,
        effective_footprint=parsed_effective_footprint,
    )


def _parse_combat_state_fields(
    combat_state_payload: dict[str, Any],
) -> tuple[str | None, int | None, int | None, tuple[str, ...]]:
    raw_active_combatant_id = combat_state_payload.get("activeCombatantId")
    raw_round_number = combat_state_payload.get("roundNumber")
    raw_turn_index = combat_state_payload.get("turnIndex")
    raw_initiative_order = combat_state_payload.get("initiativeOrder")
    if raw_active_combatant_id is not None and not isinstance(
        raw_active_combatant_id, str
    ):
        raise LimiarMapClientError(
            "LimiarMap state response has an invalid activeCombatantId",
            kind="payload",
        )
    if raw_round_number is not None and not isinstance(raw_round_number, int):
        raise LimiarMapClientError(
            "LimiarMap state response has an invalid roundNumber",
            kind="payload",
        )
    if raw_turn_index is not None and not isinstance(raw_turn_index, int):
        raise LimiarMapClientError(
            "LimiarMap state response has an invalid turnIndex",
            kind="payload",
        )
    if raw_initiative_order is not None and not isinstance(raw_initiative_order, list):
        raise LimiarMapClientError(
            "LimiarMap state response has an invalid initiativeOrder",
            kind="payload",
        )
    initiative_order: tuple[str, ...] = ()
    if isinstance(raw_initiative_order, list):
        normalized_initiative_order: list[str] = []
        for combatant_id in raw_initiative_order:
            if not isinstance(combatant_id, str) or not combatant_id.strip():
                raise LimiarMapClientError(
                    "LimiarMap state response has an invalid initiativeOrder entry",
                    kind="payload",
                )
            normalized_initiative_order.append(combatant_id)
        initiative_order = tuple(normalized_initiative_order)
    return (
        raw_active_combatant_id,
        raw_round_number,
        raw_turn_index,
        initiative_order,
    )


def _parse_battle_map_dimensions(
    battle_map_payload: dict[str, Any] | None,
) -> tuple[int | None, int | None]:
    if not isinstance(battle_map_payload, dict):
        return (None, None)
    raw_grid_width = battle_map_payload.get("gridWidth")
    raw_grid_height = battle_map_payload.get("gridHeight")
    if raw_grid_width is not None and not isinstance(raw_grid_width, int):
        raise LimiarMapClientError(
            "LimiarMap battleMap has an invalid gridWidth",
            kind="payload",
        )
    if raw_grid_height is not None and not isinstance(raw_grid_height, int):
        raise LimiarMapClientError(
            "LimiarMap battleMap has an invalid gridHeight",
            kind="payload",
        )
    return (raw_grid_width, raw_grid_height)


def _parse_obstacle_entry(
    obstacle_payload: dict[str, Any],
) -> LimiarMapObstacleState:
    raw_cells = obstacle_payload.get("cells")
    if not isinstance(raw_cells, list):
        raise LimiarMapClientError(
            "LimiarMap obstacle is missing cells",
            kind="payload",
        )

    cells: list[LimiarMapObstacleCell] = []
    for raw_cell in raw_cells:
        if not isinstance(raw_cell, dict):
            raise LimiarMapClientError(
                "LimiarMap obstacle cell is invalid",
                kind="payload",
            )
        x = raw_cell.get("x")
        y = raw_cell.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            raise LimiarMapClientError(
                "LimiarMap obstacle cell has invalid coordinates",
                kind="payload",
            )
        cells.append(LimiarMapObstacleCell(x=x, y=y))

    blocks_movement = obstacle_payload.get("blocksMovement", False)
    blocks_vision = obstacle_payload.get("blocksVision", False)
    # Authoritative field is `blocksEffect` (Phase 2 naming).
    # The `blocksTargeting` / `blocksSpell` fallback is retained only for
    # payloads persisted before the rename; new map-server writes always
    # emit `blocksEffect` exclusively.
    blocks_effect = obstacle_payload.get(
        "blocksEffect",
        obstacle_payload.get("blocksTargeting", obstacle_payload.get("blocksSpell", False)),
    )
    cover = obstacle_payload.get("cover")
    if not isinstance(blocks_movement, bool):
        raise LimiarMapClientError(
            "LimiarMap obstacle has an invalid blocksMovement",
            kind="payload",
        )
    if not isinstance(blocks_vision, bool):
        raise LimiarMapClientError(
            "LimiarMap obstacle has an invalid blocksVision",
            kind="payload",
        )
    if not isinstance(blocks_effect, bool):
        raise LimiarMapClientError(
            "LimiarMap obstacle has an invalid blocksEffect",
            kind="payload",
        )
    if cover is not None and not isinstance(cover, str):
        raise LimiarMapClientError(
            "LimiarMap obstacle has an invalid cover",
            kind="payload",
        )
    return LimiarMapObstacleState(
        cells=tuple(cells),
        blocks_movement=blocks_movement,
        blocks_vision=blocks_vision,
        blocks_effect=blocks_effect,
        cover=cover,
    )


def parse_state_response(payload: dict[str, Any]) -> LimiarMapStateResponse:
    session_id = payload.get("sessionId")
    version = payload.get("version")
    tokens_payload = payload.get("tokens")
    combat_state_payload = payload.get("combatState")
    battle_map_payload = payload.get("battleMap")
    obstacles_payload = payload.get("obstacles")
    active_area_effects_payload = payload.get("activeAreaEffects")
    spell_anchors_payload = payload.get("spellAnchors")

    if not isinstance(session_id, str) or not session_id.strip():
        raise LimiarMapClientError(
            "LimiarMap state response is missing sessionId",
            kind="payload",
        )
    if not isinstance(version, int):
        raise LimiarMapClientError(
            "LimiarMap state response is missing version",
            kind="payload",
        )
    if not isinstance(tokens_payload, list):
        raise LimiarMapClientError(
            "LimiarMap state response is missing tokens",
            kind="payload",
        )
    if battle_map_payload is not None and not isinstance(battle_map_payload, dict):
        raise LimiarMapClientError(
            "LimiarMap state response has an invalid battleMap",
            kind="payload",
        )
    if obstacles_payload is not None and not isinstance(obstacles_payload, list):
        raise LimiarMapClientError(
            "LimiarMap state response has invalid obstacles",
            kind="payload",
        )
    if active_area_effects_payload is not None and not isinstance(active_area_effects_payload, list):
        raise LimiarMapClientError(
            "LimiarMap state response has invalid activeAreaEffects",
            kind="payload",
        )
    if spell_anchors_payload is not None and not isinstance(spell_anchors_payload, list):
        raise LimiarMapClientError(
            "LimiarMap state response has invalid spellAnchors",
            kind="payload",
        )

    active_combatant_id: str | None = None
    round_number: int | None = None
    turn_index: int | None = None
    initiative_order: tuple[str, ...] = ()
    if combat_state_payload is not None:
        if not isinstance(combat_state_payload, dict):
            raise LimiarMapClientError(
                "LimiarMap state response has an invalid combatState",
                kind="payload",
            )
        active_combatant_id, round_number, turn_index, initiative_order = (
            _parse_combat_state_fields(combat_state_payload)
        )

    tokens: list[LimiarMapTokenState] = []
    for token_payload in tokens_payload:
        if not isinstance(token_payload, dict):
            raise LimiarMapClientError(
                "LimiarMap state response has an invalid token entry",
                kind="payload",
            )
        tokens.append(_parse_token_entry(token_payload))

    grid_width, grid_height = _parse_battle_map_dimensions(battle_map_payload)

    obstacles: list[LimiarMapObstacleState] = []
    for obstacle_payload in obstacles_payload or []:
        if not isinstance(obstacle_payload, dict):
            raise LimiarMapClientError(
                "LimiarMap obstacle entry is invalid",
                kind="payload",
            )
        obstacles.append(_parse_obstacle_entry(obstacle_payload))

    active_area_effects: list[dict[str, Any]] = []
    for effect_payload in active_area_effects_payload or []:
        if not isinstance(effect_payload, dict):
            raise LimiarMapClientError(
                "LimiarMap active area effect entry is invalid",
                kind="payload",
            )
        active_area_effects.append(effect_payload)

    spell_anchors: list[dict[str, Any]] = []
    for anchor_payload in spell_anchors_payload or []:
        if not isinstance(anchor_payload, dict):
            raise LimiarMapClientError(
                "LimiarMap spell anchor entry is invalid",
                kind="payload",
            )
        spell_anchors.append(anchor_payload)

    return LimiarMapStateResponse(
        session_id=session_id,
        version=version,
        tokens=tuple(tokens),
        grid_width=grid_width,
        grid_height=grid_height,
        obstacles=tuple(obstacles),
        active_area_effects=tuple(active_area_effects),
        spell_anchors=tuple(spell_anchors),
        active_combatant_id=active_combatant_id,
        round_number=round_number,
        turn_index=turn_index,
        initiative_order=initiative_order,
    )
