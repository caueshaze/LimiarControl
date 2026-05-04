from __future__ import annotations

from app.models.combat import CombatPhase

from .exceptions import CombatServiceError
from .limiar_map_projection import (
    maybe_project_combat_advance_to_limiar_map as _project_combat_advance_to_limiar_map,
    maybe_project_combat_end_to_limiar_map as _project_combat_end_to_limiar_map,
)
from .persistent_effects import persist_surviving_spell_effects


def maybe_project_combat_advance_to_limiar_map(session_id: str, state) -> None:
    from . import lifecycle as lifecycle_module

    projection = getattr(
        lifecycle_module,
        "maybe_project_combat_advance_to_limiar_map",
        _project_combat_advance_to_limiar_map,
    )
    if projection is not _project_combat_advance_to_limiar_map:
        projection(session_id, state)
        return
    _project_combat_advance_to_limiar_map(session_id, state)


def maybe_project_combat_end_to_limiar_map(session_id: str, state) -> None:
    from . import lifecycle as lifecycle_module

    projection = getattr(
        lifecycle_module,
        "maybe_project_combat_end_to_limiar_map",
        _project_combat_end_to_limiar_map,
    )
    if projection is not _project_combat_end_to_limiar_map:
        projection(session_id, state)
        return
    _project_combat_end_to_limiar_map(session_id, state)


class CombatLifecycleTurnsMixin:
    @classmethod
    async def next_turn(
        cls,
        db,
        session_id: str,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
        skip_turn_end_validation: bool = False,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)
        if not is_gm and not skip_turn_end_validation:
            if attacker.get("status") == "downed":
                raise CombatServiceError("You must roll a Death Save before ending your turn.", 403)
            cls._require_actor_status(attacker, ("active",), "You can only end your turn when active.")
        cls._clear_participant_pending_attack(attacker)
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(state, "participants")
        if not state.participants:
            raise CombatServiceError("No participants")
        outgoing = state.participants[state.current_turn_index]
        expired_end = await cls._expire_effects_for_participant(session_id, state, outgoing["id"], "turn_end")
        if expired_end:
            cls._execute_on_end_effects_for_removed(
                state=state,
                removed_effects=expired_end,
            )
        for effect in expired_end:
            label = effect.get("condition_type") or effect.get("kind", "effect")
            await cls._emit_log(session_id, {"message": f"Effect '{label}' expired on {effect['target_display_name']} (end of {outgoing['display_name']}'s turn).", "source": "effect_expired"})
        while True:
            state.current_turn_index += 1
            if state.current_turn_index >= len(state.participants):
                state.current_turn_index = 0
                state.round += 1
                await cls._emit_log(session_id, {"message": f"Round {state.round} started!"})
            status = state.participants[state.current_turn_index].get("status", "active")
            if status not in ("dead", "defeated", "stable"):
                break
            if status == "stable":
                await cls._emit_log(session_id, {"message": f"Turn skipped for stable participant {state.participants[state.current_turn_index]['display_name']}."})
        incoming = state.participants[state.current_turn_index]
        expired_start = await cls._expire_effects_for_participant(session_id, state, incoming["id"], "turn_start")
        if expired_start:
            cls._execute_on_end_effects_for_removed(
                state=state,
                removed_effects=expired_start,
            )
        for effect in expired_start:
            label = effect.get("condition_type") or effect.get("kind", "effect")
            await cls._emit_log(session_id, {"message": f"Effect '{label}' expired on {effect['target_display_name']} (start of {incoming['display_name']}'s turn).", "source": "effect_expired"})
        cls._reset_turn_resources(incoming)
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        maybe_project_combat_advance_to_limiar_map(session_id, state)
        active_name = state.participants[state.current_turn_index]["display_name"]
        if state.participants[state.current_turn_index].get("status") == "downed":
            await cls._emit_log(session_id, {"message": f"It is now {active_name}'s turn. They are downed and must roll a Death Save."})
        else:
            await cls._emit_log(session_id, {"message": f"It is now {active_name}'s turn."})
        return state

    @classmethod
    async def end_combat(cls, db, session_id: str, is_gm: bool):
        if not is_gm:
            raise CombatServiceError("Only GM can end combat", 403)
        state = cls.get_state(db, session_id)
        if not state:
            raise CombatServiceError("Combat not found", 404)

        concentration_source_ids: set[str] = set()
        for participant in state.participants:
            for effect in cls._get_participant_effects(participant):
                metadata = cls._get_effect_metadata(effect)
                if (
                    effect.get("source_participant_id")
                    and metadata.get("concentration") is True
                    and isinstance(metadata.get("concentration_group"), str)
                ):
                    concentration_source_ids.add(effect["source_participant_id"])

        all_removed: list[dict] = []
        for source_id in concentration_source_ids:
            result = cls._clear_concentration_for_source(state, source_participant_id=source_id)
            all_removed.extend(result["removed_effects"])

        persist_surviving_spell_effects(db, state)

        for participant in state.participants:
            remaining = cls._get_participant_effects(participant)
            all_removed.extend(
                {**effect, "target_participant_id": participant.get("id"), "target_display_name": participant.get("display_name", "")}
                for effect in remaining
            )
            cls._set_participant_effects(participant, [])
            participant.pop("pending_save", None)
            participant.pop("pending_attack", None)
            participant["turn_resources"] = dict(cls._DEFAULT_TURN_RESOURCES)

        state.phase = CombatPhase.ended
        state.active_area_effects = []

        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        maybe_project_combat_end_to_limiar_map(session_id, state)
        await cls._emit_log(session_id, {"message": "Combat ended."})
        return state

    @classmethod
    def _validate_distance_participant_refs(cls, state, entries) -> None:
        known_ref_ids = {participant.get("ref_id") for participant in state.participants if isinstance(participant.get("ref_id"), str)}
        for entry in entries:
            if entry.from_ref_id not in known_ref_ids:
                raise CombatServiceError(f"Participant {entry.from_ref_id!r} not found in combat.", 404)
            if entry.to_ref_id not in known_ref_ids:
                raise CombatServiceError(f"Participant {entry.to_ref_id!r} not found in combat.", 404)

    @classmethod
    def _apply_distance_entries(cls, state, entries) -> None:
        distances = state.local_distances if isinstance(state.local_distances, dict) else {}
        for entry in entries:
            distances.setdefault(entry.from_ref_id, {})[entry.to_ref_id] = entry.distance_meters
            distances.setdefault(entry.to_ref_id, {})[entry.from_ref_id] = entry.distance_meters
        state.local_distances = distances

    @classmethod
    async def update_distances(cls, db, session_id: str, req):
        state = cls.get_state(db, session_id)
        if not state:
            raise CombatServiceError("Combat not found", 404)
        if state.phase not in (CombatPhase.active, CombatPhase.initiative):
            raise CombatServiceError("Combat is not in an active or initiative phase")
        cls._validate_distance_participant_refs(state, req.distances)
        cls._apply_distance_entries(state, req.distances)
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(state, "local_distances")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        return state
