"""visibility.py — Phase F3 centralized visibility resolution.

Provides a structured visibility model that distinguishes:
  - geometric line of sight (LoS)
  - direct visibility (LoS + no sensory/magical blockers)
  - targetability (may target even if not directly visible)

Visibility blockers are resolved from:
  - geometric LoS (provided by the spatial layer)
  - attacker sensory limitations (blinded, unconscious, petrified)
  - target invisibility
  - target obscurement (heavily obscured blocks; lightly obscured does not)

This module is the single source of truth for visibility resolution.
All condition-based checks are delegated to condition_effects helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .condition_effects import can_see, has_condition, is_invisible


@dataclass(frozen=True)
class TargetVisibilityContext:
    """Structured visibility result for an attacker→target pair.

    Fields:
        has_line_of_sight:  True when a geometric sight path exists.
                            Determined by the spatial layer; defaults True
                            when no spatial authority is available.
        is_directly_visible: True when the attacker can directly perceive the
                             target.  Requires LoS AND no visibility blockers.
        visibility_state:   "visible" | "not_visible"
        visibility_blockers: Machine-readable reason identifiers.
                             Stable values:
                               - no_line_of_sight
                               - attacker_cannot_see
                               - target_invisible
                               - target_heavily_obscured
    """

    has_line_of_sight: bool
    is_directly_visible: bool
    visibility_state: Literal["visible", "not_visible"]
    visibility_blockers: list[str] = field(default_factory=list)

    def describe(self) -> str:
        if self.is_directly_visible:
            return "visible"
        return f"not_visible ({', '.join(self.visibility_blockers)})"


def _is_heavily_obscured(participant: dict) -> bool:
    return has_condition(participant, "heavily_obscured")


def _is_lightly_obscured(participant: dict) -> bool:
    return has_condition(participant, "lightly_obscured")


def resolve_target_visibility(
    attacker: dict,
    target: dict,
    *,
    has_line_of_sight: bool = True,
) -> TargetVisibilityContext:
    """Resolve the full visibility state of *target* from *attacker*'s perspective.

    Args:
        attacker:  Participant dict (must have ``active_effects``).
        target:    Participant dict (must have ``active_effects``).
        has_line_of_sight: Geometric LoS from the spatial layer.
                           Defaults True when no spatial authority is active.

    Returns:
        A :class:`TargetVisibilityContext` with the resolved state.
    """
    blockers: list[str] = []

    if not has_line_of_sight:
        blockers.append("no_line_of_sight")

    if not can_see(attacker):
        blockers.append("attacker_cannot_see")

    if is_invisible(target):
        blockers.append("target_invisible")

    if _is_heavily_obscured(target):
        blockers.append("target_heavily_obscured")

    directly_visible = not blockers
    vis_state: Literal["visible", "not_visible"] = (
        "visible" if directly_visible else "not_visible"
    )

    return TargetVisibilityContext(
        has_line_of_sight=has_line_of_sight,
        is_directly_visible=directly_visible,
        visibility_state=vis_state,
        visibility_blockers=blockers,
    )


def can_directly_see_target(
    attacker: dict,
    target: dict,
    *,
    has_line_of_sight: bool = True,
) -> bool:
    """Convenience: return True when attacker can directly see target."""
    return resolve_target_visibility(
        attacker,
        target,
        has_line_of_sight=has_line_of_sight,
    ).is_directly_visible


def can_target_in_combat(
    attacker: dict,
    target: dict,
    *,
    has_line_of_sight: bool = True,
    requires_sight: bool = False,
) -> tuple[bool, str | None]:
    """Return (can_target, failure_reason) for simplified known-location combat.

    Rules (Phase F3):
      - If requires_sight and target not directly visible → cannot target.
      - Otherwise → may target (may still suffer attack disadvantage).
    """
    if not requires_sight:
        return True, None

    vis = resolve_target_visibility(
        attacker,
        target,
        has_line_of_sight=has_line_of_sight,
    )
    if vis.is_directly_visible:
        return True, None

    if not vis.has_line_of_sight:
        return False, "no_line_of_sight"

    return False, "target_not_visible"
