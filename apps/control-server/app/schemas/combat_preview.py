"""Schemas for the combat preview (dry-run targeting) endpoint.

The preview endpoint lets the frontend visualise tactical information
(reach, target validity, LoS, AoE footprint) without mutating any
combat state.

Single-target flow
------------------
Set ``target_ref_id`` (and optionally ``source_position`` /
``target_position``) to get entity-level diagnostics (target found,
kind valid, LoS, reach).

AoE flow
--------
Set ``aoe_shape`` + ``aoe_size_cells`` (and both position fields) to
get the AoE footprint from LimiarMap's ``/targeting/area/preview``
endpoint — the read-only variant of the same spatial engine used for
the final cast.  The two paths are mutually exclusive per request.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PreviewPosition(BaseModel):
    x: int
    y: int


class CombatPreviewRequest(BaseModel):
    """Dry-run targeting request from the tactical preview layer."""

    source_ref_id: str
    action_type: Literal["move", "attack", "spell"] = "attack"
    target_ref_id: str | None = None
    # Positions come from the frontend (map-web owns spatial state)
    source_position: PreviewPosition | None = None
    target_position: PreviewPosition | None = None
    # Reach hint from frontend (e.g. weapon reach already resolved by UI)
    reach_cells: int = Field(default=1, ge=1, le=60)
    # AoE fields — only meaningful when action_type="spell" and the spell
    # has area targeting.  The frontend resolves size from the spell catalog
    # (meters → cells) before sending, keeping Control out of the conversion.
    aoe_shape: Literal["sphere", "cone", "line", "cube", "square", "cylinder"] | None = None
    aoe_size_cells: int | None = Field(default=None, ge=1, le=60)


class TacticalDiagnosticsPayload(BaseModel):
    """Mirror of TargetingDiagnostics serialised for the preview response.

    Field names are camelCase to match the frontend TacticalDiagnostics interface.
    """

    isValid: bool
    failureReasons: list[str]
    checks: dict[str, bool]
    metadata: dict[str, Any]


class CombatPreviewResponse(BaseModel):
    """Preview response — diagnostics + effective reach + optional AoE footprint.

    ``aoeCells`` is populated when the request included AoE parameters and
    LimiarMap returned a valid footprint.  It uses the same engine as the
    final cast (``/targeting/area`` vs ``/targeting/area/preview``), so the
    cells shown here are guaranteed to match what will actually be affected.
    """

    diagnostics: TacticalDiagnosticsPayload | None = None
    effectiveReachCells: int
    aoeCells: list[PreviewPosition] = Field(default_factory=list)
