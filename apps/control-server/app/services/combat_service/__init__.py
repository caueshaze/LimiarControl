from .combat_targeting import (
    CombatTargetingService,
    LimiarMapTargetingService,
    LocalCombatTargetingService,
    get_combat_targeting_service,
    reset_combat_targeting_service,
)
from .exceptions import CombatServiceError, _parse_dice, _roll_dice_expression
from .limiar_map_projection import (
    LimiarMapCombatProjectionService,
    LimiarMapCombatProjectionResult,
    get_limiar_map_projection_service,
    maybe_project_combat_advance_to_limiar_map,
    maybe_project_combat_end_to_limiar_map,
    maybe_project_combat_start_to_limiar_map,
    maybe_sync_conditions_to_limiar_map,
    reset_limiar_map_projection_service,
)
from .service import CombatService
from .targeting_intent import ActionIntent, AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from .targeting_result import SpatialMetadata, TargetingResult

__all__ = [
    "CombatService",
    "CombatServiceError",
    "LimiarMapCombatProjectionService",
    "LimiarMapCombatProjectionResult",
    "_parse_dice",
    "_roll_dice_expression",
    # Targeting layer
    "ActionIntent",
    "AreaTargetingIntent",
    "CombatTargetingService",
    "LimiarMapTargetingService",
    "LocalCombatTargetingService",
    "get_combat_targeting_service",
    "get_limiar_map_projection_service",
    "maybe_project_combat_advance_to_limiar_map",
    "maybe_project_combat_end_to_limiar_map",
    "maybe_project_combat_start_to_limiar_map",
    "maybe_sync_conditions_to_limiar_map",
    "reset_combat_targeting_service",
    "reset_limiar_map_projection_service",
    "SpellCastIntent",
    "WeaponAttackIntent",
    "SpatialMetadata",
    "TargetingResult",
]
