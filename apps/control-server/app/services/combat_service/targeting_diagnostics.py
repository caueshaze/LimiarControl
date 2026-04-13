"""Phase F4.5 — Targeting diagnostics.

TargetingDiagnostics captures every check performed during a targeting
validation attempt so that failures are explainable and consistent.

Canonical failure reasons are defined here as module-level constants so
that callers, tests, and future UI consumers share a single vocabulary.
All reasons are machine-readable identifiers — do NOT change them without
a migration plan for existing consumers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Canonical failure reasons ─────────────────────────────────────────────────

TARGET_NOT_FOUND = "target_not_found"
INVALID_TARGET_TYPE = "invalid_target_type"
AREA_TARGETING_UNAVAILABLE = "area_targeting_unavailable"
MAP_UNAVAILABLE_FOR_AREA_SPELL = "map_unavailable_for_area_spell"
TARGET_OUT_OF_REACH = "target_out_of_reach"
NO_LINE_OF_SIGHT = "no_line_of_sight"
NO_LINE_OF_EFFECT = "no_line_of_effect"
NOT_VISIBLE = "not_visible"
BLOCKED_BY_CONDITION = "blocked_by_condition"
SELF_TARGET_NOT_ALLOWED = "self_target_not_allowed"
MAP_UNREACHABLE = "map_unreachable"

ALL_CANONICAL_REASONS: frozenset[str] = frozenset(
    {
        TARGET_NOT_FOUND,
        INVALID_TARGET_TYPE,
        AREA_TARGETING_UNAVAILABLE,
        MAP_UNAVAILABLE_FOR_AREA_SPELL,
        TARGET_OUT_OF_REACH,
        NO_LINE_OF_SIGHT,
        NO_LINE_OF_EFFECT,
        NOT_VISIBLE,
        BLOCKED_BY_CONDITION,
        SELF_TARGET_NOT_ALLOWED,
        MAP_UNREACHABLE,
    }
)


# ── Check names (keys used in TargetingDiagnostics.checks) ───────────────────

CHECK_TARGET_FOUND = "target_found"
CHECK_TARGET_KIND_VALID = "target_kind_valid"
CHECK_IN_RANGE = "in_range"
CHECK_HAS_LINE_OF_SIGHT = "has_line_of_sight"
CHECK_HAS_LINE_OF_EFFECT = "has_line_of_effect"
CHECK_IS_VISIBLE = "is_visible"


@dataclass
class TargetingDiagnostics:
    """Structured record of a single targeting validation attempt.

    Produced for every ``validate()`` call — on success and on failure alike.
    Clients may inspect ``failure_reasons`` for UI feedback or structured
    debug logging.

    Attributes:
        is_valid:        Whether the targeting attempt succeeded.
        failure_reasons: Ordered list of canonical reason codes — empty on success.
        checks:          Named boolean outcomes for each check performed.
                         Not all checks are performed for every action type.
        metadata:        Supplementary numeric/string data (distances, cover, …).
    """

    is_valid: bool = True
    failure_reasons: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── mutation helpers ───────────────────────────────────────────────────────

    def fail(self, reason: str) -> None:
        """Record *reason* and mark this attempt as invalid.

        Idempotent — the same code is never appended twice.
        """
        self.is_valid = False
        if reason not in self.failure_reasons:
            self.failure_reasons.append(reason)

    def set_check(self, name: str, passed: bool) -> None:
        """Record the boolean outcome of a named check."""
        self.checks[name] = passed

    def set_meta(self, key: str, value: Any) -> None:
        """Record supplementary metadata (distances, cover type, …)."""
        self.metadata[key] = value

    # ── read helpers ───────────────────────────────────────────────────────────

    def primary_failure(self) -> str | None:
        """Return the first failure reason, or *None* when valid."""
        return self.failure_reasons[0] if self.failure_reasons else None

    def compact_log(self) -> str:
        """Return a short, structured log line suitable for combat logs.

        Success: ``"ok [dist=1, range=1, cover=half_cover]"``
        Failure: ``"target_out_of_reach [dist=3, range=1]"``
        """
        meta_parts: list[str] = []
        if "distance_cells" in self.metadata:
            meta_parts.append(f"dist={self.metadata['distance_cells']}")
        if "range_cells" in self.metadata:
            meta_parts.append(f"range={self.metadata['range_cells']}")
        if self.metadata.get("cover"):
            meta_parts.append(f"cover={self.metadata['cover']}")
        meta_str = f" [{', '.join(meta_parts)}]" if meta_parts else ""

        if self.is_valid:
            return f"ok{meta_str}"

        reasons = ", ".join(self.failure_reasons) if self.failure_reasons else "invalid"
        return f"{reasons}{meta_str}"
