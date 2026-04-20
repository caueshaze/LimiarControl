from __future__ import annotations

import logging
from threading import RLock
from time import monotonic
from typing import Any, Callable

from app.core.config import settings

from .limiar_map_client import LimiarMapClient
from .limiar_map_realtime_types import (
    LimiarMapSessionSyncState,
    LimiarMapTokenPositionState,
    SpatialEventStream,
    _AUTO_RESYNC_ELIGIBLE_REASONS,
    _NoopSpatialEventStream,
    apply_event_payload,
    can_attempt_auto_resync,
    hydrate_session_from_snapshot,
    mark_drift,
    parse_event_envelope,
)

logger = logging.getLogger(__name__)


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
                    ws_url=settings.centrifugo_internal_ws_url,
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
        parsed = parse_event_envelope(event_name, payload)
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
                apply_event_payload(session_state, event_name, parsed)
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
            if automatic and not can_attempt_auto_resync(
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
            return None

        with self._lock:
            session_state = self._sessions.setdefault(
                session_id,
                LimiarMapSessionSyncState(session_id=session_id),
            )
            hydrate_session_from_snapshot(session_state, snapshot)
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
            mark_drift(
                session_state,
                reason="event_out_of_order",
                event_name=event_name,
                version=version,
            )
            return False
        if last_version is not None and version > last_version + 1:
            mark_drift(
                session_state,
                reason="version_gap",
                event_name=event_name,
                version=version,
            )
        session_state.last_known_map_version = version
        return True


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
        settings.limiar_map_enabled,
        settings.limiar_map_base_url,
        settings.limiar_map_timeout_seconds,
        settings.centrifugo_internal_ws_url,
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
    if not settings.limiar_map_enabled:
        return
    get_limiar_map_realtime_sync_service().start()


def stop_limiar_map_realtime_sync() -> None:
    if _realtime_sync_service is None:
        return
    _realtime_sync_service.stop()


def resync_limiar_map_session(
    session_id: str,
) -> LimiarMapSessionSyncState | None:
    if not settings.limiar_map_enabled:
        return None
    return get_limiar_map_realtime_sync_service().resync_session(session_id)


def trigger_limiar_map_resync_if_needed(
    session_id: str,
    *,
    reason: str,
    version: int | None = None,
) -> LimiarMapSessionSyncState | None:
    if not settings.limiar_map_enabled:
        return None
    return get_limiar_map_realtime_sync_service().trigger_resync_if_needed(
        session_id,
        reason=reason,
        version=version,
    )
