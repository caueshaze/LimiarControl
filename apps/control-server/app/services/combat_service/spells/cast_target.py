from __future__ import annotations

from .cast_target import (
    CastTargetInstanceResolutionMixin,
    CastTargetMultiTargetResolutionCoreMixin,
    CastTargetOrchestratorMixin,
    CastTargetPlainMultiTargetResolutionMixin,
    CastTargetPreconditionsMixin,
    CastTargetRejectionActivityMixin,
    CastTargetResourceConsumptionMixin,
    CastTargetSingleTargetResolutionMixin,
    CastTargetTargetingValidationMixin,
    CastTargetTeleportResolutionMixin,
)
from .cast_target_commit import CastTargetCommitMixin
from .cast_target_effect import CastTargetEffectMixin


class CastTargetMixin(
    CastTargetOrchestratorMixin,
    CastTargetPlainMultiTargetResolutionMixin,
    CastTargetSingleTargetResolutionMixin,
    CastTargetMultiTargetResolutionCoreMixin,
    CastTargetInstanceResolutionMixin,
    CastTargetTargetingValidationMixin,
    CastTargetPreconditionsMixin,
    CastTargetRejectionActivityMixin,
    CastTargetTeleportResolutionMixin,
    CastTargetResourceConsumptionMixin,
    CastTargetCommitMixin,
    CastTargetEffectMixin,
):
    pass
