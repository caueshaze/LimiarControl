from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified

from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw

from ...combat_targeting import get_combat_targeting_service
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


__all__ = [
    "CastTargetMixin",
    "flag_modified",
    "get_combat_targeting_service",
    "resolve_attack_base",
    "resolve_saving_throw",
]
