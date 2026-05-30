from __future__ import annotations

import logging

from app.integrations.limiar_map_client import (
    LimiarMapClientError,
    LimiarMapStateResponse,
)
from app.models.combat import CombatState

logger = logging.getLogger(__name__)


def _sync_existing_map_turn(
    limiar_map_client,
    session_id: str,
    state: CombatState,
    map_state: LimiarMapStateResponse | None,
) -> str | None:
    from .limiar_map_projection_payloads import _build_initiative_order

    desired_order = _build_initiative_order(state)
    if not desired_order:
        return None

    if map_state is None:
        try:
            map_state = limiar_map_client.get_state(session_id)
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap turn catch-up preflight failed for session_id=%s desired_round=%s "
                "desired_turn_index=%s (%s)",
                session_id,
                state.round,
                state.current_turn_index,
                exc,
            )
            return "turn_sync_state_unavailable"
    if map_state is None:
        return "turn_sync_state_unavailable"

    if map_state.initiative_order and tuple(desired_order) != tuple(
        map_state.initiative_order
    ):
        logger.info(
            "LimiarMap turn catch-up skipped for session_id=%s because initiative order differs "
            "control=%s map=%s",
            session_id,
            desired_order,
            list(map_state.initiative_order),
        )
        return "turn_sync_order_mismatch"

    current_round = map_state.round_number
    current_turn_index = map_state.turn_index
    if (
        not isinstance(current_round, int)
        or current_round < 1
        or not isinstance(current_turn_index, int)
        or current_turn_index < 0
        or current_turn_index >= len(desired_order)
    ):
        if map_state.active_combatant_id in desired_order:
            current_round = 1
            current_turn_index = desired_order.index(map_state.active_combatant_id)
        else:
            logger.info(
                "LimiarMap turn catch-up skipped for session_id=%s because current turn state is incomplete "
                "active=%s round=%s turn_index=%s",
                session_id,
                map_state.active_combatant_id,
                map_state.round_number,
                map_state.turn_index,
            )
            return "turn_sync_state_incomplete"

    desired_round = state.round if state.round > 0 else 1
    desired_turn_index = state.current_turn_index
    if desired_turn_index < 0 or desired_turn_index >= len(desired_order):
        return None

    current_abs = ((current_round - 1) * len(desired_order)) + current_turn_index
    desired_abs = ((desired_round - 1) * len(desired_order)) + desired_turn_index
    if desired_abs <= current_abs:
        return None

    logger.info(
        "LimiarMap turn catch-up started for session_id=%s current=(round=%s turn=%s active=%s) "
        "desired=(round=%s turn=%s active=%s) steps=%s",
        session_id,
        current_round,
        current_turn_index,
        map_state.active_combatant_id,
        desired_round,
        desired_turn_index,
        desired_order[desired_turn_index],
        desired_abs - current_abs,
    )

    for absolute_step in range(current_abs + 1, desired_abs + 1):
        target_round = (absolute_step // len(desired_order)) + 1
        target_turn_index = absolute_step % len(desired_order)
        action_id = (
            f"control-combat-advance:{state.id}:{target_round}:{target_turn_index}"
        )
        try:
            limiar_map_client.advance_combat(
                session_id,
                {
                    "actionId": action_id,
                },
            )
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap turn catch-up failed for session_id=%s action_id=%s "
                "target_round=%s target_turn_index=%s (%s)",
                session_id,
                action_id,
                target_round,
                target_turn_index,
                exc,
            )
            return "turn_sync_failed"

    logger.info(
        "LimiarMap turn catch-up succeeded for session_id=%s desired_round=%s desired_turn_index=%s",
        session_id,
        desired_round,
        desired_turn_index,
    )
    return "turn_synced"
