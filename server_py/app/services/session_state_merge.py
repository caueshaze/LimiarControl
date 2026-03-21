from __future__ import annotations

from app.services.session_rest import ensure_rest_state


def merge_session_state_data(
    state_data: dict | None,
    base_sheet_data: dict | None,
) -> dict:
    next_state = ensure_rest_state(state_data if isinstance(state_data, dict) else {})
    if not isinstance(base_sheet_data, dict):
        return next_state

    for key, value in base_sheet_data.items():
        if key not in next_state:
            next_state[key] = value
    return next_state
