from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified

from app.models.combat import CombatPhase
from app.schemas.combat import CombatMapSelection
from app.services.game_time import get_game_time_seconds
from app.services.persistent_effect_expiry import should_prune_timed_effect

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

    @classmethod
    def _prune_expired_timed_combat_effects(
        cls,
        db,
        session_id: str,
        state,
        *,
        game_time_seconds: int,
    ) -> dict:
        from .persistent_effects import sync_persisted_effects_from_combat_participants

        expired_concentration_groups: set[str] = set()
        removed_effects: list[dict] = []
        removed_area_effects: list[dict] = []
        changed = False

        for participant in state.participants:
            for effect in cls._get_participant_effects(participant):
                if not should_prune_timed_effect(effect, game_time_seconds):
                    continue
                metadata = cls._get_effect_metadata(effect)
                concentration_group = metadata.get("concentration_group")
                if metadata.get("concentration") is True and isinstance(concentration_group, str):
                    expired_concentration_groups.add(concentration_group)

        for concentration_group in expired_concentration_groups:
            result = cls._remove_effect_group(state, concentration_group=concentration_group)
            if result["removed_effects"] or result["removed_area_effects"]:
                changed = True
            removed_effects.extend(result["removed_effects"])
            removed_area_effects.extend(result["removed_area_effects"])

        for participant in state.participants:
            effects = cls._get_participant_effects(participant)
            if not effects:
                continue
            kept: list[dict] = []
            participant_changed = False
            for effect in effects:
                if should_prune_timed_effect(effect, game_time_seconds):
                    removed_effects.append(
                        {
                            **effect,
                            "target_participant_id": participant.get("id"),
                            "target_display_name": participant.get("display_name", ""),
                        }
                    )
                    participant_changed = True
                    continue
                kept.append(effect)
            if participant_changed:
                cls._set_participant_effects(participant, kept)
                changed = True

        if removed_effects:
            cls._execute_on_end_effects_for_removed(
                state=state,
                removed_effects=removed_effects,
            )
        if removed_area_effects:
            cls._sync_area_effects_if_changed(session_id, state, removed_area_effects)
        if changed:
            flag_modified(state, "participants")
        modified_states = sync_persisted_effects_from_combat_participants(
            db,
            state,
            game_time_seconds=game_time_seconds,
        ) if changed else []
        return {
            "changed": changed,
            "removed_effects": removed_effects,
            "removed_area_effects": removed_area_effects,
            "modified_states": modified_states,
        }
