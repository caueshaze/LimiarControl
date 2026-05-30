from __future__ import annotations

from ...targeting_diagnostics import NO_LINE_OF_EFFECT, NO_LINE_OF_SIGHT, NOT_VISIBLE, TARGET_OUT_OF_REACH
from ...targeting_result import TargetingResult


def resolve_instance_spatial_error_phrase(result: TargetingResult) -> str:
    diag = result.diagnostics
    if diag:
        if TARGET_OUT_OF_REACH in diag.failure_reasons:
            return "is out of range"
        if NO_LINE_OF_SIGHT in diag.failure_reasons:
            return "has blocked line of sight"
        if NO_LINE_OF_EFFECT in diag.failure_reasons:
            return "has blocked line of effect"
        if NOT_VISIBLE in diag.failure_reasons:
            return "is not visible"
    return result.failure_reason or "cannot be targeted"
