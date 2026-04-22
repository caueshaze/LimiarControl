from __future__ import annotations

from dataclasses import dataclass
import logging

from sqlmodel import Session

from app.core.config import settings
from app.integrations.limiar_map_client import (
    LimiarMapClient,
    LimiarMapClientError,
    LimiarMapStateResponse,
)
from app.models.combat import CombatPhase, CombatState
from .token_resolution import (
    build_sync_entries,
    ResolvedTokenSpawnEntry,
    ResolvedTokenSyncEntry,
    _extract_participant_conditions,
)
from .limiar_map_projection_payloads import (
    _build_initiative_order,
    _build_battle_map_payload,
    _build_combatants_payload,
)
from .limiar_map_projection_sync import _sync_existing_map_turn

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LimiarMapCombatProjectionResult:
    map_available: bool
    reason: str | None = None


class LimiarMapCombatProjectionService:
    def __init__(self, limiar_map_client: LimiarMapClient) -> None:
        self._limiar_map_client = limiar_map_client

    def project_combat_start(
        self,
        db: Session,
        session_id: str,
        state: CombatState,
    ) -> LimiarMapCombatProjectionResult:
        if state.phase not in (CombatPhase.active, CombatPhase.placement, "active", "placement"):
            return LimiarMapCombatProjectionResult(
                map_available=False,
                reason="combat_not_active",
            )

        combatants_payload = _build_combatants_payload(state)
        if not combatants_payload:
            logger.warning(
                "LimiarMap combat/start skipped for session_id=%s because no combatants could be resolved",
                session_id,
            )
            return LimiarMapCombatProjectionResult(
                map_available=False,
                reason="no_combatants",
            )

        action_id = self.build_combat_start_action_id(state)
        logger.info(
            "LimiarMap combat projection started for session_id=%s action_id=%s combatants=%s",
            session_id,
            action_id,
            len(combatants_payload),
        )
        battle_map_payload = _build_battle_map_payload(session_id, state)
        map_state: LimiarMapStateResponse | None = None
        latest_map_state: LimiarMapStateResponse | None = None

        try:
            map_state = self._limiar_map_client.get_state(session_id)
            latest_map_state = map_state
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap syncTokens preparation failed for session_id=%s action_id=%s; "
                "combat start will continue without token bootstrap (%s)",
                session_id,
                action_id,
                exc,
            )

        if map_state is not None:
            latest_map_state = self._bootstrap_tokens(
                db, session_id, action_id, state, map_state
            )

        logger.info(
            "LimiarMap combat/start started for session_id=%s action_id=%s combatants=%s",
            session_id, action_id, len(combatants_payload),
        )
        return self._issue_combat_start(
            session_id, action_id, state, combatants_payload,
            battle_map_payload, latest_map_state,
        )

    def _issue_combat_start(
        self,
        session_id: str,
        action_id: str,
        state: CombatState,
        combatants_payload: list[dict],
        battle_map_payload: dict | None,
        latest_map_state: LimiarMapStateResponse | None,
    ) -> LimiarMapCombatProjectionResult:
        start_payload: dict = {"actionId": action_id, "combatants": combatants_payload}
        if battle_map_payload is not None:
            start_payload["battleMap"] = battle_map_payload
        try:
            started_state = self._limiar_map_client.start_combat(session_id, start_payload)
        except LimiarMapClientError as exc:
            return self._handle_combat_start_conflict(
                session_id, action_id, state, combatants_payload, latest_map_state, exc,
            )
        logger.info(
            "LimiarMap combat/start succeeded for session_id=%s action_id=%s combatants=%s",
            session_id, action_id, len(combatants_payload),
        )
        turn_sync_reason = _sync_existing_map_turn(
            self._limiar_map_client, session_id, state, started_state,
        )
        return LimiarMapCombatProjectionResult(map_available=True, reason=turn_sync_reason)

    def _handle_combat_start_conflict(
        self,
        session_id: str,
        action_id: str,
        state: CombatState,
        combatants_payload: list[dict],
        latest_map_state: LimiarMapStateResponse | None,
        exc: LimiarMapClientError,
    ) -> LimiarMapCombatProjectionResult:
        if (
            exc.kind == "http"
            and exc.status_code == 409
            and exc.reason in {"combat_already_active", "duplicate_action"}
        ):
            turn_sync_reason = _sync_existing_map_turn(
                self._limiar_map_client, session_id, state, latest_map_state,
            )
            logger.info(
                "LimiarMap combat/start already satisfied session_id=%s action_id=%s reason=%s sync=%s",
                session_id, action_id, exc.reason, turn_sync_reason,
            )
            reported_reason = exc.reason
            if turn_sync_reason in {"turn_synced", "turn_sync_failed", "turn_sync_state_unavailable"}:
                reported_reason = turn_sync_reason
            return LimiarMapCombatProjectionResult(map_available=True, reason=reported_reason)
        logger.warning(
            "LimiarMap combat/start failed for session_id=%s action_id=%s combatants=%s (%s)",
            session_id, action_id, len(combatants_payload), exc,
        )
        return LimiarMapCombatProjectionResult(map_available=False, reason=f"combat_start_{exc.kind}")

    def _bootstrap_tokens(
        self,
        db: Session,
        session_id: str,
        action_id: str,
        state: CombatState,
        map_state: LimiarMapStateResponse,
    ) -> LimiarMapStateResponse | None:
        latest_map_state: LimiarMapStateResponse | None = map_state
        sync_entries, spawn_entries = build_sync_entries(
            db, session_id, state.participants, map_state,
        )
        if not sync_entries and not spawn_entries:
            logger.info(
                "LimiarMap syncTokens skipped for session_id=%s action_id=%s (no resolvable links)",
                session_id, action_id,
            )
            return latest_map_state
        logger.info(
            "LimiarMap syncTokens started for session_id=%s action_id=%s sync=%s spawn=%s",
            session_id, action_id, len(sync_entries), len(spawn_entries),
        )

        def _entry_payload(
            e: ResolvedTokenSyncEntry | ResolvedTokenSpawnEntry,
            *,
            token_id: str | None = None,
        ) -> dict:
            payload: dict = {}
            if token_id is not None:
                payload["tokenId"] = token_id
            if isinstance(e, ResolvedTokenSpawnEntry) and e.kind is not None:
                payload["kind"] = e.kind
            payload["combatantId"] = e.combatant_id
            if e.movement_speed_cells is not None:
                payload["movementSpeedCells"] = e.movement_speed_cells
            if e.label is not None:
                payload["label"] = e.label
            if e.controller_id is not None:
                payload["controllerId"] = e.controller_id
            if e.controller_type is not None:
                payload["controllerType"] = e.controller_type
            if e.size_category is not None:
                payload["sizeCategory"] = e.size_category
            payload["conditions"] = list(e.conditions)
            return payload

        tokens_payload = (
            [_entry_payload(e, token_id=e.token_id) for e in sync_entries]
            + [_entry_payload(e) for e in spawn_entries]
        )
        try:
            latest_map_state = self._limiar_map_client.sync_tokens(
                session_id,
                {"tokens": tokens_payload},
            )
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap syncTokens failed for session_id=%s action_id=%s count=%s (%s)",
                session_id, action_id, len(sync_entries), exc,
            )
        else:
            logger.info(
                "LimiarMap syncTokens succeeded for session_id=%s action_id=%s count=%s",
                session_id, action_id, len(sync_entries),
            )
        return latest_map_state

    def sync_conditions_to_map(self, session_id: str, state: CombatState) -> None:
        try:
            map_state = self._limiar_map_client.get_state(session_id)
        except LimiarMapClientError as exc:
            logger.warning("[conditions] sync skipped session=%s — could not fetch map state: %s", session_id, exc)
            return
        token_by_combatant_id = {
            t.combatant_id: t.token_id for t in map_state.tokens if t.combatant_id is not None
        }
        payload_tokens: list[dict] = []
        for p in state.participants:
            cid = p.get("ref_id")
            if not isinstance(cid, str):
                continue
            tid = token_by_combatant_id.get(cid)
            if tid is None:
                continue
            payload_tokens.append({"tokenId": tid, "conditions": _extract_participant_conditions(p)})
        if not payload_tokens:
            return
        try:
            self._limiar_map_client.sync_tokens(session_id, {"tokens": payload_tokens})
        except LimiarMapClientError as exc:
            logger.warning("[conditions] sync failed session=%s participants=%d: %s", session_id, len(payload_tokens), exc)

    def project_combat_advance(self, session_id: str, state: CombatState) -> None:
        if state.phase not in (CombatPhase.active, "active"):
            return
        action_id = self.build_combat_advance_action_id(state)
        logger.info(
            "LimiarMap combat/advance started for session_id=%s action_id=%s round=%s turn_index=%s",
            session_id, action_id, state.round, state.current_turn_index,
        )
        try:
            self._limiar_map_client.advance_combat(session_id, {"actionId": action_id})
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap combat/advance failed for session_id=%s action_id=%s round=%s turn_index=%s (%s)",
                session_id, action_id, state.round, state.current_turn_index, exc,
            )
            return
        logger.info(
            "LimiarMap combat/advance succeeded for session_id=%s action_id=%s round=%s turn_index=%s",
            session_id, action_id, state.round, state.current_turn_index,
        )
        self.sync_conditions_to_map(session_id, state)

    def project_combat_end(self, session_id: str, state: CombatState) -> None:
        if state.phase not in (CombatPhase.ended, "ended"):
            return
        action_id = self.build_combat_end_action_id(state)
        logger.info("LimiarMap combat/end started for session_id=%s action_id=%s", session_id, action_id)
        try:
            self._limiar_map_client.end_combat(session_id, {"actionId": action_id})
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap combat/end failed for session_id=%s action_id=%s (%s)",
                session_id, action_id, exc,
            )
            return
        logger.info("LimiarMap combat/end succeeded for session_id=%s action_id=%s", session_id, action_id)

    @staticmethod
    def build_combat_start_action_id(state: CombatState) -> str:
        return f"control-combat-start:{state.id}"

    @staticmethod
    def build_combat_advance_action_id(state: CombatState) -> str:
        return f"control-combat-advance:{state.id}:{state.round}:{state.current_turn_index}"

    @staticmethod
    def build_combat_end_action_id(state: CombatState) -> str:
        return f"control-combat-end:{state.id}"


_projection_service: LimiarMapCombatProjectionService | None = None
_projection_service_signature: tuple[bool, str, float] | None = None


def reset_limiar_map_projection_service() -> None:
    global _projection_service, _projection_service_signature
    _projection_service = None
    _projection_service_signature = None


def _build_projection_service() -> LimiarMapCombatProjectionService:
    return LimiarMapCombatProjectionService(
        LimiarMapClient(
            base_url=settings.limiar_map_base_url,
            timeout_seconds=settings.limiar_map_timeout_seconds,
        )
    )


def get_limiar_map_projection_service() -> LimiarMapCombatProjectionService:
    global _projection_service, _projection_service_signature
    signature = (
        settings.limiar_map_enabled,
        settings.limiar_map_base_url,
        settings.limiar_map_timeout_seconds,
    )
    if _projection_service is None or _projection_service_signature != signature:
        _projection_service = _build_projection_service()
        _projection_service_signature = signature
    return _projection_service


def maybe_project_combat_start_to_limiar_map(db: Session, session_id: str, state: CombatState) -> None:
    if not settings.limiar_map_enabled or not state.use_map:
        return
    get_limiar_map_projection_service().project_combat_start(db, session_id, state)


def maybe_project_combat_advance_to_limiar_map(session_id: str, state: CombatState) -> None:
    if not settings.limiar_map_enabled or not state.use_map:
        return
    get_limiar_map_projection_service().project_combat_advance(session_id, state)


def maybe_project_combat_end_to_limiar_map(session_id: str, state: CombatState) -> None:
    if not settings.limiar_map_enabled or not state.use_map:
        return
    get_limiar_map_projection_service().project_combat_end(session_id, state)


def maybe_sync_conditions_to_limiar_map(session_id: str, state: CombatState) -> None:
    if not settings.limiar_map_enabled or not state.use_map:
        return
    get_limiar_map_projection_service().sync_conditions_to_map(session_id, state)
