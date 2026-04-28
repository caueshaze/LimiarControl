from __future__ import annotations

from typing import Any

import httpx

from .limiar_map_client_types import (
    LimiarMapAreaTargetingResponse,
    LimiarMapBatchTargetingResponse,
    LimiarMapClientError,
    LimiarMapMovementResponse,
    LimiarMapStateResponse,
    LimiarMapTargetingResponse,
)
from .limiar_map_client_types import (  # noqa: F401
    LimiarMapAreaCell,
    LimiarMapMovementCell,
    LimiarMapObstacleCell,
    LimiarMapObstacleState,
    LimiarMapTokenState,
)
from .limiar_map_client_parsers import (
    parse_area_targeting_response,
    parse_batch_targeting_response,
    parse_movement_response,
    parse_targeting_response,
)
from .limiar_map_client_state_parser import parse_state_response


class LimiarMapClient:
    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def get_state(self, session_id: str) -> LimiarMapStateResponse:
        data = self._request_json("GET", f"/integration/sessions/{session_id}/state")
        return parse_state_response(data)

    def get_session_state(self, session_id: str) -> LimiarMapStateResponse:
        return self.get_state(session_id)

    def sync_tokens(
        self, session_id: str, payload: dict[str, Any]
    ) -> LimiarMapStateResponse:
        data = self._request_json(
            "PUT",
            f"/integration/sessions/{session_id}/tokens",
            json_payload=payload,
        )
        return parse_state_response(data)

    def sync_active_area_effects(
        self, session_id: str, payload: dict[str, Any]
    ) -> LimiarMapStateResponse:
        data = self._request_json(
            "PUT",
            f"/integration/sessions/{session_id}/area-effects",
            json_payload=payload,
        )
        return parse_state_response(data)

    def start_combat(
        self, session_id: str, payload: dict[str, Any]
    ) -> LimiarMapStateResponse:
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/combat/start",
            json_payload=payload,
        )
        return parse_state_response(data)

    def advance_combat(
        self, session_id: str, payload: dict[str, Any]
    ) -> LimiarMapStateResponse:
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/combat/advance",
            json_payload=payload,
        )
        return parse_state_response(data)

    def end_combat(
        self, session_id: str, payload: dict[str, Any]
    ) -> LimiarMapStateResponse:
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/combat/end",
            json_payload=payload,
        )
        return parse_state_response(data)

    def validate_single_target(
        self,
        *,
        session_id: str,
        action_id: str,
        combatant_id: str,
        target_combatant_id: str,
        range_cells: int | None,
        requires_sight: bool = False,
        requires_effect: bool = False,
    ) -> LimiarMapTargetingResponse:
        # range_cells is already converted from meters at the LimiarControl boundary.
        payload = {
            "actionId": action_id,
            "combatantId": combatant_id,
            "targetCombatantId": target_combatant_id,
            "rangeCells": range_cells,
            "requiresSight": requires_sight,
            "requiresEffect": requires_effect,
        }
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/targeting",
            json_payload=payload,
        )
        return parse_targeting_response(data)

    def validate_targets_batch(
        self,
        *,
        session_id: str,
        action_id: str,
        combatant_id: str,
        target_combatant_ids: list[str],
    ) -> LimiarMapBatchTargetingResponse:
        payload = {
            "actionId": action_id,
            "combatantId": combatant_id,
            "targetCombatantIds": target_combatant_ids,
        }
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/targeting/batch",
            json_payload=payload,
        )
        return parse_batch_targeting_response(data)

    def resolve_area_targeting(
        self,
        *,
        session_id: str,
        action_id: str,
        combatant_id: str,
        shape: str,
        origin_cell: dict[str, int],
        anchor_cell: dict[str, int],
        range_cells: int | None,
        size_cells: int,
        requires_sight: bool = False,
        requires_effect: bool = False,
    ) -> LimiarMapAreaTargetingResponse:
        # range_cells and size_cells are already converted from meters at the LimiarControl boundary.
        payload = {
            "actionId": action_id,
            "combatantId": combatant_id,
            "shape": shape,
            "originCell": origin_cell,
            "anchorCell": anchor_cell,
            "rangeCells": range_cells,
            "sizeCells": size_cells,
            "requiresSight": requires_sight,
            "requiresEffect": requires_effect,
        }
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/targeting/area",
            json_payload=payload,
        )
        return parse_area_targeting_response(data)

    def preview_area_targeting(
        self,
        *,
        session_id: str,
        action_id: str,
        combatant_id: str,
        shape: str,
        origin_cell: dict[str, int],
        anchor_cell: dict[str, int],
        range_cells: int | None,
        size_cells: int,
        requires_sight: bool = False,
        requires_effect: bool = False,
    ) -> LimiarMapAreaTargetingResponse:
        # range_cells and size_cells are already converted from meters at the LimiarControl boundary.
        payload = {
            "actionId": action_id,
            "combatantId": combatant_id,
            "shape": shape,
            "originCell": origin_cell,
            "anchorCell": anchor_cell,
            "rangeCells": range_cells,
            "sizeCells": size_cells,
            "requiresSight": requires_sight,
            "requiresEffect": requires_effect,
        }
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/targeting/area/preview",
            json_payload=payload,
        )
        return parse_area_targeting_response(data)

    def preview_movement(
        self,
        *,
        session_id: str,
        action_id: str,
        combatant_id: str,
        destination_cell: dict[str, int],
    ) -> LimiarMapMovementResponse:
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/movement/preview",
            json_payload={
                "actionId": action_id,
                "combatantId": combatant_id,
                "destinationCell": destination_cell,
            },
        )
        return parse_movement_response(data)

    def move_combatant(
        self,
        *,
        session_id: str,
        action_id: str,
        combatant_id: str,
        destination_cell: dict[str, int],
    ) -> LimiarMapMovementResponse:
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/movement",
            json_payload={
                "actionId": action_id,
                "combatantId": combatant_id,
                "destinationCell": destination_cell,
            },
        )
        return parse_movement_response(data)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.request(method, url, json=json_payload)
        except httpx.TimeoutException as exc:
            raise LimiarMapClientError(
                f"LimiarMap request timed out: {method} {url}",
                kind="timeout",
            ) from exc
        except httpx.RequestError as exc:
            raise LimiarMapClientError(
                f"LimiarMap request failed: {method} {url}",
                kind="network",
            ) from exc

        if response.status_code >= 400:
            message = f"LimiarMap returned HTTP {response.status_code} for {method} {url}"
            reason: str | None = None
            try:
                payload = response.json()
            except ValueError:
                payload = None
            if isinstance(payload, dict) and isinstance(payload.get("message"), str):
                message = payload["message"]
            if isinstance(payload, dict) and isinstance(payload.get("reason"), str):
                reason = payload["reason"]
            raise LimiarMapClientError(
                message,
                kind="http",
                status_code=response.status_code,
                reason=reason,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LimiarMapClientError(
                f"LimiarMap returned invalid JSON for {method} {url}",
                kind="payload",
            ) from exc

        if not isinstance(data, dict):
            raise LimiarMapClientError(
                f"LimiarMap returned an unexpected payload for {method} {url}",
                kind="payload",
            )
        return data
