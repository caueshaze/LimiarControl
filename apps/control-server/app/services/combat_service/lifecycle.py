from __future__ import annotations

from app.models.combat import CombatPhase
from app.schemas.combat import CombatMapSelection
from app.services.game_time import get_game_time_seconds

from .lifecycle_initiative import CombatLifecycleInitiativeMixin
from .lifecycle_turns import CombatLifecycleTurnsMixin
from .limiar_map_projection import (
    maybe_project_combat_advance_to_limiar_map,
    maybe_project_combat_end_to_limiar_map,
    maybe_project_combat_start_to_limiar_map,
)


class CombatLifecycleMixin(CombatLifecycleInitiativeMixin, CombatLifecycleTurnsMixin):
    _INITIATIVE_SKIPPED_STATUSES = {"dead", "defeated", "stable"}
    _DEMO_MAP_SELECTION = CombatMapSelection(
        kind="demo_map",
        mapId=None,
        mapName="Demo Encounter",
        imageUrl="/maps/map.jpg",
        gridWidth=20,
        gridHeight=14,
        calibration={"x": 0, "y": 0, "width": 1, "height": 1},
    )

    @classmethod
    def _mark_active_combat_time_started(cls, db, session_id: str, state) -> None:
        state.active_started_at_game_time_seconds = get_game_time_seconds(session_id, db)
        state.accounted_game_time_rounds = 0

    @classmethod
    def _ensure_active_combat_time_accounting_started(cls, db, session_id: str, state) -> None:
        if state.phase not in (CombatPhase.active, "active"):
            return
        if state.active_started_at_game_time_seconds is not None:
            if not isinstance(state.accounted_game_time_rounds, int) or state.accounted_game_time_rounds < 0:
                state.accounted_game_time_rounds = 0
            return
        state.active_started_at_game_time_seconds = get_game_time_seconds(session_id, db)
        existing_accounted_rounds = state.accounted_game_time_rounds
        if not isinstance(existing_accounted_rounds, int) or existing_accounted_rounds < 0:
            existing_accounted_rounds = 0
        legacy_completed_rounds = max(0, int(getattr(state, "round", 1) or 1) - 1)
        state.accounted_game_time_rounds = max(existing_accounted_rounds, legacy_completed_rounds)
