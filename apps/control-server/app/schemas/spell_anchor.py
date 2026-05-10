from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SpellAnchorPosition(BaseModel):
    x: int
    y: int


class SpellAnchorMovement(BaseModel):
    max_meters_per_follow_up: float | None = None


class SpellAnchorRead(BaseModel):
    id: str
    source_spell_key: str
    source_spell_name: str | None = None
    owner_participant_id: str
    created_by_participant_id: str
    position: SpellAnchorPosition
    duration_type: Literal["rounds"]
    remaining_rounds: int | None = None
    expires_on: Literal["turn_start", "turn_end"] | None = None
    expires_at_participant_id: str | None = None
    render_kind: str = "generic"
    movement: SpellAnchorMovement | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
