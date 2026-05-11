from __future__ import annotations

from dataclasses import replace
import logging

from app.integrations.limiar_map_client import (
    LimiarMapClient,
    LimiarMapClientError,
)
from app.models.combat import CombatState

from .targeting_diagnostics import (
    MAP_UNAVAILABLE_FOR_AREA_SPELL,
    CHECK_IN_RANGE,
    CHECK_HAS_LINE_OF_SIGHT,
    CHECK_HAS_LINE_OF_EFFECT,
    CHECK_IS_VISIBLE,
    TargetingDiagnostics,
)
from .targeting_result import SpatialMetadata, TargetingResult
from .targeting_intent import WeaponAttackIntent
from .unit_conversion import METERS_PER_CELL
from .visibility import can_target_in_combat
from .reach import resolve_weapon_attack_range_profile
from .combat_targeting import (
    CombatTargetingService,
    _build_map_spatial_metadata,
    _derive_range_cells,
    _log_diagnostics_debug,
    _map_failure_reason,
    _map_reason_to_canonical,
    _map_visibility_failure,
    _populate_checks_from_map_failure,
    _resolve_area_requires_effect,
    _resolve_area_requires_sight,
    _resolve_single_target_requirements,
    _token_position_to_cell,
    _visibility_reason_to_canonical,
)
from .combat_targeting_local import LocalCombatTargetingService

logger = logging.getLogger(__name__)


class LimiarMapTargetingService(CombatTargetingService):
    def __init__(
        self,
        limiar_map_client: LimiarMapClient,
        fallback_service: CombatTargetingService | None = None,
    ) -> None:
        self._limiar_map_client = limiar_map_client
        if fallback_service is None:
            self._fallback_service = LocalCombatTargetingService(
                skip_range_validation=True
            )
        elif isinstance(fallback_service, LocalCombatTargetingService):
            self._fallback_service = LocalCombatTargetingService(
                skip_range_validation=True
            )
        else:
            self._fallback_service = fallback_service

    def validate(
        self,
        intent,
        state: CombatState,
    ) -> TargetingResult:
        from .targeting_intent import AreaTargetingIntent

        if isinstance(intent, AreaTargetingIntent):
            return self._validate_area(intent, state)

        local_result = self._fallback_service.validate(intent, state)
        if not local_result.is_valid:
            return local_result

        diag = TargetingDiagnostics()
        if local_result.diagnostics:
            for k, v in local_result.diagnostics.checks.items():
                diag.set_check(k, v)

        if isinstance(intent, WeaponAttackIntent):
            weapon_profile = resolve_weapon_attack_range_profile(
                range_meters=intent.range_meters,
                range_long_meters=intent.range_long_meters,
                weapon_range_type=intent.weapon_range_type,
                has_reach=intent.has_reach,
                effective_size=getattr(intent, "actor_effective_size", None),
            )
            if weapon_profile.failure_reason is not None:
                diag.set_check(CHECK_IN_RANGE, False)
                diag.fail(weapon_profile.failure_reason)
                result = TargetingResult.invalid(
                    "Ranged weapon has no range configured. Cannot validate distance.",
                    diagnostics=diag,
                )
                _log_diagnostics_debug(logger, intent, result)
                return result

        range_cells = _derive_range_cells(intent)
        if range_cells is not None:
            diag.set_meta("range_cells", range_cells)

        requires_sight, requires_effect = _resolve_single_target_requirements(
            intent
        )
        try:
            response = self._limiar_map_client.validate_single_target(
                session_id=intent.session_id,
                action_id=intent.action_id,
                combatant_id=intent.actor_ref_id,
                target_combatant_id=intent.requested_target_ref_id,
                range_cells=range_cells,
                requires_sight=requires_sight,
                requires_effect=requires_effect,
            )
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap targeting failed for session_id=%s actor_ref_id=%s "
                "target_ref_id=%s; falling back to local targeting (%s)",
                intent.session_id,
                intent.actor_ref_id,
                intent.requested_target_ref_id,
                exc,
            )
            diag.set_meta("map_fallback", True)
            result = TargetingResult(
                is_valid=local_result.is_valid,
                validated_primary_target_ref_id=local_result.validated_primary_target_ref_id,
                affected_target_ref_ids=local_result.affected_target_ref_ids,
                target_kind=local_result.target_kind,
                spatial_metadata=local_result.spatial_metadata,
                diagnostics=diag,
            )
            _log_diagnostics_debug(logger, intent, result)
            return result

        if not response.is_valid:
            if isinstance(response.distance_cells, int):
                diag.set_meta("distance_cells", response.distance_cells)
                diag.set_meta(
                    "distance_meters", response.distance_cells * METERS_PER_CELL
                )
            canonical = _map_reason_to_canonical(response.reason)
            diag.fail(canonical)
            _populate_checks_from_map_failure(diag, response.reason)
            logger.info(
                "LimiarMap targeting rejected action for session_id=%s actor_ref_id=%s "
                "target_ref_id=%s reason=%s [diag: %s]",
                intent.session_id,
                intent.actor_ref_id,
                intent.requested_target_ref_id,
                response.reason,
                diag.compact_log(),
            )
            result = TargetingResult.invalid(
                _map_failure_reason(response.reason),
                diagnostics=diag,
            )
            _log_diagnostics_debug(logger, intent, result)
            return result

        diag.set_check(CHECK_IN_RANGE, True)
        diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
        diag.set_check(CHECK_HAS_LINE_OF_EFFECT, True)

        spatial_metadata = _build_map_spatial_metadata(response, diag, intent)

        actor_participant = next(
            (p for p in state.participants if p.get("ref_id") == intent.actor_ref_id),
            None,
        )
        target_participant = next(
            (
                p
                for p in state.participants
                if p.get("ref_id") == intent.requested_target_ref_id
            ),
            None,
        )
        if (
            actor_participant is not None
            and target_participant is not None
            and requires_sight
        ):
            can_tgt, fail_reason = can_target_in_combat(
                actor_participant,
                target_participant,
                has_line_of_sight=True,
                requires_sight=True,
            )
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
            diag.set_check(CHECK_IS_VISIBLE, True)

        result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id=local_result.validated_primary_target_ref_id,
            affected_target_ref_ids=local_result.affected_target_ref_ids,
            target_kind=local_result.target_kind,
            spatial_metadata=spatial_metadata,
            diagnostics=diag,
        )
        _log_diagnostics_debug(logger, intent, result)
        return result

    def _validate_area(
        self,
        intent,
        state: CombatState,
    ) -> TargetingResult:
        from .unit_conversion import meters_to_cells

        anchor_participant = (
            next(
                (
                    p
                    for p in state.participants
                    if p.get("ref_id") == intent.requested_target_ref_id
                ),
                None,
            )
            if isinstance(intent.requested_target_ref_id, str)
            else None
        )

        try:
            snapshot = self._limiar_map_client.get_session_state(intent.session_id)
            source_token = next(
                (
                    token
                    for token in snapshot.tokens
                    if token.combatant_id == intent.actor_ref_id
                ),
                None,
            )
            if source_token is None:
                return TargetingResult.invalid("Actor is not linked to a map token.")
            origin_cell = intent.origin_cell or _token_position_to_cell(
                source_token
            )
            if origin_cell is None:
                return TargetingResult.invalid("Actor map token is missing a position.")

            anchor_cell = intent.anchor_cell
            if anchor_cell is None and isinstance(intent.requested_target_ref_id, str):
                anchor_token = next(
                    (
                        token
                        for token in snapshot.tokens
                        if token.combatant_id == intent.requested_target_ref_id
                    ),
                    None,
                )
                if anchor_token is None:
                    return TargetingResult.invalid(
                        "Target anchor is not linked to a map token."
                    )
                anchor_cell = _token_position_to_cell(anchor_token)
            if anchor_cell is None:
                return TargetingResult.invalid("Area anchor is missing.")

            range_cells = (
                meters_to_cells(intent.range_meters)
                if intent.range_meters is not None and intent.range_meters > 0
                else None
            )
            size_cells = meters_to_cells(intent.size_meters)
            response = self._limiar_map_client.resolve_area_targeting(
                session_id=intent.session_id,
                action_id=intent.action_id,
                combatant_id=intent.actor_ref_id,
                shape=intent.shape,
                origin_cell=origin_cell,
                anchor_cell=anchor_cell,
                range_cells=range_cells,
                size_cells=size_cells,
                requires_sight=_resolve_area_requires_sight(intent),
                requires_effect=_resolve_area_requires_effect(intent),
            )
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap area targeting failed session_id=%s actor_ref_id=%s target_ref_id=%s shape=%s; "
                "area targeting cannot continue without the map (%s)",
                intent.session_id,
                intent.actor_ref_id,
                intent.requested_target_ref_id,
                intent.shape,
                exc,
            )
            diag = TargetingDiagnostics()
            diag.fail(MAP_UNAVAILABLE_FOR_AREA_SPELL)
            return TargetingResult.invalid(
                "Area targeting is temporarily unavailable because LimiarMap could not be reached.",
                diagnostics=diag,
            )

        if not response.is_valid:
            logger.info(
                "LimiarMap area targeting rejected action session_id=%s actor_ref_id=%s target_ref_id=%s "
                "shape=%s reason=%s",
                intent.session_id,
                intent.actor_ref_id,
                intent.requested_target_ref_id,
                intent.shape,
                response.reason,
            )
            return TargetingResult.invalid(_map_failure_reason(response.reason))

        participant_by_ref_id = {
            participant.get("ref_id"): participant
            for participant in state.participants
            if isinstance(participant.get("ref_id"), str)
        }
        affected_target_ref_ids = [
            combatant_id
            for combatant_id in response.affected_combatant_ids
            if combatant_id in participant_by_ref_id
        ]
        primary_target_ref_id = (
            intent.requested_target_ref_id
            if isinstance(intent.requested_target_ref_id, str)
            else (affected_target_ref_ids[0] if affected_target_ref_ids else "")
        )
        primary_target_kind = (
            anchor_participant.get("kind")
            if anchor_participant is not None
            else (
                participant_by_ref_id[affected_target_ref_ids[0]].get("kind")
                if affected_target_ref_ids
                else ""
            )
        ) or ""

        return TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id=primary_target_ref_id,
            affected_target_ref_ids=affected_target_ref_ids,
            target_kind=primary_target_kind,
            spatial_metadata=SpatialMetadata(
                source_token_id=response.source_token_id,
                affected_token_ids=list(response.affected_token_ids),
                affected_cells=[
                    {"x": cell.x, "y": cell.y} for cell in response.affected_cells
                ],
                area_shape=response.shape,
                map_version=response.version,
                targeting_authority="limiar_map",
            ),
        )
