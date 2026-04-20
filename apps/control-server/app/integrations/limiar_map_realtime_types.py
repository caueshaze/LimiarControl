from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Protocol

from .limiar_map_client_types import LimiarMapStateResponse

logger = logging.getLogger(__name__)


class SpatialEventStream(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...


class _NoopSpatialEventStream:
    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


_AUTO_RESYNC_ELIGIBLE_REASONS = frozenset(
    {
        "version_gap",
        "event_out_of_order",
        "invalid_movement_payload",
        "invalid_tokens_payload",
        "invalid_combat_payload",
        "unknown_token_movement",
    }
)
_AUTO_RESYNC_COOLDOWN_SECONDS = 5.0
_MAX_CONSECUTIVE_AUTO_RESYNC_FAILURES = 3


@dataclass(frozen=True)
class LimiarMapTokenPositionState:
    token_id: str
    position_x: int | None = None
    position_y: int | None = None
    combatant_id: str | None = None


@dataclass
class LimiarMapSessionSyncState:
    session_id: str
    last_known_map_version: int | None = None
    token_positions: dict[str, LimiarMapTokenPositionState] = field(default_factory=dict)
    last_active_combatant_id: str | None = None
    out_of_sync: bool = False
    drift_reason: str | None = None
    last_resync_at: float | None = None
    last_resync_reason: str | None = None
    resync_in_progress: bool = False
    consecutive_resync_failures: int = 0
    last_event_at: float | None = None


@dataclass(frozen=True)
class _ParsedRealtimeEvent:
    session_id: str
    version: int
    action_id: str | None
    payload: dict[str, Any]


def mark_drift(
    session_state: LimiarMapSessionSyncState,
    *,
    reason: str,
    event_name: str,
    version: int,
) -> None:
    session_state.out_of_sync = True
    session_state.drift_reason = reason
    logger.warning(
        "LimiarMap drift detected session_id=%s event=%s version=%s reason=%s last_known_map_version=%s",
        session_state.session_id,
        event_name,
        version,
        reason,
        session_state.last_known_map_version,
    )


def parse_event_envelope(
    event_name: str,
    payload: dict[str, Any],
) -> _ParsedRealtimeEvent | None:
    session_id = payload.get("encounterId")
    version = payload.get("version")
    action_id = payload.get("actionId")
    event_payload = payload.get("payload")

    if not isinstance(session_id, str) or not session_id.strip():
        logger.warning(
            "LimiarMap realtime ignored event=%s because encounterId is invalid",
            event_name,
        )
        return None
    if not isinstance(version, int):
        logger.warning(
            "LimiarMap realtime ignored event=%s session_id=%s because version is invalid",
            event_name,
            session_id,
        )
        return None
    if action_id is not None and not isinstance(action_id, str):
        logger.warning(
            "LimiarMap realtime ignored event=%s session_id=%s because actionId is invalid",
            event_name,
            session_id,
        )
        return None
    if event_payload is None:
        event_payload = {}
    if not isinstance(event_payload, dict):
        logger.warning(
            "LimiarMap realtime ignored event=%s session_id=%s because payload is invalid",
            event_name,
            session_id,
        )
        return None

    return _ParsedRealtimeEvent(
        session_id=session_id,
        version=version,
        action_id=action_id,
        payload=event_payload,
    )


def can_attempt_auto_resync(
    session_state: LimiarMapSessionSyncState,
    *,
    reason: str,
    now: float,
) -> bool:
    if session_state.resync_in_progress:
        logger.info(
            "LimiarMap auto-resync suppressed session_id=%s reason=%s because resync is already in progress",
            session_state.session_id,
            reason,
        )
        return False

    if (
        session_state.last_resync_at is not None
        and now - session_state.last_resync_at < _AUTO_RESYNC_COOLDOWN_SECONDS
    ):
        logger.info(
            "LimiarMap auto-resync suppressed session_id=%s reason=%s because cooldown is active "
            "cooldown_seconds=%s",
            session_state.session_id,
            reason,
            _AUTO_RESYNC_COOLDOWN_SECONDS,
        )
        return False

    if session_state.consecutive_resync_failures >= _MAX_CONSECUTIVE_AUTO_RESYNC_FAILURES:
        logger.warning(
            "LimiarMap auto-resync suppressed session_id=%s reason=%s because failure limit was reached "
            "failures=%s",
            session_state.session_id,
            reason,
            session_state.consecutive_resync_failures,
        )
        return False

    return True


def hydrate_session_from_snapshot(
    session_state: LimiarMapSessionSyncState,
    snapshot: LimiarMapStateResponse,
) -> None:
    session_state.last_known_map_version = snapshot.version
    session_state.last_active_combatant_id = snapshot.active_combatant_id
    session_state.token_positions = {
        token.token_id: LimiarMapTokenPositionState(
            token_id=token.token_id,
            position_x=token.position_x,
            position_y=token.position_y,
            combatant_id=token.combatant_id,
        )
        for token in snapshot.tokens
    }


def apply_event_payload(
    session_state: LimiarMapSessionSyncState,
    event_name: str,
    parsed: _ParsedRealtimeEvent,
) -> None:
    payload = parsed.payload

    if event_name == "movement.applied":
        token_id = payload.get("tokenId")
        position = payload.get("position")
        if not isinstance(token_id, str) or not isinstance(position, dict):
            mark_drift(
                session_state,
                reason="invalid_movement_payload",
                event_name=event_name,
                version=parsed.version,
            )
            return
        x = position.get("x")
        y = position.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            mark_drift(
                session_state,
                reason="invalid_movement_payload",
                event_name=event_name,
                version=parsed.version,
            )
            return
        existing = session_state.token_positions.get(token_id)
        if existing is None and session_state.token_positions:
            mark_drift(
                session_state,
                reason="unknown_token_movement",
                event_name=event_name,
                version=parsed.version,
            )
        session_state.token_positions[token_id] = LimiarMapTokenPositionState(
            token_id=token_id,
            position_x=x,
            position_y=y,
            combatant_id=existing.combatant_id if existing is not None else None,
        )
        return

    if event_name == "tokens.synced":
        tokens = payload.get("tokens")
        if not isinstance(tokens, list):
            mark_drift(
                session_state,
                reason="invalid_tokens_payload",
                event_name=event_name,
                version=parsed.version,
            )
            return
        next_positions: dict[str, LimiarMapTokenPositionState] = {}
        for token in tokens:
            if not isinstance(token, dict):
                mark_drift(
                    session_state,
                    reason="invalid_tokens_payload",
                    event_name=event_name,
                    version=parsed.version,
                )
                return
            token_id = token.get("id")
            position = token.get("position")
            combatant_id = token.get("combatantId")
            if not isinstance(token_id, str):
                mark_drift(
                    session_state,
                    reason="invalid_tokens_payload",
                    event_name=event_name,
                    version=parsed.version,
                )
                return
            x = y = None
            if isinstance(position, dict):
                raw_x = position.get("x")
                raw_y = position.get("y")
                if isinstance(raw_x, int) and isinstance(raw_y, int):
                    x = raw_x
                    y = raw_y
            next_positions[token_id] = LimiarMapTokenPositionState(
                token_id=token_id,
                position_x=x,
                position_y=y,
                combatant_id=combatant_id if isinstance(combatant_id, str) else None,
            )
        session_state.token_positions = next_positions
        return

    if event_name in ("combat.started", "combat.advanced"):
        active_combatant_id = payload.get("activeCombatantId")
        if active_combatant_id is not None and not isinstance(active_combatant_id, str):
            mark_drift(
                session_state,
                reason="invalid_combat_payload",
                event_name=event_name,
                version=parsed.version,
            )
            return
        session_state.last_active_combatant_id = active_combatant_id
        return

    if event_name == "combat.ended":
        session_state.last_active_combatant_id = None
        return

    if event_name == "action.rejected":
        if parsed.action_id and parsed.action_id.startswith("control-"):
            mark_drift(
                session_state,
                reason="control_action_rejected",
                event_name=event_name,
                version=parsed.version,
            )
        return

    if event_name == "targeting.resolved":
        return
