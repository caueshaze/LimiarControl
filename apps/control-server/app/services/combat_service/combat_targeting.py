from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
import logging

from app.core.config import settings
from app.integrations.limiar_map_client import LimiarMapClient
from app.models.combat import CombatState

from .reach import classify_weapon_attack_distance, resolve_weapon_attack_range_profile
from .targeting_diagnostics import (
    CHECK_HAS_LINE_OF_EFFECT,
    CHECK_HAS_LINE_OF_SIGHT,
    CHECK_IN_RANGE,
    CHECK_IS_VISIBLE,
    NO_LINE_OF_EFFECT,
    NO_LINE_OF_SIGHT,
    NOT_VISIBLE,
    TARGET_OUT_OF_REACH,
    TargetingDiagnostics,
)
from .targeting_intent import ActionIntent, AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from .targeting_requirements import resolve_spell_targeting_requirements, resolve_weapon_targeting_requirements
from .targeting_result import SpatialMetadata, TargetingResult
from .unit_conversion import METERS_PER_CELL, meters_to_cells

logger = logging.getLogger(__name__)


def _map_visibility_failure(reason: str | None) -> str:
    if reason == "target_not_visible":
        return "Target is not visible."
    if reason == "no_line_of_sight":
        return "Target is blocked by line of sight."
    if reason:
        return f"Targeting failed ({reason})."
    return "Targeting failed."


def _visibility_reason_to_canonical(reason: str | None) -> str:
    if reason == "no_line_of_sight":
        return NO_LINE_OF_SIGHT
    return NOT_VISIBLE


def _log_diagnostics_debug(
    log: logging.Logger,
    intent: ActionIntent,
    result: TargetingResult,
) -> None:
    if not settings.combat_debug_targeting or result.diagnostics is None:
        return
    diag = result.diagnostics
    log.debug(
        "[targeting:debug] session=%s actor=%s target=%s valid=%s reasons=%s checks=%s meta=%s",
        intent.session_id,
        intent.actor_ref_id,
        getattr(intent, "requested_target_ref_id", None),
        diag.is_valid,
        diag.failure_reasons,
        diag.checks,
        diag.metadata,
    )


class CombatTargetingService(ABC):
    @abstractmethod
    def validate(
        self,
        intent: ActionIntent,
        state: CombatState,
    ) -> TargetingResult:
        """Validate the spatial aspects of an action intent."""


def _build_map_spatial_metadata(
    response,
    diag: TargetingDiagnostics,
    intent: ActionIntent,
) -> SpatialMetadata:
    spatial_metadata = SpatialMetadata(
        source_token_id=response.source_token_id,
        target_token_id=response.target_token_id,
        map_version=response.version,
        targeting_authority="limiar_map",
        cover=response.cover,
        has_line_of_sight=True,
    )
    if getattr(response, "cover", None):
        diag.set_meta("cover", response.cover)
    if not isinstance(response.distance_cells, int):
        return spatial_metadata

    diag.set_meta("distance_cells", response.distance_cells)
    diag.set_meta("distance_meters", response.distance_cells * METERS_PER_CELL)
    spatial_metadata = replace(
        spatial_metadata,
        distance_meters=response.distance_cells * METERS_PER_CELL,
    )
    if not isinstance(intent, WeaponAttackIntent):
        return spatial_metadata

    weapon_profile = resolve_weapon_attack_range_profile(
        range_meters=intent.range_meters,
        range_long_meters=intent.range_long_meters,
        weapon_range_type=intent.weapon_range_type,
        has_reach=intent.has_reach,
        effective_size=getattr(intent, "actor_effective_size", None),
    )
    if weapon_profile.normal_range is None:
        return spatial_metadata

    normal_range_cells = meters_to_cells(weapon_profile.normal_range)
    long_range_cells = (
        meters_to_cells(weapon_profile.long_range)
        if weapon_profile.long_range is not None
        else None
    )
    range_classification = classify_weapon_attack_distance(
        response.distance_cells,
        normal_range=normal_range_cells,
        long_range=long_range_cells,
    )
    diag.set_meta("normal_range_cells", normal_range_cells)
    if long_range_cells is not None:
        diag.set_meta("long_range_cells", long_range_cells)
    return replace(
        spatial_metadata,
        is_in_normal_range=range_classification.is_in_normal_range,
        is_in_long_range=range_classification.is_in_long_range,
    )


def _map_reason_to_canonical(reason: str | None) -> str:
    if reason == "out_of_range":
        return TARGET_OUT_OF_REACH
    if reason == "no_line_of_sight":
        return NO_LINE_OF_SIGHT
    if reason in ("no_line_of_effect", "full_cover"):
        return NO_LINE_OF_EFFECT
    return TARGET_OUT_OF_REACH


def _populate_checks_from_map_failure(
    diag: TargetingDiagnostics,
    reason: str | None,
) -> None:
    if reason == "out_of_range":
        diag.set_check(CHECK_IN_RANGE, False)
        diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
        diag.set_check(CHECK_HAS_LINE_OF_EFFECT, True)
        return
    if reason == "no_line_of_sight":
        diag.set_check(CHECK_IN_RANGE, True)
        diag.set_check(CHECK_HAS_LINE_OF_SIGHT, False)
        diag.set_check(CHECK_HAS_LINE_OF_EFFECT, True)
        return
    if reason in ("no_line_of_effect", "full_cover"):
        diag.set_check(CHECK_IN_RANGE, True)
        diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
        diag.set_check(CHECK_HAS_LINE_OF_EFFECT, False)
        return
    diag.set_check(CHECK_IN_RANGE, False)
    diag.set_check(CHECK_HAS_LINE_OF_SIGHT, False)
    diag.set_check(CHECK_HAS_LINE_OF_EFFECT, False)


def _map_failure_reason(reason: str | None) -> str:
    if reason == "out_of_range":
        return "Target is out of range."
    if reason == "no_line_of_sight":
        return "Target is blocked by line of sight."
    if reason == "no_line_of_effect":
        return "Target is blocked by line of effect."
    if reason == "full_cover":
        return "Target has full cover and cannot be directly targeted."
    if reason == "invalid_origin":
        return "Area origin is outside the map grid."
    if reason == "invalid_anchor":
        return "Area anchor is outside the map grid."
    if reason == "token_not_linked":
        return "Actor or target is not linked to a map token."
    if reason == "unknown_combatant":
        return "Actor or target is not present in the active map encounter."
    if reason:
        return f"Map targeting rejected the action ({reason})."
    return "Map targeting rejected the action."


def _token_position_to_cell(token: object) -> dict[str, int] | None:
    position_x = getattr(token, "position_x", None)
    position_y = getattr(token, "position_y", None)
    if not isinstance(position_x, int) or not isinstance(position_y, int):
        return None
    return {"x": position_x, "y": position_y}


def _derive_range_cells(intent: ActionIntent) -> int | None:
    if isinstance(intent, SpellCastIntent):
        if intent.range_kind == "self":
            return None
        if intent.range_kind == "touch":
            return meters_to_cells(1.5)
        if isinstance(intent.range_meters, (int, float)) and intent.range_meters > 0:
            return meters_to_cells(intent.range_meters)
        return None
    if not isinstance(intent, WeaponAttackIntent):
        return None
    profile = resolve_weapon_attack_range_profile(
        range_meters=intent.range_meters,
        range_long_meters=intent.range_long_meters,
        weapon_range_type=intent.weapon_range_type,
        has_reach=intent.has_reach,
        effective_size=getattr(intent, "actor_effective_size", None),
    )
    if profile.max_range is not None:
        return meters_to_cells(profile.max_range)
    return None


def _resolve_single_target_requirements(
    intent: WeaponAttackIntent | SpellCastIntent,
) -> tuple[bool, bool]:
    if isinstance(intent, WeaponAttackIntent):
        resolved = resolve_weapon_targeting_requirements(
            requires_target_sight=intent.requires_sight if isinstance(intent.requires_sight, bool) else None,
            requires_target_effect=intent.requires_effect if isinstance(intent.requires_effect, bool) else None,
        )
        return resolved.requires_target_sight, resolved.requires_target_effect

    resolved = resolve_spell_targeting_requirements(
        {
            "target_type": intent.target_type,
            "selection_type": intent.selection_type,
            "attack_type": intent.attack_type,
            "range_kind": intent.range_kind,
            "area_shape": getattr(intent, "area_shape", None),
            "spell_mode": intent.spell_mode,
            "requires_target_sight": intent.requires_sight if isinstance(intent.requires_sight, bool) else None,
            "requires_target_effect": intent.requires_effect if isinstance(intent.requires_effect, bool) else None,
        },
        spell_mode=intent.spell_mode,
    )
    return resolved.requires_target_sight, resolved.requires_target_effect


def _resolve_area_requires_sight(intent: AreaTargetingIntent) -> bool:
    resolved = resolve_spell_targeting_requirements(
        {
            "target_type": intent.target_type,
            "selection_type": intent.selection_type,
            "origin_type": intent.origin_type,
            "target_anchor": intent.target_anchor,
            "attack_type": intent.attack_type,
            "range_kind": intent.range_kind,
            "effect_timing": intent.effect_timing,
            "area_shape": getattr(intent, "area_shape", None),
            "spell_mode": intent.spell_mode,
            "requires_point_sight": intent.requires_sight if isinstance(intent.requires_sight, bool) else None,
        },
        spell_mode=intent.spell_mode,
    )
    return resolved.requires_point_sight


def _resolve_area_requires_effect(intent: AreaTargetingIntent) -> bool:
    resolved = resolve_spell_targeting_requirements(
        {
            "target_type": intent.target_type,
            "selection_type": intent.selection_type,
            "origin_type": intent.origin_type,
            "target_anchor": intent.target_anchor,
            "attack_type": intent.attack_type,
            "range_kind": intent.range_kind,
            "effect_timing": intent.effect_timing,
            "area_shape": getattr(intent, "area_shape", None),
            "spell_mode": intent.spell_mode,
            "requires_point_effect": intent.requires_effect if isinstance(intent.requires_effect, bool) else None,
        },
        spell_mode=intent.spell_mode,
    )
    return resolved.requires_point_effect


from .combat_targeting_local import LocalCombatTargetingService  # noqa: E402
from .combat_targeting_map import LimiarMapTargetingService  # noqa: E402

_map_targeting_service: CombatTargetingService | None = None
_map_targeting_service_signature: tuple[str, float] | None = None
_local_targeting_service: LocalCombatTargetingService | None = None
_map_fallback_targeting_service: LocalCombatTargetingService | None = None


def reset_combat_targeting_service() -> None:
    global _map_targeting_service
    global _map_targeting_service_signature
    global _local_targeting_service
    global _map_fallback_targeting_service
    _map_targeting_service = None
    _map_targeting_service_signature = None
    _local_targeting_service = None
    _map_fallback_targeting_service = None


def _get_local_targeting_service() -> LocalCombatTargetingService:
    global _local_targeting_service
    if _local_targeting_service is None:
        _local_targeting_service = LocalCombatTargetingService()
    return _local_targeting_service


def _get_map_fallback_targeting_service() -> LocalCombatTargetingService:
    global _map_fallback_targeting_service
    if _map_fallback_targeting_service is None:
        _map_fallback_targeting_service = LocalCombatTargetingService(
            skip_range_validation=True
        )
    return _map_fallback_targeting_service


def _get_map_targeting_service() -> CombatTargetingService:
    global _map_targeting_service, _map_targeting_service_signature
    signature = (
        settings.limiar_map_base_url,
        settings.limiar_map_timeout_seconds,
    )
    if _map_targeting_service is None or _map_targeting_service_signature != signature:
        logger.info(
            "Combat targeting service using LimiarMapTargetingService base_url=%s timeout_seconds=%s",
            settings.limiar_map_base_url,
            settings.limiar_map_timeout_seconds,
        )
        _map_targeting_service = LimiarMapTargetingService(
            LimiarMapClient(
                base_url=settings.limiar_map_base_url,
                timeout_seconds=settings.limiar_map_timeout_seconds,
            ),
            fallback_service=_get_map_fallback_targeting_service(),
        )
        _map_targeting_service_signature = signature
    return _map_targeting_service


def get_combat_targeting_service(use_map: bool = True) -> CombatTargetingService:
    if not use_map or not settings.limiar_map_enabled:
        return _get_local_targeting_service()
    return _get_map_targeting_service()
