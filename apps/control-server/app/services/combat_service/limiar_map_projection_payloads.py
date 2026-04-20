from __future__ import annotations

from app.models.combat import CombatState


def _build_initiative_order(state: CombatState) -> list[str]:
    return [
        combatant_id
        for participant in state.participants
        if isinstance((combatant_id := participant.get("ref_id")), str)
        and combatant_id.strip()
    ]


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

    obstacles = raw_selection.get("obstacles")
    if isinstance(obstacles, list) and obstacles:
        payload["obstacles"] = obstacles
    else:
        blocked_cells = raw_selection.get("blockedCells")
        if isinstance(blocked_cells, list) and blocked_cells:
            payload["blockedCells"] = blocked_cells

    edge_obstacles = raw_selection.get("edgeObstacles")
    if isinstance(edge_obstacles, list) and edge_obstacles:
        payload["edgeObstacles"] = edge_obstacles

    return payload


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
