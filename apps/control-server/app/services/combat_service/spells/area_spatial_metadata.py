"""Shared helpers for per-target spatial metadata in area spells.

Used by both the preview path (area_targeting.py) and the cast path
(cast_area.py) so that cover lookup and DC calculation are never
duplicated between the two flows.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.integrations.limiar_map_client_types import LimiarMapClientError

from ..cover_modifiers import resolve_cover_save_dc

if TYPE_CHECKING:
    from app.integrations.limiar_map_client import LimiarMapClient

logger = logging.getLogger(__name__)


def get_area_per_target_cover(
    *,
    client: "LimiarMapClient",
    session_id: str,
    action_id: str,
    actor_ref_id: str,
    target_ref_ids: list[str],
) -> dict[str, str | None]:
    """Return cover from actor position to each area target.

    Each entry maps target_ref_id → cover level (or None when the lookup
    fails). Failures are isolated per-target so that one bad lookup never
    blocks the others.

    Prefers a single batch call when the client supports it; falls back to
    per-target individual calls otherwise or on batch failure.

    Callers are responsible for skipping this function when the map is
    unavailable or cover does not apply to the save.
    """
    if not target_ref_ids:
        return {}

    unique_ref_ids = list(dict.fromkeys(target_ref_ids))

    if hasattr(client, "validate_targets_batch"):
        try:
            return _cover_via_batch(
                client=client,
                session_id=session_id,
                action_id=action_id,
                actor_ref_id=actor_ref_id,
                unique_ref_ids=unique_ref_ids,
            )
        except LimiarMapClientError as exc:
            logger.warning(
                "Batch cover lookup failed for session_id=%s (%s); "
                "falling back to per-target individual lookups",
                session_id,
                exc,
            )

    return _cover_via_individual(
        client=client,
        session_id=session_id,
        action_id=action_id,
        actor_ref_id=actor_ref_id,
        unique_ref_ids=unique_ref_ids,
    )


def _cover_via_batch(
    *,
    client: "LimiarMapClient",
    session_id: str,
    action_id: str,
    actor_ref_id: str,
    unique_ref_ids: list[str],
) -> dict[str, str | None]:
    response = client.validate_targets_batch(
        session_id=session_id,
        action_id=action_id,
        combatant_id=actor_ref_id,
        target_combatant_ids=unique_ref_ids,
    )
    result: dict[str, str | None] = {}
    for item in response.results:
        result[item.target_combatant_id] = item.cover

    for ref_id in unique_ref_ids:
        if ref_id not in result:
            logger.warning(
                "Batch cover response missing target_ref_id=%s session_id=%s; "
                "using None (base DC)",
                ref_id,
                session_id,
            )
            result[ref_id] = None

    return result


def _cover_via_individual(
    *,
    client: "LimiarMapClient",
    session_id: str,
    action_id: str,
    actor_ref_id: str,
    unique_ref_ids: list[str],
) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for target_ref_id in unique_ref_ids:
        try:
            response = client.validate_single_target(
                session_id=session_id,
                action_id=f"{action_id}:cover:{target_ref_id}",
                combatant_id=actor_ref_id,
                target_combatant_id=target_ref_id,
                range_cells=None,
                requires_sight=False,
                requires_effect=False,
            )
            result[target_ref_id] = response.cover
        except LimiarMapClientError as exc:
            logger.warning(
                "Cover lookup failed for area target session_id=%s "
                "target_ref_id=%s (%s); falling back to base DC",
                session_id,
                target_ref_id,
                exc,
            )
            result[target_ref_id] = None
    return result


def build_area_affected_target_spatial_metadata(
    *,
    affected_ref_ids: list[str],
    name_by_ref: dict[str, str | None],
    cover_by_ref: dict[str, str | None],
    base_save_dc: int,
    cover_applies_to_save: str | None,
) -> list[dict]:
    """Build per-target spatial metadata dicts for area preview/cast results.

    Returns a list ordered by affected_ref_ids. Each entry contains:
        target_ref_id, target_display_name, cover,
        base_save_dc, effective_save_dc, cover_modifier.

    resolve_cover_save_dc is the single source of truth for DC calculation.
    """
    metadata = []
    for ref_id in affected_ref_ids:
        cover = cover_by_ref.get(ref_id)
        effective_dc, modifier = resolve_cover_save_dc(
            base_save_dc,
            cover,
            cover_applies_to_save,
        )
        metadata.append(
            {
                "target_ref_id": ref_id,
                "target_display_name": name_by_ref.get(ref_id),
                "cover": cover,
                "base_save_dc": base_save_dc,
                "effective_save_dc": effective_dc,
                "cover_modifier": modifier,
            }
        )
    return metadata
