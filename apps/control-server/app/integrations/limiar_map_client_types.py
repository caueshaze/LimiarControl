from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LimiarMapTokenState:
    token_id: str
    controller_type: str
    controller_id: str
    movement_speed_cells: int
    combatant_id: str | None
    movement_budget: int = 0
    kind: str | None = None
    label: str | None = None
    position_x: int | None = None
    position_y: int | None = None


@dataclass(frozen=True)
class LimiarMapObstacleCell:
    x: int
    y: int


@dataclass(frozen=True)
class LimiarMapObstacleState:
    cells: tuple[LimiarMapObstacleCell, ...]
    blocks_movement: bool
    blocks_vision: bool
    blocks_effect: bool
    cover: str | None = None


@dataclass(frozen=True)
class LimiarMapStateResponse:
    session_id: str
    version: int
    tokens: tuple[LimiarMapTokenState, ...]
    grid_width: int | None = None
    grid_height: int | None = None
    obstacles: tuple[LimiarMapObstacleState, ...] = ()
    active_area_effects: tuple[dict[str, Any], ...] = ()
    spell_anchors: tuple[dict[str, Any], ...] = ()
    active_combatant_id: str | None = None
    round_number: int | None = None
    turn_index: int | None = None
    initiative_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class LimiarMapTargetingResponse:
    is_valid: bool
    reason: str | None
    session_id: str
    action_id: str
    version: int
    source_token_id: str | None
    target_token_id: str | None
    distance_cells: int | None = None
    cover: str | None = None


@dataclass(frozen=True)
class LimiarMapAreaCell:
    x: int
    y: int


@dataclass(frozen=True)
class LimiarMapAreaTargetingResponse:
    is_valid: bool
    reason: str | None
    session_id: str
    action_id: str
    version: int
    shape: str
    source_token_id: str | None
    affected_cells: tuple[LimiarMapAreaCell, ...]
    affected_token_ids: tuple[str, ...]
    affected_combatant_ids: tuple[str, ...]


@dataclass(frozen=True)
class LimiarMapMovementCell:
    x: int
    y: int


@dataclass(frozen=True)
class LimiarMapMovementResponse:
    is_valid: bool
    reason: str | None
    session_id: str
    action_id: str
    version: int
    token_id: str | None
    combatant_id: str | None
    source_cell: LimiarMapMovementCell | None
    destination_cell: LimiarMapMovementCell
    path: tuple[LimiarMapMovementCell, ...]
    path_cost_units: int
    movement_budget: int
    movement_speed_cells: int
    remaining_budget: int
    source_elevation_meters: float | None = None
    destination_elevation_meters: float | None = None


@dataclass(frozen=True)
class LimiarMapBatchTargetingResult:
    target_combatant_id: str
    cover: str | None


@dataclass(frozen=True)
class LimiarMapBatchTargetingResponse:
    session_id: str
    action_id: str
    version: int
    results: tuple["LimiarMapBatchTargetingResult", ...]


class LimiarMapClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        kind: str,
        status_code: int | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.reason = reason
