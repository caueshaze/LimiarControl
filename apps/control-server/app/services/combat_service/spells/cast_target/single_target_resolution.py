from __future__ import annotations

from .single_target_cast_resolution import CastTargetSingleTargetCastResolutionMixin
from .single_target_no_external_resolution import CastTargetSingleTargetNoExternalResolutionMixin


class CastTargetSingleTargetResolutionMixin(
    CastTargetSingleTargetCastResolutionMixin,
    CastTargetSingleTargetNoExternalResolutionMixin,
):
    pass
