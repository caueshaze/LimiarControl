from __future__ import annotations

from app.models.combat import CombatPhase
from app.services.game_time import (
    COMBAT_ROUND_GAME_TIME_SECONDS,
    advance_game_time_seconds,
    get_game_time_seconds,
)
from app.services.combat_service.condition_effects_saves import modify_saving_throw
from app.services.roll_resolution import resolve_saving_throw

from .exceptions import CombatServiceError
from .limiar_map_projection import (
    maybe_project_combat_advance_to_limiar_map as _project_combat_advance_to_limiar_map,
    maybe_project_combat_end_to_limiar_map as _project_combat_end_to_limiar_map,
)
from .persistent_effects import persist_surviving_spell_effects
from .spell_anchors import tick_spell_anchors_for_turn


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
    async def _resolve_turn_end_repeat_saves(
        cls,
        db,
        session_id: str,
        state,
        participant: dict,
    ) -> None:
        effects = cls._get_participant_effects(participant)
        for effect in list(effects):
            effect_id = effect.get("id")
            metadata = cls._get_effect_metadata(effect)
            repeat_save = metadata.get("repeat_save")
            if not isinstance(effect_id, str) or not isinstance(repeat_save, dict):
                continue
            if repeat_save.get("timing") != "target_turn_end":
                continue
            ability = str(repeat_save.get("ability") or "").strip().lower()
            dc = cls._safe_int(repeat_save.get("dc"), 0)
            if ability not in cls._ENTITY_ABILITY_ALIASES or dc <= 0:
                continue

            save_mod = modify_saving_throw(participant, ability)
            roll_result = resolve_saving_throw(
                cls._build_roll_actor_stats_for_save(
                    db,
                    session_id,
                    participant["ref_id"],
                    participant["kind"],
                    participant["display_name"],
                ),
                ability=ability,
                advantage_mode=save_mod.result,
                dc=dc,
                roll_source="system",
            )
            is_saved = False if save_mod.auto_fail else bool(roll_result.success)
            if is_saved and repeat_save.get("ends_on_success", True):
                participant["active_effects"] = [
                    e for e in cls._get_participant_effects(participant) if e.get("id") != effect_id
                ]
                concentration_group = metadata.get("concentration_group")
                if isinstance(concentration_group, str):
                    still_has_group = any(
                        isinstance(cls._get_effect_metadata(e).get("concentration_group"), str)
                        and cls._get_effect_metadata(e).get("concentration_group") == concentration_group
                        for p in state.participants
                        for e in cls._get_participant_effects(p)
                    )
                    if not still_has_group and isinstance(metadata.get("source_participant_id"), str):
                        cls._clear_concentration_for_source(
                            state,
                            source_participant_id=metadata.get("source_participant_id"),
                            db=db,
                        )
                await cls._emit_log(
                    session_id,
                    {
                        "message": (
                            f"{participant['display_name']} passou na salvaguarda de {ability} "
                            f"e deixou de estar paralisado."
                        ),
                        "source": "repeat_save_resolve",
                    },
                )
            else:
                await cls._emit_log(
                    session_id,
                    {
                        "message": (
                            f"{participant['display_name']} falhou na salvaguarda de {ability} "
                            f"e continua paralisado."
                        ),
                        "source": "repeat_save_resolve",
                    },
                )

    @classmethod
    async def _process_recurring_temp_hp(
        cls,
        db,
        session_id: str,
        state,
        participant: dict,
    ) -> None:
        from app.services.session_state_finalize import finalize_session_state_data
        from sqlalchemy.orm.attributes import flag_modified as _flag_modified

        effects = cls._get_participant_effects(participant)
        for effect in effects:
            metadata = cls._get_effect_metadata(effect)
            if not metadata.get("recurring_temp_hp"):
                continue
            temp_hp_per_turn = cls._safe_int(metadata.get("temp_hp_per_turn"), 0)
            if temp_hp_per_turn <= 0:
                continue
            target_ref_id = metadata.get("effect_target_ref_id")
            target_kind = None
            for p in state.participants:
                if p.get("ref_id") == target_ref_id or p.get("id") == metadata.get("effect_target_participant_id"):
                    target_kind = p.get("kind")
                    target_ref_id = p.get("ref_id")
                    break
            if target_kind == "player" and target_ref_id:
                try:
                    target_model, *_ = cls._get_stats(db, target_ref_id, "player", session_id)
                    data = cls._as_dict(target_model.state_json)
                    previous = max(0, cls._safe_int(data.get("tempHP"), 0))
                    final = max(previous, temp_hp_per_turn)
                    metadata["last_granted_temp_hp"] = temp_hp_per_turn
                    if final > previous:
                        data["tempHP"] = final
                        target_model.state_json = finalize_session_state_data(data)
                        _flag_modified(target_model, "state_json")
                        if db is not None:
                            db.add(target_model)
                    spell_name = metadata.get("source_spell_name") or "Spell"
                    await cls._emit_log(
                        session_id,
                        {
                            "message": f"{participant['display_name']} ganhou {temp_hp_per_turn} PV temporários de {spell_name}.",
                            "source": "recurring_temp_hp",
                        },
                    )
                except Exception:
                    pass

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
        cls._ensure_active_combat_time_accounting_started(db, session_id, state)
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
        expired_anchor_end = tick_spell_anchors_for_turn(
            state,
            participant_id=outgoing["id"],
            trigger="turn_end",
        )
        if expired_end:
            cls._execute_on_end_effects_for_removed(
                state=state,
                removed_effects=expired_end,
            )
        for effect in expired_end:
            label = effect.get("condition_type") or effect.get("kind", "effect")
            await cls._emit_log(session_id, {"message": f"Effect '{label}' expired on {effect['target_display_name']} (end of {outgoing['display_name']}'s turn).", "source": "effect_expired"})
        for anchor in expired_anchor_end:
            label = anchor.get("source_spell_name") or anchor.get("source_spell_key") or "Spell anchor"
            await cls._emit_log(session_id, {"message": f"Spell anchor '{label}' expired (end of {outgoing['display_name']}'s turn).", "source": "effect_expired"})
        await cls._resolve_turn_end_repeat_saves(db, session_id, state, outgoing)
        while True:
            state.current_turn_index += 1
            if state.current_turn_index >= len(state.participants):
                state.current_turn_index = 0
                state.round += 1
                completed_round_count = max(0, state.round - 1)
                if state.accounted_game_time_rounds < completed_round_count:
                    missing_rounds = completed_round_count - state.accounted_game_time_rounds
                    advance_game_time_seconds(
                        session_id,
                        missing_rounds * COMBAT_ROUND_GAME_TIME_SECONDS,
                        db,
                    )
                    state.accounted_game_time_rounds += missing_rounds
                    cls._prune_expired_timed_combat_effects(
                        db,
                        session_id,
                        state,
                        game_time_seconds=get_game_time_seconds(session_id, db),
                    )
                await cls._emit_log(session_id, {"message": f"Round {state.round} started!"})
            status = state.participants[state.current_turn_index].get("status", "active")
            if status not in ("dead", "defeated", "stable"):
                break
            if status == "stable":
                await cls._emit_log(session_id, {"message": f"Turn skipped for stable participant {state.participants[state.current_turn_index]['display_name']}."})
        incoming = state.participants[state.current_turn_index]
        expired_start = await cls._expire_effects_for_participant(session_id, state, incoming["id"], "turn_start")
        expired_anchor_start = tick_spell_anchors_for_turn(
            state,
            participant_id=incoming["id"],
            trigger="turn_start",
        )
        if expired_start:
            cls._execute_on_end_effects_for_removed(
                state=state,
                removed_effects=expired_start,
            )
        for effect in expired_start:
            label = effect.get("condition_type") or effect.get("kind", "effect")
            await cls._emit_log(session_id, {"message": f"Effect '{label}' expired on {effect['target_display_name']} (start of {incoming['display_name']}'s turn).", "source": "effect_expired"})
        for anchor in expired_anchor_start:
            label = anchor.get("source_spell_name") or anchor.get("source_spell_key") or "Spell anchor"
            await cls._emit_log(session_id, {"message": f"Spell anchor '{label}' expired (start of {incoming['display_name']}'s turn).", "source": "effect_expired"})
        cls._reset_turn_resources(incoming)
        await cls._process_recurring_temp_hp(db, session_id, state, incoming)
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
        if state.phase in (CombatPhase.active, "active"):
            cls._ensure_active_combat_time_accounting_started(db, session_id, state)
            started_rounds = max(1, state.round)
            missing_rounds = started_rounds - state.accounted_game_time_rounds
            if missing_rounds > 0:
                advance_game_time_seconds(
                    session_id,
                    missing_rounds * COMBAT_ROUND_GAME_TIME_SECONDS,
                    db,
                )
                state.accounted_game_time_rounds += missing_rounds
                cls._prune_expired_timed_combat_effects(
                    db,
                    session_id,
                    state,
                    game_time_seconds=get_game_time_seconds(session_id, db),
                )

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
            result = cls._clear_concentration_for_source(state, source_participant_id=source_id, db=db)
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
        state.spell_anchors = []

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
