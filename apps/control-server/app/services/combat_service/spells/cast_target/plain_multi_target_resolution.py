from __future__ import annotations

from .plain_multi_target_resolver import CastTargetPlainMultiTargetResolverMixin
from .plain_multi_target_validation import CastTargetPlainMultiTargetValidationMixin


class CastTargetPlainMultiTargetResolutionMixin(
    CastTargetPlainMultiTargetValidationMixin,
    CastTargetPlainMultiTargetResolverMixin,
):
    pass
