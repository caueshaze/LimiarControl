from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class LimiarMapTokenState:
    token_id: str
    controller_type: str
    controller_id: str
    movement_speed_cells: int
    combatant_id: str | None
    kind: str | None = None
    label: str | None = None
    position_x: int | None = None
    position_y: int | None = None


@dataclass(frozen=True)
class LimiarMapObstacleCell:
    x: int
    y: int


@dataclass(frozen=True)
class LimiarMapObstacleState:
    cells: tuple[LimiarMapObstacleCell, ...]
    blocks_movement: bool
    blocks_vision: bool
    blocks_effect: bool
    cover: str | None = None


@dataclass(frozen=True)
class LimiarMapStateResponse:
    session_id: str
    version: int
    tokens: tuple[LimiarMapTokenState, ...]
    grid_width: int | None = None
    grid_height: int | None = None
    obstacles: tuple[LimiarMapObstacleState, ...] = ()
    active_combatant_id: str | None = None
    round_number: int | None = None
    turn_index: int | None = None
    initiative_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class LimiarMapTargetingResponse:
    is_valid: bool
    reason: str | None
    session_id: str
    action_id: str
    version: int
    source_token_id: str | None
    target_token_id: str | None
    cover: str | None = None


@dataclass(frozen=True)
class LimiarMapAreaCell:
    x: int
    y: int


@dataclass(frozen=True)
class LimiarMapAreaTargetingResponse:
    is_valid: bool
    reason: str | None
    session_id: str
    action_id: str
    version: int
    shape: str
    source_token_id: str | None
    affected_cells: tuple[LimiarMapAreaCell, ...]
    affected_token_ids: tuple[str, ...]
    affected_combatant_ids: tuple[str, ...]


class LimiarMapClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        kind: str,
        status_code: int | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.reason = reason


class LimiarMapClient:
    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def get_state(self, session_id: str) -> LimiarMapStateResponse:
        data = self._request_json("GET", f"/integration/sessions/{session_id}/state")
        return self._parse_state_response(data)

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
        return self._parse_state_response(data)

    def start_combat(
        self, session_id: str, payload: dict[str, Any]
    ) -> LimiarMapStateResponse:
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/combat/start",
            json_payload=payload,
        )
        return self._parse_state_response(data)

    def advance_combat(
        self, session_id: str, payload: dict[str, Any]
    ) -> LimiarMapStateResponse:
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/combat/advance",
            json_payload=payload,
        )
        return self._parse_state_response(data)

    def end_combat(
        self, session_id: str, payload: dict[str, Any]
    ) -> LimiarMapStateResponse:
        data = self._request_json(
            "POST",
            f"/integration/sessions/{session_id}/combat/end",
            json_payload=payload,
        )
        return self._parse_state_response(data)

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
        return self._parse_targeting_response(data)

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
        return self._parse_area_targeting_response(data)

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
        return self._parse_area_targeting_response(data)

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

    def _parse_targeting_response(
        self, payload: dict[str, Any]
    ) -> LimiarMapTargetingResponse:
        is_valid = payload.get("isValid")
        reason = payload.get("reason")
        session_id = payload.get("sessionId")
        action_id = payload.get("actionId")
        version = payload.get("version")
        source_token_id = payload.get("sourceTokenId")
        target_token_id = payload.get("targetTokenId")

        if not isinstance(is_valid, bool):
            raise LimiarMapClientError(
                "LimiarMap targeting response is missing isValid",
                kind="payload",
            )
        if reason is not None and not isinstance(reason, str):
            raise LimiarMapClientError(
                "LimiarMap targeting response has an invalid reason",
                kind="payload",
            )
        if not isinstance(session_id, str) or not session_id.strip():
            raise LimiarMapClientError(
                "LimiarMap targeting response is missing sessionId",
                kind="payload",
            )
        if not isinstance(action_id, str) or not action_id.strip():
            raise LimiarMapClientError(
                "LimiarMap targeting response is missing actionId",
                kind="payload",
            )
        if not isinstance(version, int):
            raise LimiarMapClientError(
                "LimiarMap targeting response is missing version",
                kind="payload",
            )
        if source_token_id is not None and not isinstance(source_token_id, str):
            raise LimiarMapClientError(
                "LimiarMap targeting response has an invalid sourceTokenId",
                kind="payload",
            )
        if target_token_id is not None and not isinstance(target_token_id, str):
            raise LimiarMapClientError(
                "LimiarMap targeting response has an invalid targetTokenId",
                kind="payload",
            )

        return LimiarMapTargetingResponse(
            is_valid=is_valid,
            reason=reason,
            session_id=session_id,
            action_id=action_id,
            version=version,
            source_token_id=source_token_id,
            target_token_id=target_token_id,
            cover=payload.get("cover") if isinstance(payload.get("cover"), str) else None,
        )

    def _parse_area_targeting_response(
        self, payload: dict[str, Any]
    ) -> LimiarMapAreaTargetingResponse:
        is_valid = payload.get("isValid")
        reason = payload.get("reason")
        session_id = payload.get("sessionId")
        action_id = payload.get("actionId")
        version = payload.get("version")
        shape = payload.get("shape")
        source_token_id = payload.get("sourceTokenId")
        affected_cells_payload = payload.get("affectedCells")
        affected_token_ids_payload = payload.get("affectedTokenIds")
        affected_combatant_ids_payload = payload.get("affectedCombatantIds")

        if not isinstance(is_valid, bool):
            raise LimiarMapClientError(
                "LimiarMap area targeting response is missing isValid",
                kind="payload",
            )
        if reason is not None and not isinstance(reason, str):
            raise LimiarMapClientError(
                "LimiarMap area targeting response has an invalid reason",
                kind="payload",
            )
        if not isinstance(session_id, str) or not session_id.strip():
            raise LimiarMapClientError(
                "LimiarMap area targeting response is missing sessionId",
                kind="payload",
            )
        if not isinstance(action_id, str) or not action_id.strip():
            raise LimiarMapClientError(
                "LimiarMap area targeting response is missing actionId",
                kind="payload",
            )
        if not isinstance(version, int):
            raise LimiarMapClientError(
                "LimiarMap area targeting response is missing version",
                kind="payload",
            )
        if not isinstance(shape, str) or not shape.strip():
            raise LimiarMapClientError(
                "LimiarMap area targeting response is missing shape",
                kind="payload",
            )
        if source_token_id is not None and not isinstance(source_token_id, str):
            raise LimiarMapClientError(
                "LimiarMap area targeting response has an invalid sourceTokenId",
                kind="payload",
            )
        if not isinstance(affected_cells_payload, list):
            raise LimiarMapClientError(
                "LimiarMap area targeting response is missing affectedCells",
                kind="payload",
            )
        if not isinstance(affected_token_ids_payload, list):
            raise LimiarMapClientError(
                "LimiarMap area targeting response is missing affectedTokenIds",
                kind="payload",
            )
        if not isinstance(affected_combatant_ids_payload, list):
            raise LimiarMapClientError(
                "LimiarMap area targeting response is missing affectedCombatantIds",
                kind="payload",
            )

        affected_cells: list[LimiarMapAreaCell] = []
        for raw_cell in affected_cells_payload:
            if not isinstance(raw_cell, dict):
                raise LimiarMapClientError(
                    "LimiarMap area targeting response has an invalid affected cell",
                    kind="payload",
                )
            x = raw_cell.get("x")
            y = raw_cell.get("y")
            if not isinstance(x, int) or not isinstance(y, int):
                raise LimiarMapClientError(
                    "LimiarMap area targeting response has an invalid affected cell coordinate",
                    kind="payload",
                )
            affected_cells.append(LimiarMapAreaCell(x=x, y=y))

        affected_token_ids: list[str] = []
        for token_id in affected_token_ids_payload:
            if not isinstance(token_id, str):
                raise LimiarMapClientError(
                    "LimiarMap area targeting response has an invalid affectedTokenId",
                    kind="payload",
                )
            affected_token_ids.append(token_id)

        affected_combatant_ids: list[str] = []
        for combatant_id in affected_combatant_ids_payload:
            if not isinstance(combatant_id, str):
                raise LimiarMapClientError(
                    "LimiarMap area targeting response has an invalid affectedCombatantId",
                    kind="payload",
                )
            affected_combatant_ids.append(combatant_id)

        return LimiarMapAreaTargetingResponse(
            is_valid=is_valid,
            reason=reason,
            session_id=session_id,
            action_id=action_id,
            version=version,
            shape=shape,
            source_token_id=source_token_id,
            affected_cells=tuple(affected_cells),
            affected_token_ids=tuple(affected_token_ids),
            affected_combatant_ids=tuple(affected_combatant_ids),
        )

    def _parse_state_response(self, payload: dict[str, Any]) -> LimiarMapStateResponse:
        session_id = payload.get("sessionId")
        version = payload.get("version")
        tokens_payload = payload.get("tokens")
        combat_state_payload = payload.get("combatState")
        battle_map_payload = payload.get("battleMap")
        obstacles_payload = payload.get("obstacles")

        if not isinstance(session_id, str) or not session_id.strip():
            raise LimiarMapClientError(
                "LimiarMap state response is missing sessionId",
                kind="payload",
            )
        if not isinstance(version, int):
            raise LimiarMapClientError(
                "LimiarMap state response is missing version",
                kind="payload",
            )
        if not isinstance(tokens_payload, list):
            raise LimiarMapClientError(
                "LimiarMap state response is missing tokens",
                kind="payload",
            )
        if battle_map_payload is not None and not isinstance(battle_map_payload, dict):
            raise LimiarMapClientError(
                "LimiarMap state response has an invalid battleMap",
                kind="payload",
            )
        if obstacles_payload is not None and not isinstance(obstacles_payload, list):
            raise LimiarMapClientError(
                "LimiarMap state response has invalid obstacles",
                kind="payload",
            )
        active_combatant_id: str | None = None
        round_number: int | None = None
        turn_index: int | None = None
        initiative_order: tuple[str, ...] = ()
        if combat_state_payload is not None:
            if not isinstance(combat_state_payload, dict):
                raise LimiarMapClientError(
                    "LimiarMap state response has an invalid combatState",
                    kind="payload",
                )
            raw_active_combatant_id = combat_state_payload.get("activeCombatantId")
            raw_round_number = combat_state_payload.get("roundNumber")
            raw_turn_index = combat_state_payload.get("turnIndex")
            raw_initiative_order = combat_state_payload.get("initiativeOrder")
            if raw_active_combatant_id is not None and not isinstance(
                raw_active_combatant_id, str
            ):
                raise LimiarMapClientError(
                    "LimiarMap state response has an invalid activeCombatantId",
                    kind="payload",
                )
            if raw_round_number is not None and not isinstance(raw_round_number, int):
                raise LimiarMapClientError(
                    "LimiarMap state response has an invalid roundNumber",
                    kind="payload",
                )
            if raw_turn_index is not None and not isinstance(raw_turn_index, int):
                raise LimiarMapClientError(
                    "LimiarMap state response has an invalid turnIndex",
                    kind="payload",
                )
            if raw_initiative_order is not None and not isinstance(raw_initiative_order, list):
                raise LimiarMapClientError(
                    "LimiarMap state response has an invalid initiativeOrder",
                    kind="payload",
                )
            if isinstance(raw_initiative_order, list):
                normalized_initiative_order: list[str] = []
                for combatant_id in raw_initiative_order:
                    if not isinstance(combatant_id, str) or not combatant_id.strip():
                        raise LimiarMapClientError(
                            "LimiarMap state response has an invalid initiativeOrder entry",
                            kind="payload",
                        )
                    normalized_initiative_order.append(combatant_id)
                initiative_order = tuple(normalized_initiative_order)
            active_combatant_id = raw_active_combatant_id
            round_number = raw_round_number
            turn_index = raw_turn_index

        tokens: list[LimiarMapTokenState] = []
        for token_payload in tokens_payload:
            if not isinstance(token_payload, dict):
                raise LimiarMapClientError(
                    "LimiarMap state response has an invalid token entry",
                    kind="payload",
                )

            token_id = token_payload.get("id")
            controller_type = token_payload.get("controllerType")
            controller_id = token_payload.get("controllerId")
            token_kind = token_payload.get("kind")
            movement_speed_cells = token_payload.get("movementSpeedCells")
            combatant_id = token_payload.get("combatantId")
            position_payload = token_payload.get("position")
            label = token_payload.get("label")

            if not isinstance(token_id, str) or not token_id.strip():
                raise LimiarMapClientError(
                    "LimiarMap token entry is missing id",
                    kind="payload",
                )
            if not isinstance(controller_type, str) or not controller_type.strip():
                raise LimiarMapClientError(
                    "LimiarMap token entry is missing controllerType",
                    kind="payload",
                )
            if token_kind is not None and not isinstance(token_kind, str):
                raise LimiarMapClientError(
                    "LimiarMap token entry has an invalid kind",
                    kind="payload",
                )
            if not isinstance(controller_id, str) or not controller_id.strip():
                raise LimiarMapClientError(
                    "LimiarMap token entry is missing controllerId",
                    kind="payload",
                )
            if not isinstance(movement_speed_cells, int):
                raise LimiarMapClientError(
                    "LimiarMap token entry is missing movementSpeedCells",
                    kind="payload",
                )
            if combatant_id is not None and not isinstance(combatant_id, str):
                raise LimiarMapClientError(
                    "LimiarMap token entry has an invalid combatantId",
                    kind="payload",
                )
            if label is not None and not isinstance(label, str):
                raise LimiarMapClientError(
                    "LimiarMap token entry has an invalid label",
                    kind="payload",
                )
            position_x: int | None = None
            position_y: int | None = None
            if position_payload is not None:
                if not isinstance(position_payload, dict):
                    raise LimiarMapClientError(
                        "LimiarMap token entry has an invalid position",
                        kind="payload",
                    )
                raw_x = position_payload.get("x")
                raw_y = position_payload.get("y")
                if not isinstance(raw_x, int) or not isinstance(raw_y, int):
                    raise LimiarMapClientError(
                        "LimiarMap token entry has an invalid position",
                        kind="payload",
                    )
                position_x = raw_x
                position_y = raw_y

            tokens.append(
                LimiarMapTokenState(
                    token_id=token_id,
                    kind=token_kind,
                    controller_type=controller_type,
                    controller_id=controller_id,
                    movement_speed_cells=movement_speed_cells,
                    combatant_id=combatant_id,
                    label=label,
                    position_x=position_x,
                    position_y=position_y,
                )
            )

        grid_width: int | None = None
        grid_height: int | None = None
        if isinstance(battle_map_payload, dict):
            raw_grid_width = battle_map_payload.get("gridWidth")
            raw_grid_height = battle_map_payload.get("gridHeight")
            if raw_grid_width is not None and not isinstance(raw_grid_width, int):
                raise LimiarMapClientError(
                    "LimiarMap battleMap has an invalid gridWidth",
                    kind="payload",
                )
            if raw_grid_height is not None and not isinstance(raw_grid_height, int):
                raise LimiarMapClientError(
                    "LimiarMap battleMap has an invalid gridHeight",
                    kind="payload",
                )
            grid_width = raw_grid_width
            grid_height = raw_grid_height

        obstacles: list[LimiarMapObstacleState] = []
        for obstacle_payload in obstacles_payload or []:
            if not isinstance(obstacle_payload, dict):
                raise LimiarMapClientError(
                    "LimiarMap obstacle entry is invalid",
                    kind="payload",
                )
            raw_cells = obstacle_payload.get("cells")
            if not isinstance(raw_cells, list):
                raise LimiarMapClientError(
                    "LimiarMap obstacle is missing cells",
                    kind="payload",
                )

            cells: list[LimiarMapObstacleCell] = []
            for raw_cell in raw_cells:
                if not isinstance(raw_cell, dict):
                    raise LimiarMapClientError(
                        "LimiarMap obstacle cell is invalid",
                        kind="payload",
                    )
                x = raw_cell.get("x")
                y = raw_cell.get("y")
                if not isinstance(x, int) or not isinstance(y, int):
                    raise LimiarMapClientError(
                        "LimiarMap obstacle cell has invalid coordinates",
                        kind="payload",
                    )
                cells.append(LimiarMapObstacleCell(x=x, y=y))

            blocks_movement = obstacle_payload.get("blocksMovement", False)
            blocks_vision = obstacle_payload.get("blocksVision", False)
            # Authoritative field is `blocksEffect` (Phase 2 naming).
            # The `blocksTargeting` / `blocksSpell` fallback is retained only for
            # payloads persisted before the rename; new map-server writes always
            # emit `blocksEffect` exclusively.
            blocks_effect = obstacle_payload.get(
                "blocksEffect",
                obstacle_payload.get("blocksTargeting", obstacle_payload.get("blocksSpell", False)),
            )
            cover = obstacle_payload.get("cover")
            if not isinstance(blocks_movement, bool):
                raise LimiarMapClientError(
                    "LimiarMap obstacle has an invalid blocksMovement",
                    kind="payload",
                )
            if not isinstance(blocks_vision, bool):
                raise LimiarMapClientError(
                    "LimiarMap obstacle has an invalid blocksVision",
                    kind="payload",
                )
            if not isinstance(blocks_effect, bool):
                raise LimiarMapClientError(
                    "LimiarMap obstacle has an invalid blocksEffect",
                    kind="payload",
                )
            if cover is not None and not isinstance(cover, str):
                raise LimiarMapClientError(
                    "LimiarMap obstacle has an invalid cover",
                    kind="payload",
                )
            obstacles.append(
                LimiarMapObstacleState(
                    cells=tuple(cells),
                    blocks_movement=blocks_movement,
                    blocks_vision=blocks_vision,
                    blocks_effect=blocks_effect,
                    cover=cover,
                )
            )

        return LimiarMapStateResponse(
            session_id=session_id,
            version=version,
            tokens=tuple(tokens),
            grid_width=grid_width,
            grid_height=grid_height,
            obstacles=tuple(obstacles),
            active_combatant_id=active_combatant_id,
            round_number=round_number,
            turn_index=turn_index,
            initiative_order=initiative_order,
        )
