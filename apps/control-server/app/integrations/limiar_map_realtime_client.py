from __future__ import annotations

from dataclasses import dataclass, field
import logging
from threading import RLock
from time import monotonic
from typing import Any, Callable, Protocol

from app.core.config import settings

from .limiar_map_client import (
    LimiarMapClient,
    LimiarMapStateResponse,
)

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


class LimiarMapRealtimeSyncService:
    def __init__(
        self,
        *,
        http_client: LimiarMapClient,
        realtime_client: SpatialEventStream | None = None,
        now_provider: Callable[[], float] | None = None,
    ) -> None:
        self._http_client = http_client
        self._sessions: dict[str, LimiarMapSessionSyncState] = {}
        self._lock = RLock()
        self._now_provider = now_provider or monotonic

        if realtime_client is None:
            try:
                from .limiar_map_centrifugo_client import (
                    MAP_SYSTEM_EVENTS_CHANNEL,
                    LimiarMapCentrifugoClient,
                )
            except ModuleNotFoundError:
                logger.warning(
                    "LimiarMap realtime stream disabled because centrifuge-python is not installed"
                )
                self._realtime_client = _NoopSpatialEventStream()
            else:
                self._realtime_client = LimiarMapCentrifugoClient(
                    ws_url=settings.centrifugo_public_url,
                    event_handler=self.handle_event,
                    channels=(MAP_SYSTEM_EVENTS_CHANNEL,),
                )
        else:
            self._realtime_client = realtime_client

    def start(self) -> None:
        self._realtime_client.start()

    def stop(self) -> None:
        self._realtime_client.stop()

    def handle_event(self, event_name: str, payload: dict[str, Any]) -> None:
        parsed = self._parse_event_envelope(event_name, payload)
        if parsed is None:
            return

        logger.info(
            "LimiarMap realtime event received event=%s session_id=%s version=%s",
            event_name,
            parsed.session_id,
            parsed.version,
        )

        drift_reason: str | None = None
        with self._lock:
            session_state = self._sessions.setdefault(
                parsed.session_id,
                LimiarMapSessionSyncState(session_id=parsed.session_id),
            )
            session_state.last_event_at = self._now_provider()
            if not self._apply_version_progression(
                session_state,
                event_name,
                parsed.version,
            ):
                drift_reason = session_state.drift_reason
            else:
                self._apply_event_payload(session_state, event_name, parsed)
                if session_state.out_of_sync:
                    drift_reason = session_state.drift_reason
            should_trigger_auto_resync = bool(drift_reason)
        if should_trigger_auto_resync and drift_reason is not None:
            self.trigger_resync_if_needed(
                parsed.session_id,
                reason=drift_reason,
                version=parsed.version,
            )

    def resync_session(
        self,
        session_id: str,
        *,
        reason: str = "manual",
        automatic: bool = False,
    ) -> LimiarMapSessionSyncState | None:
        now = self._now_provider()
        with self._lock:
            session_state = self._sessions.setdefault(
                session_id,
                LimiarMapSessionSyncState(session_id=session_id),
            )
            if session_state.resync_in_progress:
                logger.info(
                    "LimiarMap resync suppressed session_id=%s reason=%s because another resync is in progress",
                    session_id,
                    reason,
                )
                return self.get_session_state(session_id)
            if automatic and not self._can_attempt_auto_resync(
                session_state,
                reason=reason,
                now=now,
            ):
                return self.get_session_state(session_id)
            session_state.resync_in_progress = True
            session_state.last_resync_at = now
            session_state.last_resync_reason = reason

        logger.info(
            "LimiarMap resync started session_id=%s reason=%s automatic=%s",
            session_id,
            reason,
            automatic,
        )
        try:
            snapshot = self._http_client.get_session_state(session_id)
        except Exception as exc:
            with self._lock:
                session_state = self._sessions.setdefault(
                    session_id,
                    LimiarMapSessionSyncState(session_id=session_id),
                )
                session_state.resync_in_progress = False
                session_state.consecutive_resync_failures += 1
                session_state.out_of_sync = True
                if session_state.drift_reason is None:
                    session_state.drift_reason = reason
                failure_count = session_state.consecutive_resync_failures
            logger.warning(
                "LimiarMap resync failed session_id=%s reason=%s automatic=%s failures=%s error=%s",
                session_id,
                reason,
                automatic,
                failure_count,
                exc,
            )
            if automatic and failure_count >= _MAX_CONSECUTIVE_AUTO_RESYNC_FAILURES:
                logger.warning(
                    "LimiarMap session remains out of sync after repeated auto-resync failures "
                    "session_id=%s failures=%s reason=%s",
                    session_id,
                    failure_count,
                    reason,
                )
            return None

        with self._lock:
            session_state = self._sessions.setdefault(
                session_id,
                LimiarMapSessionSyncState(session_id=session_id),
            )
            self._hydrate_session_from_snapshot(session_state, snapshot)
            session_state.out_of_sync = False
            session_state.drift_reason = None
            session_state.resync_in_progress = False
            session_state.consecutive_resync_failures = 0

        logger.info(
            "LimiarMap resync succeeded session_id=%s reason=%s automatic=%s version=%s",
            session_id,
            reason,
            automatic,
            snapshot.version,
        )
        return self.get_session_state(session_id)

    def trigger_resync_if_needed(
        self,
        session_id: str,
        *,
        reason: str,
        version: int | None = None,
    ) -> LimiarMapSessionSyncState | None:
        if reason not in _AUTO_RESYNC_ELIGIBLE_REASONS:
            logger.info(
                "LimiarMap auto-resync not eligible session_id=%s reason=%s version=%s",
                session_id,
                reason,
                version,
            )
            return self.get_session_state(session_id)

        logger.info(
            "LimiarMap auto-resync eligible session_id=%s reason=%s version=%s",
            session_id,
            reason,
            version,
        )
        return self.resync_session(
            session_id,
            reason=reason,
            automatic=True,
        )

    def get_session_state(self, session_id: str) -> LimiarMapSessionSyncState | None:
        with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                return None
            return LimiarMapSessionSyncState(
                session_id=state.session_id,
                last_known_map_version=state.last_known_map_version,
                token_positions=dict(state.token_positions),
                last_active_combatant_id=state.last_active_combatant_id,
                out_of_sync=state.out_of_sync,
                drift_reason=state.drift_reason,
                last_resync_at=state.last_resync_at,
                last_resync_reason=state.last_resync_reason,
                resync_in_progress=state.resync_in_progress,
                consecutive_resync_failures=state.consecutive_resync_failures,
                last_event_at=state.last_event_at,
            )

    def is_out_of_sync(self, session_id: str) -> bool:
        state = self.get_session_state(session_id)
        return bool(state.out_of_sync) if state is not None else False

    def _apply_version_progression(
        self,
        session_state: LimiarMapSessionSyncState,
        event_name: str,
        version: int,
    ) -> bool:
        last_version = session_state.last_known_map_version
        if last_version is not None and version < last_version:
            self._mark_drift(
                session_state,
                reason="event_out_of_order",
                event_name=event_name,
                version=version,
            )
            return False
        if last_version is not None and version > last_version + 1:
            self._mark_drift(
                session_state,
                reason="version_gap",
                event_name=event_name,
                version=version,
            )
        session_state.last_known_map_version = version
        return True

    def _apply_event_payload(
        self,
        session_state: LimiarMapSessionSyncState,
        event_name: str,
        parsed: "_ParsedRealtimeEvent",
    ) -> None:
        payload = parsed.payload

        if event_name == "movement.applied":
            token_id = payload.get("tokenId")
            position = payload.get("position")
            if not isinstance(token_id, str) or not isinstance(position, dict):
                self._mark_drift(
                    session_state,
                    reason="invalid_movement_payload",
                    event_name=event_name,
                    version=parsed.version,
                )
                return
            x = position.get("x")
            y = position.get("y")
            if not isinstance(x, int) or not isinstance(y, int):
                self._mark_drift(
                    session_state,
                    reason="invalid_movement_payload",
                    event_name=event_name,
                    version=parsed.version,
                )
                return
            existing = session_state.token_positions.get(token_id)
            if existing is None and session_state.token_positions:
                self._mark_drift(
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
                self._mark_drift(
                    session_state,
                    reason="invalid_tokens_payload",
                    event_name=event_name,
                    version=parsed.version,
                )
                return
            next_positions: dict[str, LimiarMapTokenPositionState] = {}
            for token in tokens:
                if not isinstance(token, dict):
                    self._mark_drift(
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
                    self._mark_drift(
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
                self._mark_drift(
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
                self._mark_drift(
                    session_state,
                    reason="control_action_rejected",
                    event_name=event_name,
                    version=parsed.version,
                )
            return

        if event_name == "targeting.resolved":
            return

    def _hydrate_session_from_snapshot(
        self,
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

    def _mark_drift(
        self,
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

    def _can_attempt_auto_resync(
        self,
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

    @staticmethod
    def _parse_event_envelope(
        event_name: str,
        payload: dict[str, Any],
    ) -> "_ParsedRealtimeEvent | None":
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


@dataclass(frozen=True)
class _ParsedRealtimeEvent:
    session_id: str
    version: int
    action_id: str | None
    payload: dict[str, Any]


_realtime_sync_service: LimiarMapRealtimeSyncService | None = None
_realtime_sync_service_signature: tuple[bool, str, float, str] | None = None


def reset_limiar_map_realtime_sync_service() -> None:
    global _realtime_sync_service, _realtime_sync_service_signature
    if _realtime_sync_service is not None:
        _realtime_sync_service.stop()
    _realtime_sync_service = None
    _realtime_sync_service_signature = None


def get_limiar_map_realtime_sync_service() -> LimiarMapRealtimeSyncService:
    global _realtime_sync_service, _realtime_sync_service_signature
    signature = (
        settings.limiar_map_base_url,
        settings.limiar_map_timeout_seconds,
        settings.centrifugo_public_url,
    )
    if _realtime_sync_service is None or _realtime_sync_service_signature != signature:
        if _realtime_sync_service is not None:
            _realtime_sync_service.stop()
        _realtime_sync_service = LimiarMapRealtimeSyncService(
            http_client=LimiarMapClient(
                base_url=settings.limiar_map_base_url,
                timeout_seconds=settings.limiar_map_timeout_seconds,
            )
        )
        _realtime_sync_service_signature = signature
    return _realtime_sync_service


def start_limiar_map_realtime_sync() -> None:
    get_limiar_map_realtime_sync_service().start()


def stop_limiar_map_realtime_sync() -> None:
    if _realtime_sync_service is None:
        return
    _realtime_sync_service.stop()


def resync_limiar_map_session(
    session_id: str,
) -> LimiarMapSessionSyncState | None:
    return get_limiar_map_realtime_sync_service().resync_session(session_id)


def trigger_limiar_map_resync_if_needed(
    session_id: str,
    *,
    reason: str,
    version: int | None = None,
) -> LimiarMapSessionSyncState | None:
    return get_limiar_map_realtime_sync_service().trigger_resync_if_needed(
        session_id,
        reason=reason,
        version=version,
    )
