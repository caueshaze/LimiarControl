from __future__ import annotations

from ..cast_target_commit import CastTargetCommitMixin
from ..cast_target_effect import CastTargetEffectMixin
from .instance_resolution import CastTargetInstanceResolutionMixin
from .multi_target_resolution_core import CastTargetMultiTargetResolutionCoreMixin
from .orchestrator import CastTargetOrchestratorMixin
from .plain_multi_target_resolution import CastTargetPlainMultiTargetResolutionMixin
from .preconditions import CastTargetPreconditionsMixin
from .rejection_activity import CastTargetRejectionActivityMixin
from .resource_consumption import CastTargetResourceConsumptionMixin
from .single_target_resolution import CastTargetSingleTargetResolutionMixin
from .targeting_validation import CastTargetTargetingValidationMixin
from .teleport_resolution import CastTargetTeleportResolutionMixin


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


__all__ = ["CastTargetMixin"]
