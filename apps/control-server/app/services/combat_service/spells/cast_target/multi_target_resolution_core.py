from __future__ import annotations

from .modal_multi_target_resolution import CastTargetModalMultiTargetResolutionMixin
from .multi_instance_resolution import CastTargetMultiInstanceResolutionMixin


class CastTargetMultiTargetResolutionCoreMixin(
    CastTargetMultiInstanceResolutionMixin,
    CastTargetModalMultiTargetResolutionMixin,
):
    pass
