from __future__ import annotations

from typing import Any

from .limiar_map_client_types import (
    LimiarMapAreaCell,
    LimiarMapAreaTargetingResponse,
    LimiarMapBatchTargetingResponse,
    LimiarMapBatchTargetingResult,
    LimiarMapClientError,
    LimiarMapMovementCell,
    LimiarMapMovementResponse,
    LimiarMapTargetingResponse,
)


def parse_targeting_response(
    payload: dict[str, Any],
) -> LimiarMapTargetingResponse:
    is_valid = payload.get("isValid")
    reason = payload.get("reason")
    session_id = payload.get("sessionId")
    action_id = payload.get("actionId")
    version = payload.get("version")
    source_token_id = payload.get("sourceTokenId")
    target_token_id = payload.get("targetTokenId")
    distance_cells = payload.get("distanceCells")

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
    if distance_cells is not None and not isinstance(distance_cells, int):
        raise LimiarMapClientError(
            "LimiarMap targeting response has an invalid distanceCells",
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
        distance_cells=distance_cells,
        cover=payload.get("cover") if isinstance(payload.get("cover"), str) else None,
    )


def parse_area_targeting_response(
    payload: dict[str, Any],
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


def parse_batch_targeting_response(
    payload: dict[str, Any],
) -> LimiarMapBatchTargetingResponse:
    session_id = payload.get("sessionId")
    action_id = payload.get("actionId")
    version = payload.get("version")
    raw_results = payload.get("results")

    if not isinstance(session_id, str) or not session_id.strip():
        raise LimiarMapClientError(
            "LimiarMap batch targeting response is missing sessionId",
            kind="payload",
        )
    if not isinstance(action_id, str) or not action_id.strip():
        raise LimiarMapClientError(
            "LimiarMap batch targeting response is missing actionId",
            kind="payload",
        )
    if not isinstance(version, int):
        raise LimiarMapClientError(
            "LimiarMap batch targeting response is missing version",
            kind="payload",
        )
    if not isinstance(raw_results, list):
        raise LimiarMapClientError(
            "LimiarMap batch targeting response is missing results",
            kind="payload",
        )

    results: list[LimiarMapBatchTargetingResult] = []
    for item in raw_results:
        if not isinstance(item, dict):
            raise LimiarMapClientError(
                "LimiarMap batch targeting response has an invalid result entry",
                kind="payload",
            )
        target_combatant_id = item.get("targetCombatantId")
        if not isinstance(target_combatant_id, str):
            raise LimiarMapClientError(
                "LimiarMap batch targeting result is missing targetCombatantId",
                kind="payload",
            )
        cover_raw = item.get("cover")
        cover = cover_raw if isinstance(cover_raw, str) else None
        results.append(LimiarMapBatchTargetingResult(
            target_combatant_id=target_combatant_id,
            cover=cover,
        ))

    return LimiarMapBatchTargetingResponse(
        session_id=session_id,
        action_id=action_id,
        version=version,
        results=tuple(results),
    )


def parse_movement_response(
    payload: dict[str, Any],
) -> LimiarMapMovementResponse:
    source_cell_payload = payload.get("sourceCell")
    destination_cell_payload = payload.get("destinationCell")
    path_payload = payload.get("path")

    if not isinstance(payload.get("isValid"), bool):
        raise LimiarMapClientError(
            "LimiarMap movement response is missing isValid",
            kind="payload",
        )
    if payload.get("reason") is not None and not isinstance(payload.get("reason"), str):
        raise LimiarMapClientError(
            "LimiarMap movement response has an invalid reason",
            kind="payload",
        )
    if not isinstance(payload.get("sessionId"), str) or not payload.get("sessionId"):
        raise LimiarMapClientError(
            "LimiarMap movement response is missing sessionId",
            kind="payload",
        )
    if not isinstance(payload.get("actionId"), str) or not payload.get("actionId"):
        raise LimiarMapClientError(
            "LimiarMap movement response is missing actionId",
            kind="payload",
        )
    if not isinstance(payload.get("version"), int):
        raise LimiarMapClientError(
            "LimiarMap movement response is missing version",
            kind="payload",
        )
    if not isinstance(destination_cell_payload, dict):
        raise LimiarMapClientError(
            "LimiarMap movement response is missing destinationCell",
            kind="payload",
        )
    if not isinstance(path_payload, list):
        raise LimiarMapClientError(
            "LimiarMap movement response is missing path",
            kind="payload",
        )

    def parse_cell(raw_cell: Any, field_name: str) -> LimiarMapMovementCell:
        if not isinstance(raw_cell, dict):
            raise LimiarMapClientError(
                f"LimiarMap movement response has an invalid {field_name}",
                kind="payload",
            )
        x = raw_cell.get("x")
        y = raw_cell.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            raise LimiarMapClientError(
                f"LimiarMap movement response has an invalid {field_name}",
                kind="payload",
            )
        return LimiarMapMovementCell(x=x, y=y)

    return LimiarMapMovementResponse(
        is_valid=bool(payload.get("isValid")),
        reason=payload.get("reason") if isinstance(payload.get("reason"), str) else None,
        session_id=str(payload["sessionId"]),
        action_id=str(payload["actionId"]),
        version=int(payload["version"]),
        token_id=str(payload["tokenId"]) if payload.get("tokenId") is not None else None,
        combatant_id=(
            str(payload["combatantId"]) if payload.get("combatantId") is not None else None
        ),
        source_cell=(
            parse_cell(source_cell_payload, "sourceCell")
            if source_cell_payload is not None
            else None
        ),
        destination_cell=parse_cell(destination_cell_payload, "destinationCell"),
        path=tuple(parse_cell(raw_cell, "path cell") for raw_cell in path_payload),
        path_cost_units=int(payload.get("pathCostUnits") or 0),
        movement_budget=int(payload.get("movementBudget") or 0),
        movement_speed_cells=max(1, int(payload.get("movementSpeedCells") or 1)),
        remaining_budget=int(payload.get("remainingBudget") or 0),
    )
