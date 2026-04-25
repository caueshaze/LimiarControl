from __future__ import annotations

import logging

from app.core.config import settings
from app.models.combat import CombatState

from .targeting_intent import (
    ActionIntent,
    AreaTargetingIntent,
    SpellCastIntent,
    WeaponAttackIntent,
)
from .reach import derive_max_range_meters
from .reach import (
    classify_weapon_attack_distance,
    resolve_weapon_attack_range_profile,
)
from .targeting_diagnostics import (
    TARGET_NOT_FOUND,
    INVALID_TARGET_TYPE,
    MAP_UNAVAILABLE_FOR_AREA_SPELL,
    TARGET_OUT_OF_REACH,
    WEAPON_RANGE_NOT_CONFIGURED,
    SPELL_RANGE_NOT_CONFIGURED,
    CHECK_TARGET_FOUND,
    CHECK_TARGET_KIND_VALID,
    CHECK_IN_RANGE,
    CHECK_HAS_LINE_OF_SIGHT,
    CHECK_IS_VISIBLE,
    TargetingDiagnostics,
)
from .targeting_result import SpatialMetadata, TargetingResult
from .visibility import can_target_in_combat
from .combat_targeting import (
    CombatTargetingService,
    _log_diagnostics_debug,
    _map_visibility_failure,
    _visibility_reason_to_canonical,
)

logger = logging.getLogger(__name__)


_RANGE_FAILURE_MESSAGES: dict[str, str] = {
    WEAPON_RANGE_NOT_CONFIGURED: "Ranged weapon has no range configured. Cannot validate distance.",
    SPELL_RANGE_NOT_CONFIGURED: "Spell range is not configured. Cannot validate distance.",
}


def _get_local_distance(state: CombatState, from_ref: str, to_ref: str) -> float | None:
    distances = state.local_distances if isinstance(state.local_distances, dict) else {}
    from_map = distances.get(from_ref)
    if isinstance(from_map, dict):
        d = from_map.get(to_ref)
        if isinstance(d, (int, float)):
            return float(d)
    to_map = distances.get(to_ref)
    if isinstance(to_map, dict):
        d = to_map.get(from_ref)
        if isinstance(d, (int, float)):
            return float(d)
    return None


class LocalCombatTargetingService(CombatTargetingService):
    """Local targeting service for non-map (theater-of-mind) combat.

    Behaviour
    ---------
    - Looks up the requested target in state.participants.
    - Confirms the target exists and its kind is resolved.
    - Validates visibility (condition-based: invisible, blinded, etc.).
    - Validates weapon/spell range using ``state.local_distances``
      (only when *not* acting as a map fallback).
    - Returns a valid TargetingResult with a single affected target.
    - Does NOT validate line-of-sight geometry or area geometry.

    Range validation
    ----------------
    When ``skip_range_validation`` is *False* (the default — used when
    ``use_map=False``), ``state.local_distances`` is consulted:

    * Melee weapons: 1.5 m (1 cell) default, 3 m (2 cells) with reach.
    * Ranged weapons: ``range_meters`` from the weapon metadata.
    * Ranged weapons without ``range_meters``: **fails** with
      ``weapon_range_not_configured``.
    * Spells with ``target_type="self"``: no range constraint.
    * Spells with ``target_type="touch"``: 1.5 m.
    * Spells with ``range_meters > 0``: uses that value.

    When ``skip_range_validation`` is *True* (used as a fallback inside
    ``LimiarMapTargetingService``), range checks are skipped entirely
    because the map service handles its own range validation.
    """

    def __init__(self, skip_range_validation: bool = False) -> None:
        self._skip_range_validation = skip_range_validation

    def validate(
        self,
        intent: ActionIntent,
        state: CombatState,
    ) -> TargetingResult:
        diag = TargetingDiagnostics()

        if isinstance(intent, AreaTargetingIntent):
            diag.fail(MAP_UNAVAILABLE_FOR_AREA_SPELL)
            result = TargetingResult.invalid(
                "Area targeting requires LimiarMap integration which is unavailable.",
                diagnostics=diag,
            )
            _log_diagnostics_debug(logger, intent, result)
            return result

        requested_ref_id = intent.requested_target_ref_id

        target_participant = next(
            (p for p in state.participants if p.get("ref_id") == requested_ref_id),
            None,
        )
        diag.set_check(CHECK_TARGET_FOUND, target_participant is not None)
        if target_participant is None:
            diag.fail(TARGET_NOT_FOUND)
            result = TargetingResult.invalid(
                "Target not found in combat.", diagnostics=diag
            )
            _log_diagnostics_debug(logger, intent, result)
            return result

        target_kind = target_participant.get("kind")
        kind_valid = isinstance(target_kind, str) and target_kind in (
            "player",
            "entity",
            "session_entity",
        )
        diag.set_check(CHECK_TARGET_KIND_VALID, kind_valid)
        if not kind_valid:
            diag.fail(INVALID_TARGET_TYPE)
            result = TargetingResult.invalid(
                f"Target has an unrecognised kind: {target_kind!r}.",
                diagnostics=diag,
            )
            _log_diagnostics_debug(logger, intent, result)
            return result

        requires_sight = False
        if isinstance(intent, (WeaponAttackIntent, SpellCastIntent)):
            requires_sight = bool(intent.requires_sight)

        if requires_sight:
            attacker_participant = next(
                (
                    p
                    for p in state.participants
                    if p.get("ref_id") == intent.actor_ref_id
                ),
                None,
            )
            if attacker_participant is not None:
                can_tgt, fail_reason = can_target_in_combat(
                    attacker_participant,
                    target_participant,
                    has_line_of_sight=True,
                    requires_sight=True,
                )
                diag.set_check(CHECK_HAS_LINE_OF_SIGHT, can_tgt)
                diag.set_check(CHECK_IS_VISIBLE, can_tgt)
                if not can_tgt:
                    diag.fail(_visibility_reason_to_canonical(fail_reason))
                    result = TargetingResult.invalid(
                        _map_visibility_failure(fail_reason),
                        diagnostics=diag,
                    )
                    _log_diagnostics_debug(logger, intent, result)
                    return result
            else:
                diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
                diag.set_check(CHECK_IS_VISIBLE, True)
        else:
            diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
            diag.set_check(CHECK_IS_VISIBLE, True)

        weapon_profile = None
        if isinstance(intent, WeaponAttackIntent):
            weapon_profile = resolve_weapon_attack_range_profile(
                range_meters=getattr(intent, "range_meters", None),
                range_long_meters=getattr(intent, "range_long_meters", None),
                weapon_range_type=getattr(intent, "weapon_range_type", None),
                has_reach=getattr(intent, "has_reach", False),
            )
            max_range = weapon_profile.max_range
            range_failure = weapon_profile.failure_reason
        else:
            max_range, range_failure = derive_max_range_meters(
                range_meters=getattr(intent, "range_meters", None),
                weapon_range_type=getattr(intent, "weapon_range_type", None),
                has_reach=getattr(intent, "has_reach", False),
                target_type=getattr(intent, "target_type", None),
                range_kind=getattr(intent, "range_kind", None),
            )

        spatial_metadata = SpatialMetadata(targeting_authority="local")

        if not self._skip_range_validation:
            if range_failure is not None:
                diag.set_check(CHECK_IN_RANGE, False)
                diag.fail(range_failure)
                result = TargetingResult.invalid(
                    _RANGE_FAILURE_MESSAGES.get(range_failure, range_failure),
                    diagnostics=diag,
                )
                _log_diagnostics_debug(logger, intent, result)
                return result

            if max_range is not None:
                distance_meters = _get_local_distance(
                    state, intent.actor_ref_id, requested_ref_id
                )
                if distance_meters is None:
                    diag.set_check(CHECK_IN_RANGE, False)
                    diag.fail(TARGET_OUT_OF_REACH)
                    result = TargetingResult.invalid(
                        "Target distance not configured for non-map combat. "
                        "GM must set combat distances first.",
                        diagnostics=diag,
                    )
                    _log_diagnostics_debug(logger, intent, result)
                    return result
                diag.set_meta("distance_meters", distance_meters)
                diag.set_meta("max_range_meters", max_range)
                if weapon_profile is not None and weapon_profile.normal_range is not None:
                    diag.set_meta("normal_range_meters", weapon_profile.normal_range)
                    if weapon_profile.long_range is not None:
                        diag.set_meta("long_range_meters", weapon_profile.long_range)
                    range_classification = classify_weapon_attack_distance(
                        distance_meters,
                        normal_range=weapon_profile.normal_range,
                        long_range=weapon_profile.long_range,
                    )
                    spatial_metadata = SpatialMetadata(
                        distance_meters=distance_meters,
                        is_in_normal_range=range_classification.is_in_normal_range,
                        is_in_long_range=range_classification.is_in_long_range,
                        targeting_authority="local",
                    )
                    if not range_classification.is_in_range:
                        diag.set_check(CHECK_IN_RANGE, False)
                        diag.fail(TARGET_OUT_OF_REACH)
                        result = TargetingResult.invalid(
                            f"Target out of range ({distance_meters:.1f}m > {max_range:.1f}m).",
                            diagnostics=diag,
                        )
                        _log_diagnostics_debug(logger, intent, result)
                        return result
                elif distance_meters > max_range:
                    diag.set_check(CHECK_IN_RANGE, False)
                    diag.fail(TARGET_OUT_OF_REACH)
                    result = TargetingResult.invalid(
                        f"Target out of range ({distance_meters:.1f}m > {max_range:.1f}m).",
                        diagnostics=diag,
                    )
                    _log_diagnostics_debug(logger, intent, result)
                    return result
                else:
                    spatial_metadata = SpatialMetadata(
                        distance_meters=distance_meters,
                        targeting_authority="local",
                    )
            diag.set_check(CHECK_IN_RANGE, True)

        result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id=requested_ref_id,
            affected_target_ref_ids=[requested_ref_id],
            target_kind=target_kind,
            spatial_metadata=spatial_metadata,
            diagnostics=diag,
        )
        _log_diagnostics_debug(logger, intent, result)
        return result
