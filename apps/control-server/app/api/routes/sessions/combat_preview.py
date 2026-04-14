"""Tactical preview endpoint — dry-run targeting validation.

POST /sessions/{session_id}/combat/preview

Validates a targeting intent without mutating any combat state.
Used by the map-web tactical preview layer so players can see reach,
target validity, failure reasons, and AoE footprints before committing.

Design constraints:
- Read-only: no state mutations, no realtime events published
- Returns TargetingDiagnostics serialised as JSON
- Delegates to get_combat_targeting_service() so that LimiarMap LoS/LoE/range
  validation is used automatically when the integration is active
- AoE footprints come from LimiarMap /targeting/area/preview — the read-only
  variant of the same spatial engine used for the final cast, so the cells
  shown here are guaranteed to match the actual resolution
- Positions come from the frontend (map-web owns spatial authority).
  Chebyshev is used as a local supplement when LimiarMap is offline/disabled.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_session
from app.integrations.limiar_map_client import LimiarMapClient, LimiarMapClientError
from app.models.combat import CombatState
from app.models.session import Session
from app.schemas.combat_preview import (
    CombatPreviewRequest,
    CombatPreviewResponse,
    PreviewPosition,
    TacticalDiagnosticsPayload,
)
from app.services.combat_service.combat_targeting import get_combat_targeting_service
from app.services.combat_service.targeting_diagnostics import (
    CHECK_IN_RANGE,
    TARGET_OUT_OF_REACH,
    TargetingDiagnostics,
)
from app.services.combat_service.targeting_intent import (
    SpellCastIntent,
    WeaponAttackIntent,
)
from app.services.combat_service.unit_conversion import METERS_PER_CELL

logger = logging.getLogger(__name__)

router = APIRouter()


def _chebyshev(a: PreviewPosition, b: PreviewPosition) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


def _to_payload(diag: TargetingDiagnostics) -> TacticalDiagnosticsPayload:
    return TacticalDiagnosticsPayload(
        isValid=diag.is_valid,
        failureReasons=diag.failure_reasons,
        checks=diag.checks,
        metadata=diag.metadata,
    )


def _reach_to_range_meters(reach_cells: int) -> int:
    """Convert a reach expressed in grid cells to the nearest integer meter value.

    The round-trip ``meters_to_cells(reach_to_range_meters(n)) == n`` holds for
    all integer values of *n* between 1 and 60 at the default 1.5 m/cell scale.
    """
    return round(reach_cells * METERS_PER_CELL)


@router.post(
    "/sessions/{session_id}/combat/preview",
    response_model=CombatPreviewResponse,
)
def combat_preview(
    session_id: str,
    payload: CombatPreviewRequest,
    user=Depends(get_current_user),
    db: DbSession = Depends(get_session),
) -> CombatPreviewResponse:
    """Dry-run targeting validation for tactical preview.

    Two mutually exclusive validation paths:

    **AoE path** (``aoe_shape`` + ``aoe_size_cells`` set):
      Calls LimiarMap ``/targeting/area/preview`` — the read-only variant of
      the same spatial engine used for the final cast.  The cells returned here
      are guaranteed to match the actual AoE resolution because both paths use
      the same computation, only differing in side effects.

    **Single-target path** (``target_ref_id`` set, no AoE fields):
      Delegates to ``get_combat_targeting_service()`` so that LimiarMap
      LoS/LoE/range checks are included when the integration is enabled.
      When LimiarMap is offline or disabled, entity-level checks (target found,
      kind valid, visibility) run locally, and Chebyshev distance from the
      frontend-provided positions is used as a range supplement.
    """
    entry = db.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")

    reach = payload.reach_cells

    # ── AoE path ─────────────────────────────────────────────────────────────
    # AoE takes priority: when shape + size are provided we skip entity-level
    # diagnostics and return only the spatial footprint.
    if (
        payload.aoe_shape is not None
        and payload.aoe_size_cells is not None
        and payload.source_position is not None
        and payload.target_position is not None
    ):
        return _handle_aoe_preview(session_id, payload, reach)

    # ── Reach-only path ───────────────────────────────────────────────────────
    if not payload.target_ref_id:
        return CombatPreviewResponse(effectiveReachCells=reach)

    # ── Single-target path ────────────────────────────────────────────────────
    combat_state = db.exec(
        select(CombatState).where(CombatState.session_id == session_id)
    ).first()
    if not combat_state:
        return CombatPreviewResponse(effectiveReachCells=reach)

    actor_participant = next(
        (p for p in combat_state.participants if p.get("ref_id") == payload.source_ref_id),
        None,
    )
    actor_kind = (actor_participant.get("kind") or "player") if actor_participant else "player"

    range_meters = _reach_to_range_meters(reach)

    if payload.action_type == "spell":
        intent = SpellCastIntent(
            session_id=session_id,
            action_id="preview",
            actor_ref_id=payload.source_ref_id,
            actor_kind=actor_kind,
            requested_target_ref_id=payload.target_ref_id,
            spell_canonical_key="preview",
            spell_mode="spell_attack",
            range_meters=range_meters,
            requires_sight=True,
            requires_effect=True,
        )
    else:
        intent = WeaponAttackIntent(
            session_id=session_id,
            action_id="preview",
            actor_ref_id=payload.source_ref_id,
            actor_kind=actor_kind,
            requested_target_ref_id=payload.target_ref_id,
            range_meters=range_meters,
            requires_sight=True,
            requires_effect=True,
        )

    targeting_service = get_combat_targeting_service(combat_state.use_map)
    result = targeting_service.validate(intent, combat_state)

    diag: TargetingDiagnostics = result.diagnostics or TargetingDiagnostics()

    if payload.source_position and payload.target_position:
        distance = _chebyshev(payload.source_position, payload.target_position)
        diag.set_meta("reach_cells", reach)
        if "distance_cells" not in diag.metadata:
            diag.set_meta("distance_cells", distance)

        if CHECK_IN_RANGE not in diag.checks:
            in_range = distance <= reach
            diag.set_check(CHECK_IN_RANGE, in_range)
            if not in_range and diag.is_valid:
                diag.fail(TARGET_OUT_OF_REACH)
                logger.debug(
                    "[preview] local range check failed session=%s distance=%d reach=%d",
                    session_id,
                    distance,
                    reach,
                )

    return CombatPreviewResponse(
        diagnostics=_to_payload(diag),
        effectiveReachCells=reach,
    )


def _handle_aoe_preview(
    session_id: str,
    payload: CombatPreviewRequest,
    reach: int,
) -> CombatPreviewResponse:
    """Call LimiarMap /targeting/area/preview to compute the AoE footprint.

    This is the read-only variant of the same spatial engine used by
    LimiarMapTargetingService._validate_area() during the final cast.
    Both paths receive identical parameters (shape, origin_cell, anchor_cell,
    range_cells, size_cells, requires_sight, requires_effect), so the cells
    returned here will match the actual AoE resolution exactly.

    Graceful degradation: if LimiarMap is disabled or unreachable, returns
    an empty ``aoeCells`` list rather than failing the request.
    """
    # payload.aoe_shape, aoe_size_cells, source_position, target_position
    # are all guaranteed non-None by the caller guard.
    assert payload.aoe_shape is not None
    assert payload.aoe_size_cells is not None
    assert payload.source_position is not None
    assert payload.target_position is not None

    if not combat_state.use_map:
        logger.debug("[preview] AoE preview skipped — combat opened without map session=%s", session_id)
        return CombatPreviewResponse(effectiveReachCells=reach)

    try:
        client = LimiarMapClient(
            base_url=settings.limiar_map_base_url,
            timeout_seconds=settings.limiar_map_timeout_seconds,
        )
        response = client.preview_area_targeting(
            session_id=session_id,
            action_id="preview",
            combatant_id=payload.source_ref_id,
            shape=payload.aoe_shape,
            origin_cell={"x": payload.source_position.x, "y": payload.source_position.y},
            anchor_cell={"x": payload.target_position.x, "y": payload.target_position.y},
            range_cells=reach,
            size_cells=payload.aoe_size_cells,
            requires_sight=True,
            requires_effect=True,
        )
    except LimiarMapClientError as exc:
        logger.warning(
            "[preview] AoE preview failed session=%s shape=%s: %s",
            session_id,
            payload.aoe_shape,
            exc,
        )
        return CombatPreviewResponse(effectiveReachCells=reach)

    return CombatPreviewResponse(
        effectiveReachCells=reach,
        aoeCells=[
            PreviewPosition(x=cell.x, y=cell.y)
            for cell in response.affected_cells
        ],
    )
