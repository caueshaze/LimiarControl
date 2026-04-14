"""
CombatTargetingService — spatial validation layer between action intent
and mechanical resolution.

Architecture
------------
This module defines the boundary between:
    1. Action Intent     (what the actor wants to do)
    2. Spatial Validation (is the action geometrically valid?)
    3. Mechanical Resolution (apply rules — damage, saves, effects)

The interface CombatTargetingService declares the contract that any
targeting authority must implement. Today there is one implementation:
LocalCombatTargetingService, which preserves current behaviour (accept
any target that exists in the combat state) without consulting a map.

Future integration with LimiarMap
----------------------------------
To plug in the real spatial authority, create a new class:

    class LimiarMapTargetingService(CombatTargetingService):
        def __init__(self, limiar_map_client: LimiarMapClient): ...

        def validate(
            self,
            intent: ActionIntent,
            state: CombatState,
        ) -> TargetingResult:
            # 1. Build spatial request from intent + participant positions
            # 2. Call LimiarMap HTTP/WS endpoint
            # 3. Map LimiarMap response → TargetingResult
            ...

Then swap the implementation in get_combat_targeting_service() or inject
it per-request. No changes to attack(), cast_spell() or any other
mechanical resolution code are needed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging

from app.core.config import settings
from app.integrations.limiar_map_client import (
    LimiarMapClient,
    LimiarMapClientError,
)
from app.models.combat import CombatState

from .targeting_intent import (
    ActionIntent,
    AreaTargetingIntent,
    SpellCastIntent,
    WeaponAttackIntent,
)
from .targeting_requirements import (
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)
from .reach import resolve_melee_reach_cells
from .targeting_diagnostics import (
    TARGET_NOT_FOUND,
    INVALID_TARGET_TYPE,
    AREA_TARGETING_UNAVAILABLE,
    MAP_UNAVAILABLE_FOR_AREA_SPELL,
    TARGET_OUT_OF_REACH,
    NO_LINE_OF_SIGHT,
    NO_LINE_OF_EFFECT,
    NOT_VISIBLE,
    MAP_UNREACHABLE,
    CHECK_TARGET_FOUND,
    CHECK_TARGET_KIND_VALID,
    CHECK_IN_RANGE,
    CHECK_HAS_LINE_OF_SIGHT,
    CHECK_HAS_LINE_OF_EFFECT,
    CHECK_IS_VISIBLE,
    TargetingDiagnostics,
)
from .targeting_result import SpatialMetadata, TargetingResult
from .unit_conversion import meters_to_cells
from .visibility import can_target_in_combat

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
    """Map a visibility failure code to a canonical diagnostic reason."""
    if reason == "no_line_of_sight":
        return NO_LINE_OF_SIGHT
    return NOT_VISIBLE


def _log_diagnostics_debug(
    log: logging.Logger,
    intent: "ActionIntent",
    result: TargetingResult,
) -> None:
    """Emit a full diagnostics log line when COMBAT_DEBUG_TARGETING is enabled."""
    if not settings.combat_debug_targeting or result.diagnostics is None:
        return
    diag = result.diagnostics
    log.debug(
        "[targeting:debug] session=%s actor=%s target=%s valid=%s "
        "reasons=%s checks=%s meta=%s",
        intent.session_id,
        intent.actor_ref_id,
        getattr(intent, "requested_target_ref_id", None),
        diag.is_valid,
        diag.failure_reasons,
        diag.checks,
        diag.metadata,
    )


class CombatTargetingService(ABC):
    """Abstract interface for the spatial targeting authority.

    Implementors receive an ActionIntent and the current CombatState
    and return a TargetingResult that the mechanical resolution layer
    can trust.
    """

    @abstractmethod
    def validate(
        self,
        intent: ActionIntent,
        state: CombatState,
    ) -> TargetingResult:
        """Validate the spatial aspects of an action intent.

        Args:
            intent: The action the actor wants to perform.
            state:  Current combat state (participant list, etc.).

        Returns:
            TargetingResult with is_valid=True when the action may
            proceed, or is_valid=False with a failure_reason.
        """


class LocalCombatTargetingService(CombatTargetingService):
    """Default (local) implementation — no map, no distance validation.

    Behaviour
    ---------
    - Looks up the requested target in state.participants.
    - Confirms the target exists and its kind is resolved.
    - Returns a valid TargetingResult with a single affected target.
    - Does NOT validate distance, range, LoS or area geometry.

    This implementation preserves 100% of the current system behaviour
    while establishing the architectural boundary for future integration.
    """

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
                # Attacker not in participants — skip local visibility check.
                diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
                diag.set_check(CHECK_IS_VISIBLE, True)
        else:
            diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
            diag.set_check(CHECK_IS_VISIBLE, True)

        result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id=requested_ref_id,
            affected_target_ref_ids=[requested_ref_id],
            target_kind=target_kind,
            spatial_metadata=SpatialMetadata(targeting_authority="local"),
            diagnostics=diag,
        )
        _log_diagnostics_debug(logger, intent, result)
        return result


class LimiarMapTargetingService(CombatTargetingService):
    def __init__(
        self,
        limiar_map_client: LimiarMapClient,
        fallback_service: CombatTargetingService | None = None,
    ) -> None:
        self._limiar_map_client = limiar_map_client
        self._fallback_service = fallback_service or LocalCombatTargetingService()

    def validate(
        self,
        intent: ActionIntent,
        state: CombatState,
    ) -> TargetingResult:
        if isinstance(intent, AreaTargetingIntent):
            return self._validate_area(intent, state)

        local_result = self._fallback_service.validate(intent, state)
        if not local_result.is_valid:
            # Diagnostics from the local service are already attached.
            return local_result

        # Build a fresh diagnostics that inherits local checks.
        diag = TargetingDiagnostics()
        if local_result.diagnostics:
            for k, v in local_result.diagnostics.checks.items():
                diag.set_check(k, v)

        range_cells = self._derive_range_cells(intent)
        if range_cells is not None:
            diag.set_meta("range_cells", range_cells)

        requires_sight, requires_effect = self._resolve_single_target_requirements(
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
            # Return local result enriched with map metadata.
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
            canonical = self._map_reason_to_canonical(response.reason)
            diag.fail(canonical)
            self._populate_checks_from_map_failure(diag, response.reason)
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
                self._map_failure_reason(response.reason),
                diagnostics=diag,
            )
            _log_diagnostics_debug(logger, intent, result)
            return result

        # Map accepted the action — populate spatial checks from response.
        diag.set_check(CHECK_IN_RANGE, True)
        diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
        diag.set_check(CHECK_HAS_LINE_OF_EFFECT, True)
        if getattr(response, "cover", None):
            diag.set_meta("cover", response.cover)

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
            spatial_metadata=SpatialMetadata(
                source_token_id=response.source_token_id,
                target_token_id=response.target_token_id,
                map_version=response.version,
                targeting_authority="limiar_map",
                cover=response.cover,
            ),
            diagnostics=diag,
        )
        _log_diagnostics_debug(logger, intent, result)
        return result

    def _validate_area(
        self,
        intent: AreaTargetingIntent,
        state: CombatState,
    ) -> TargetingResult:
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
            origin_cell = intent.origin_cell or self._token_position_to_cell(
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
                anchor_cell = self._token_position_to_cell(anchor_token)
            if anchor_cell is None:
                return TargetingResult.invalid("Area anchor is missing.")

            # Convert meters → cells at the Control → Map boundary.
            # range_meters == 0 means self-origin (no range restriction) → send null to skip map check.
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
                requires_sight=self._resolve_area_requires_sight(intent),
                requires_effect=self._resolve_area_requires_effect(intent),
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
            return TargetingResult.invalid(self._map_failure_reason(response.reason))

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

    @staticmethod
    def _map_reason_to_canonical(reason: str | None) -> str:
        """Map a LimiarMap failure code to a canonical diagnostic reason."""
        if reason == "out_of_range":
            return TARGET_OUT_OF_REACH
        if reason == "no_line_of_sight":
            return NO_LINE_OF_SIGHT
        if reason in ("no_line_of_effect", "full_cover"):
            return NO_LINE_OF_EFFECT
        return TARGET_OUT_OF_REACH

    @staticmethod
    def _populate_checks_from_map_failure(
        diag: TargetingDiagnostics, reason: str | None
    ) -> None:
        """Set check flags based on the LimiarMap failure code."""
        if reason == "out_of_range":
            diag.set_check(CHECK_IN_RANGE, False)
            diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
            diag.set_check(CHECK_HAS_LINE_OF_EFFECT, True)
        elif reason == "no_line_of_sight":
            diag.set_check(CHECK_IN_RANGE, True)
            diag.set_check(CHECK_HAS_LINE_OF_SIGHT, False)
            diag.set_check(CHECK_HAS_LINE_OF_EFFECT, True)
        elif reason in ("no_line_of_effect", "full_cover"):
            diag.set_check(CHECK_IN_RANGE, True)
            diag.set_check(CHECK_HAS_LINE_OF_SIGHT, True)
            diag.set_check(CHECK_HAS_LINE_OF_EFFECT, False)
        else:
            diag.set_check(CHECK_IN_RANGE, False)
            diag.set_check(CHECK_HAS_LINE_OF_SIGHT, False)
            diag.set_check(CHECK_HAS_LINE_OF_EFFECT, False)

    @staticmethod
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

    @staticmethod
    def _token_position_to_cell(token: object) -> dict[str, int] | None:
        position_x = getattr(token, "position_x", None)
        position_y = getattr(token, "position_y", None)
        if not isinstance(position_x, int) or not isinstance(position_y, int):
            return None
        return {"x": position_x, "y": position_y}

    @staticmethod
    def _derive_range_cells(intent: ActionIntent) -> int | None:
        """Derive the maximum allowed distance in grid cells.

        Melee reach is resolved in cells directly via the centralized
        reach module.  Ranged weapons and spells convert from meters at
        the boundary.

        Returns None when no range constraint applies.
        """
        if isinstance(intent, SpellCastIntent):
            if isinstance(intent.range_meters, int) and intent.range_meters > 0:
                return meters_to_cells(intent.range_meters)
            return None

        if isinstance(intent.range_meters, int) and intent.range_meters > 0:
            return meters_to_cells(intent.range_meters)

        weapon_range_type = (intent.weapon_range_type or "").strip().lower()
        if weapon_range_type == "melee":
            return resolve_melee_reach_cells(has_reach=intent.has_reach)

        return None

    @staticmethod
    def _resolve_single_target_requirements(
        intent: WeaponAttackIntent | SpellCastIntent,
    ) -> tuple[bool, bool]:
        if isinstance(intent, WeaponAttackIntent):
            resolved = resolve_weapon_targeting_requirements(
                requires_target_sight=intent.requires_sight
                if isinstance(intent.requires_sight, bool)
                else None,
                requires_target_effect=intent.requires_effect
                if isinstance(intent.requires_effect, bool)
                else None,
            )
            return resolved.requires_target_sight, resolved.requires_target_effect

        resolved = resolve_spell_targeting_requirements(
            {
                "target_mode": intent.target_mode,
                "spell_mode": intent.spell_mode,
                "requires_target_sight": intent.requires_sight
                if isinstance(intent.requires_sight, bool)
                else None,
                "requires_target_effect": intent.requires_effect
                if isinstance(intent.requires_effect, bool)
                else None,
            },
            spell_mode=intent.spell_mode,
        )
        return resolved.requires_target_sight, resolved.requires_target_effect

    @staticmethod
    def _resolve_area_requires_sight(intent: AreaTargetingIntent) -> bool:
        resolved = resolve_spell_targeting_requirements(
            {
                "target_mode": intent.target_mode,
                "spell_mode": intent.spell_mode,
                "requires_point_sight": intent.requires_sight
                if isinstance(intent.requires_sight, bool)
                else None,
            },
            spell_mode=intent.spell_mode,
        )
        return resolved.requires_point_sight

    @staticmethod
    def _resolve_area_requires_effect(intent: AreaTargetingIntent) -> bool:
        resolved = resolve_spell_targeting_requirements(
            {
                "target_mode": intent.target_mode,
                "spell_mode": intent.spell_mode,
                "requires_point_effect": intent.requires_effect
                if isinstance(intent.requires_effect, bool)
                else None,
            },
            spell_mode=intent.spell_mode,
        )
        return resolved.requires_point_effect


# ---------------------------------------------------------------------------
# Module-level singleton — swap this to change the active implementation.
# ---------------------------------------------------------------------------

_targeting_service: CombatTargetingService | None = None
_targeting_service_signature: tuple[bool, str, float] | None = None


def reset_combat_targeting_service() -> None:
    global _targeting_service, _targeting_service_signature
    _targeting_service = None
    _targeting_service_signature = None


def _build_targeting_service() -> CombatTargetingService:
    if not settings.limiar_map_enabled:
        logger.info(
            "Combat targeting service using LocalCombatTargetingService (LIMIAR_MAP_ENABLED=false)"
        )
        return LocalCombatTargetingService()

    logger.info(
        "Combat targeting service using LimiarMapTargetingService base_url=%s timeout_seconds=%s",
        settings.limiar_map_base_url,
        settings.limiar_map_timeout_seconds,
    )
    return LimiarMapTargetingService(
        LimiarMapClient(
            base_url=settings.limiar_map_base_url,
            timeout_seconds=settings.limiar_map_timeout_seconds,
        ),
        fallback_service=LocalCombatTargetingService(),
    )


def get_combat_targeting_service() -> CombatTargetingService:
    """Return the active CombatTargetingService implementation.

    Replace the module-level _targeting_service instance (or override this
    function) to plug in the LimiarMap adapter without touching any caller.
    """
    global _targeting_service, _targeting_service_signature
    signature = (
        settings.limiar_map_enabled,
        settings.limiar_map_base_url,
        settings.limiar_map_timeout_seconds,
    )
    if _targeting_service is None or _targeting_service_signature != signature:
        _targeting_service = _build_targeting_service()
        _targeting_service_signature = signature
    return _targeting_service
