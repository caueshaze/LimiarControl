"""
Result type returned by CombatTargetingService after spatial validation.

A TargetingResult is the structured output of the pre-resolution spatial
layer. It tells the mechanical resolution layer:
  - whether the action is spatially valid
  - which participant is the validated primary target
  - which participants are affected (always one for single-target, future
    multi-target for area effects)
  - any spatial metadata the LimiarMap may return (distance, geometry, etc.)
  - structured diagnostics explaining every check that was performed

Current state (single-target, no map integration):
  - is_valid is True whenever the requested target exists in combat
  - affected_target_ref_ids always contains exactly one entry
  - spatial_metadata is empty but typed for future extension

Future integration with LimiarMap:
  - is_valid will reflect the map authority's range/LoS validation
  - affected_target_ref_ids will contain all participants in the effect area
  - spatial_metadata will carry distance, geometric area, LoS booleans, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .targeting_diagnostics import TargetingDiagnostics


@dataclass(frozen=True)
class SpatialMetadata:
    """Spatial information returned by the targeting authority.

    All fields are optional. When LimiarMap is not integrated, all fields
    remain None / False. The structure exists so that the mechanical
    resolution layer can reference it without requiring code changes when
    the map integration is added.
    """
    distance_meters: float | None = None
    is_in_normal_range: bool | None = None
    is_in_long_range: bool | None = None
    has_line_of_sight: bool | None = None
    is_adjacent: bool | None = None
    source_token_id: str | None = None
    target_token_id: str | None = None
    affected_token_ids: list[str] = field(default_factory=list)
    affected_cells: list[dict[str, int]] = field(default_factory=list)
    area_shape: str | None = None
    map_version: int | None = None
    targeting_authority: str | None = None
    cover: str | None = None


@dataclass(frozen=True)
class TargetingResult:
    """Output of the CombatTargetingService.validate() call.

    Fields:
        is_valid                        — True if the action may proceed
        failure_reason                  — Human-readable reason when is_valid is False
        validated_primary_target_ref_id — The ref_id of the confirmed primary target
                                          (same as requested for now; may differ if
                                           LimiarMap snaps to nearest valid token)
        affected_target_ref_ids         — All ref_ids affected by the action.
                                          Single-target: list of one. Area: multiple.
        target_kind                     — "player" or "entity" for the primary target
        spatial_metadata                — Optional spatial data from the map authority
    """
    is_valid: bool
    validated_primary_target_ref_id: str
    affected_target_ref_ids: list[str]
    target_kind: str
    failure_reason: str | None = None
    spatial_metadata: SpatialMetadata = field(default_factory=SpatialMetadata)
    diagnostics: TargetingDiagnostics | None = field(default=None)

    @classmethod
    def invalid(
        cls,
        reason: str,
        diagnostics: TargetingDiagnostics | None = None,
    ) -> "TargetingResult":
        """Convenience constructor for a failed targeting result."""
        return cls(
            is_valid=False,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=[],
            target_kind="",
            failure_reason=reason,
            diagnostics=diagnostics,
        )
