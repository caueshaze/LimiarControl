from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

MAX_GRID_DIMENSION = 150

ControllerType = Literal["player", "gm", "limiarControl"]
ActionResult = Literal["pending", "accepted", "rejected"]
CombatStatus = Literal["inactive", "active", "completed"]
TargetingShape = Literal["line", "cone", "sphere", "cube"]
ObstacleCover = Literal["none", "half", "threeQuarters", "full"]
ObstaclePaintMode = Literal["paint", "erase"]


class Coordinate(BaseModel):
    x: int
    y: int

    @field_validator("x", "y")
    @classmethod
    def must_be_nonnegative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("coordinate must be non-negative")
        return v


class GridCalibration(BaseModel):
    x: float
    y: float
    width: float
    height: float

    @model_validator(mode="after")
    def validate_bounds(self) -> GridCalibration:
        if not (0 <= self.x <= 1):
            raise ValueError("x must be between 0 and 1")
        if not (0 <= self.y <= 1):
            raise ValueError("y must be between 0 and 1")
        if not (0 < self.width <= 1):
            raise ValueError("width must be positive and <= 1")
        if not (0 < self.height <= 1):
            raise ValueError("height must be positive and <= 1")
        if self.x + self.width > 1:
            raise ValueError("Grid calibration width exceeds image bounds")
        if self.y + self.height > 1:
            raise ValueError("Grid calibration height exceeds image bounds")
        return self


class GridDimensions(BaseModel):
    grid_width: int
    grid_height: int

    @field_validator("grid_width", "grid_height")
    @classmethod
    def valid_dimension(cls, v: int) -> int:
        if v <= 0 or v > MAX_GRID_DIMENSION:
            raise ValueError(f"dimension must be between 1 and {MAX_GRID_DIMENSION}")
        return v


class BattleMap(BaseModel):
    id: str
    name: str
    grid_width: int
    grid_height: int
    terrain_version: int
    grid_calibration: GridCalibration
    active_encounter_id: Optional[str] = None


class ObstacleStyle(BaseModel):
    blocks_movement: bool
    blocks_targeting: bool
    blocks_spell: bool = False
    blocks_vision: bool = False
    cover: ObstacleCover = "none"
    clips_diagonal_movement: bool = False


class Obstacle(ObstacleStyle):
    id: str
    battle_map_id: str
    cells: list[Coordinate]
    label: Optional[str] = None


class Token(BaseModel):
    id: str
    battle_map_id: str
    label: str
    kind: Literal["playerCharacter", "ally", "enemy", "neutral"]
    controller_type: ControllerType
    controller_id: str
    position: Coordinate
    movement_speed_base: int
    movement_budget: int
    combatant_id: Optional[str] = None


class CombatState(BaseModel):
    id: str
    battle_map_id: str
    status: CombatStatus
    round_number: int
    turn_index: int
    active_combatant_id: Optional[str]
    initiative_order: list[str]
    advanced_by: Literal["LimiarControl"]
    version: int


class SpellAnchorMovement(BaseModel):
    max_meters_per_follow_up: float | None = None


class SpellAnchor(BaseModel):
    id: str
    source_spell_key: str
    source_spell_name: str | None = None
    owner_participant_id: str
    created_by_participant_id: str
    position: Coordinate
    duration_type: Literal["rounds"]
    remaining_rounds: int | None = None
    expires_on: Literal["turn_start", "turn_end"] | None = None
    expires_at_participant_id: str | None = None
    render_kind: str = "generic"
    movement: SpellAnchorMovement | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class MovementAction(BaseModel):
    action_id: str
    token_id: str
    requested_path: list[Coordinate]
    submitted_by: str
    submitted_at_version: int
    result: ActionResult = "pending"
    rejection_reason: Optional[str] = None


class TargetingTemplate(BaseModel):
    action_id: str
    token_id: str
    shape: TargetingShape
    origin_cell: Coordinate
    anchor_cell: Coordinate
    range: int
    size: int
    affected_cells: list[Coordinate] = []
    result: ActionResult = "pending"
    rejection_reason: Optional[str] = None


class RealtimeActionEvent(BaseModel):
    event_id: str
    event_type: str
    encounter_id: str
    version: int
    action_id: Optional[str] = None
    payload: dict
    replay_safe: bool = True
