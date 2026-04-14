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
    _extract_participant_conditions,
)

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
        if state.phase not in (CombatPhase.active, "active"):
            return LimiarMapCombatProjectionResult(
                map_available=False,
                reason="combat_not_active",
            )

        combatants_payload = self._build_combatants_payload(state)
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
        battle_map_payload = self._build_battle_map_payload(session_id, state)
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
            sync_entries, unresolved_combatants = build_sync_entries(
                db,
                session_id,
                state.participants,
                map_state,
            )
            if unresolved_combatants:
                logger.warning(
                    "LimiarMap token linkage unresolved for session_id=%s action_id=%s unresolved_combatants=%s",
                    session_id,
                    action_id,
                    unresolved_combatants,
                )

            if sync_entries:
                logger.info(
                    "LimiarMap syncTokens started for session_id=%s action_id=%s token_count=%s",
                    session_id,
                    action_id,
                    len(sync_entries),
                )
                try:
                    latest_map_state = self._limiar_map_client.sync_tokens(
                        session_id,
                        {
                            "tokens": [
                                {
                                    "tokenId": entry.token_id,
                                    "combatantId": entry.combatant_id,
                                    **(
                                        {
                                            "movementSpeedCells": entry.movement_speed_cells
                                        }
                                        if entry.movement_speed_cells is not None
                                        else {}
                                    ),
                                    **(
                                        {"label": entry.label}
                                        if entry.label is not None
                                        else {}
                                    ),
                                    **(
                                        {"controllerId": entry.controller_id}
                                        if entry.controller_id is not None
                                        else {}
                                    ),
                                    **(
                                        {"controllerType": entry.controller_type}
                                        if entry.controller_type is not None
                                        else {}
                                    ),
                                    **(
                                        {"sizeCategory": entry.size_category}
                                        if entry.size_category is not None
                                        else {}
                                    ),
                                    # Always include conditions (even []) so the
                                    # map-server can clear stale condition badges.
                                    "conditions": list(entry.conditions),
                                }
                                for entry in sync_entries
                            ]
                        },
                    )
                except LimiarMapClientError as exc:
                    logger.warning(
                        "LimiarMap syncTokens failed for session_id=%s action_id=%s token_count=%s; "
                        "combat start will continue without token bootstrap (%s)",
                        session_id,
                        action_id,
                        len(sync_entries),
                        exc,
                    )
                else:
                    logger.info(
                        "LimiarMap syncTokens succeeded for session_id=%s action_id=%s token_count=%s",
                        session_id,
                        action_id,
                        len(sync_entries),
                    )
            else:
                logger.info(
                    "LimiarMap syncTokens skipped for session_id=%s action_id=%s because no token links were resolvable",
                    session_id,
                    action_id,
                )

        logger.info(
            "LimiarMap combat/start started for session_id=%s action_id=%s combatants=%s",
            session_id,
            action_id,
            len(combatants_payload),
        )
        try:
            started_state = self._limiar_map_client.start_combat(
                session_id,
                {
                    "actionId": action_id,
                    "combatants": combatants_payload,
                    **(
                        {"battleMap": battle_map_payload}
                        if battle_map_payload is not None
                        else {}
                    ),
                },
            )
        except LimiarMapClientError as exc:
            if (
                exc.kind == "http"
                and exc.status_code == 409
                and exc.reason
                in {
                    "combat_already_active",
                    "duplicate_action",
                }
            ):
                turn_sync_reason = self._sync_existing_map_turn(
                    session_id,
                    state,
                    latest_map_state,
                )
                logger.info(
                    "LimiarMap combat/start already satisfied for session_id=%s action_id=%s "
                    "reason=%s turn_sync_reason=%s; treating map as available",
                    session_id,
                    action_id,
                    exc.reason,
                    turn_sync_reason,
                )
                reported_reason = exc.reason
                if turn_sync_reason in {
                    "turn_synced",
                    "turn_sync_failed",
                    "turn_sync_state_unavailable",
                }:
                    reported_reason = turn_sync_reason
                return LimiarMapCombatProjectionResult(
                    map_available=True,
                    reason=reported_reason,
                )
            logger.warning(
                "LimiarMap combat/start failed for session_id=%s action_id=%s combatants=%s; "
                "combat remains active only in Control (%s)",
                session_id,
                action_id,
                len(combatants_payload),
                exc,
            )
            return LimiarMapCombatProjectionResult(
                map_available=False,
                reason=f"combat_start_{exc.kind}",
            )

        logger.info(
            "LimiarMap combat/start succeeded for session_id=%s action_id=%s combatants=%s",
            session_id,
            action_id,
            len(combatants_payload),
        )
        turn_sync_reason = self._sync_existing_map_turn(
            session_id,
            state,
            started_state,
        )
        return LimiarMapCombatProjectionResult(
            map_available=True,
            reason=turn_sync_reason,
        )

    def _sync_existing_map_turn(
        self,
        session_id: str,
        state: CombatState,
        map_state: LimiarMapStateResponse | None,
    ) -> str | None:
        desired_order = self._build_initiative_order(state)
        if not desired_order:
            return None

        if map_state is None:
            try:
                map_state = self._limiar_map_client.get_state(session_id)
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
                self._limiar_map_client.advance_combat(
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

    def sync_conditions_to_map(
        self,
        session_id: str,
        state: CombatState,
    ) -> None:
        """Push current condition lists for all participants to the map-server.

        Called after any action that may have changed participant conditions
        (attacks, spells, saves, turn advance).  Uses the same syncTokens path
        as the initial combat-start projection — only the ``conditions`` field
        is touched, leaving positions, labels, and movement speed unchanged.

        Errors are logged and swallowed; condition display degradation is
        preferable to blocking the combat flow.
        """
        try:
            map_state = self._limiar_map_client.get_state(session_id)
        except LimiarMapClientError as exc:
            logger.warning(
                "[conditions] sync skipped session=%s — could not fetch map state: %s",
                session_id,
                exc,
            )
            return

        token_by_combatant_id = {
            token.combatant_id: token.token_id
            for token in map_state.tokens
            if token.combatant_id is not None
        }

        payload_tokens: list[dict] = []
        for participant in state.participants:
            combatant_id = participant.get("ref_id")
            if not isinstance(combatant_id, str):
                continue
            token_id = token_by_combatant_id.get(combatant_id)
            if token_id is None:
                continue
            conditions = _extract_participant_conditions(participant)
            payload_tokens.append({"tokenId": token_id, "conditions": conditions})

        if not payload_tokens:
            return

        try:
            self._limiar_map_client.sync_tokens(session_id, {"tokens": payload_tokens})
        except LimiarMapClientError as exc:
            logger.warning(
                "[conditions] sync failed session=%s participants=%d: %s",
                session_id,
                len(payload_tokens),
                exc,
            )

    def project_combat_advance(
        self,
        session_id: str,
        state: CombatState,
    ) -> None:
        if state.phase not in (CombatPhase.active, "active"):
            return

        action_id = self.build_combat_advance_action_id(state)
        logger.info(
            "LimiarMap combat/advance started for session_id=%s action_id=%s round=%s turn_index=%s",
            session_id,
            action_id,
            state.round,
            state.current_turn_index,
        )
        try:
            self._limiar_map_client.advance_combat(
                session_id,
                {
                    "actionId": action_id,
                },
            )
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap combat/advance failed for session_id=%s action_id=%s round=%s turn_index=%s; "
                "combat remains authoritative in Control (%s)",
                session_id,
                action_id,
                state.round,
                state.current_turn_index,
                exc,
            )
            return

        logger.info(
            "LimiarMap combat/advance succeeded for session_id=%s action_id=%s round=%s turn_index=%s",
            session_id,
            action_id,
            state.round,
            state.current_turn_index,
        )

        # Refresh condition badges on every turn advance so conditions applied
        # or removed mid-turn become visible at the start of the next turn.
        self.sync_conditions_to_map(session_id, state)

    def project_combat_end(
        self,
        session_id: str,
        state: CombatState,
    ) -> None:
        if state.phase not in (CombatPhase.ended, "ended"):
            return

        action_id = self.build_combat_end_action_id(state)
        logger.info(
            "LimiarMap combat/end started for session_id=%s action_id=%s",
            session_id,
            action_id,
        )
        try:
            self._limiar_map_client.end_combat(
                session_id,
                {
                    "actionId": action_id,
                },
            )
        except LimiarMapClientError as exc:
            logger.warning(
                "LimiarMap combat/end failed for session_id=%s action_id=%s; "
                "combat remains ended in Control (%s)",
                session_id,
                action_id,
                exc,
            )
            return

        logger.info(
            "LimiarMap combat/end succeeded for session_id=%s action_id=%s",
            session_id,
            action_id,
        )

    @staticmethod
    def build_combat_start_action_id(state: CombatState) -> str:
        return f"control-combat-start:{state.id}"

    @staticmethod
    def build_combat_advance_action_id(state: CombatState) -> str:
        return f"control-combat-advance:{state.id}:{state.round}:{state.current_turn_index}"

    @staticmethod
    def build_combat_end_action_id(state: CombatState) -> str:
        return f"control-combat-end:{state.id}"

    @staticmethod
    def _build_initiative_order(state: CombatState) -> list[str]:
        return [
            combatant_id
            for participant in state.participants
            if isinstance((combatant_id := participant.get("ref_id")), str)
            and combatant_id.strip()
        ]

    @staticmethod
    def _build_battle_map_payload(
        session_id: str,
        state: CombatState,
    ) -> dict[str, object] | None:
        raw_selection = getattr(state, "map_selection", None)
        if not isinstance(raw_selection, dict):
            return None

        map_name = raw_selection.get("mapName")
        image_url = raw_selection.get("imageUrl")
        grid_width = raw_selection.get("gridWidth")
        grid_height = raw_selection.get("gridHeight")
        calibration = raw_selection.get("calibration")
        if (
            not isinstance(map_name, str)
            or not map_name.strip()
            or not isinstance(image_url, str)
            or not image_url.strip()
            or not isinstance(grid_width, int)
            or not isinstance(grid_height, int)
            or not isinstance(calibration, dict)
        ):
            return None

        source_image_url = image_url.strip()
        if source_image_url.startswith("/api/assets/"):
            map_image_url = f"/sessions/{session_id}/battle-map/background"
            source_image_url = source_image_url.replace(
                "/api/assets/",
                "/api/assets/internal/",
                1,
            )
        else:
            map_image_url = source_image_url

        payload: dict[str, object] = {
            "name": map_name.strip(),
            "gridWidth": grid_width,
            "gridHeight": grid_height,
            "gridCalibration": calibration,
            "imageUrl": map_image_url,
            "sourceImageUrl": source_image_url,
        }

        # Include campaign-level blocked cells so LimiarMap can seed its
        # encounter obstacles.  authoritative source: CampaignTacticalMap DB row.
        blocked_cells = raw_selection.get("blockedCells")
        if isinstance(blocked_cells, list) and blocked_cells:
            payload["blockedCells"] = blocked_cells

        return payload

    @staticmethod
    def _build_combatants_payload(state: CombatState) -> list[dict[str, int | str]]:
        payload: list[dict[str, int | str]] = []
        for participant in state.participants:
            combatant_id = participant.get("ref_id")
            if not isinstance(combatant_id, str) or not combatant_id.strip():
                continue
            initiative = participant.get("initiative")
            initiative_score = initiative if isinstance(initiative, int) else 0
            payload.append(
                {
                    "combatantId": combatant_id,
                    "initiativeScore": initiative_score,
                }
            )
        return payload


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


def maybe_project_combat_start_to_limiar_map(
    db: Session,
    session_id: str,
    state: CombatState,
) -> None:
    if not settings.limiar_map_enabled or not state.use_map:
        return

    get_limiar_map_projection_service().project_combat_start(
        db,
        session_id,
        state,
    )


def maybe_project_combat_advance_to_limiar_map(
    session_id: str,
    state: CombatState,
) -> None:
    if not settings.limiar_map_enabled or not state.use_map:
        return

    get_limiar_map_projection_service().project_combat_advance(
        session_id,
        state,
    )


def maybe_project_combat_end_to_limiar_map(
    session_id: str,
    state: CombatState,
) -> None:
    if not settings.limiar_map_enabled or not state.use_map:
        return

    get_limiar_map_projection_service().project_combat_end(
        session_id,
        state,
    )


def maybe_sync_conditions_to_limiar_map(
    session_id: str,
    state: CombatState,
) -> None:
    """Push current participant conditions to the map-server after any combat
    action that may have changed them (attacks, spells, saving throws, etc.).

    Errors are logged and swallowed inside the projection service — condition
    display degradation must never block the combat flow.
    """
    if not settings.limiar_map_enabled or not state.use_map:
        return

    get_limiar_map_projection_service().sync_conditions_to_map(
        session_id,
        state,
    )
