from __future__ import annotations

import logging
from copy import deepcopy
from typing import Literal
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.base_spell import SpellDeclarativeEffect
from app.services.game_time import get_game_time_seconds
from app.services.out_of_combat_cast import _target_has_armor, _check_requires_unarmored_eligibility

logger = logging.getLogger(__name__)
from app.schemas.campaign_entity_shared import AbilityName, SKILL_ABILITY_MAP, SkillName
from .condition_effects_predicates import (
    explain_check_modifier_sources,
    get_roll_bonus_dice_sources,
    has_condition_immunity,
    has_condition_immunity_from_source,
    resolve_actor_participant,
    resolve_check_advantage_mode,
)
from .condition_effects_saves import modify_saving_throw
from .exceptions import CombatServiceError, _roll_dice_expression


class CombatSpellDeclarativeEffectsMixin:
    @classmethod
    def _apply_roll_bonus_dice_to_roll_result(
        cls,
        *,
        participant: dict,
        roll_result,
        roll_type: Literal["attack", "save", "ability", "skill"],
        state: CombatState | None = None,
    ) -> list[str]:
        sources = get_roll_bonus_dice_sources(participant, roll_type=roll_type)
        if not sources:
            return []
        extra_total = sum(int(s.get("signed_total") or 0) for s in sources)
        roll_result.total = int(roll_result.total) + extra_total
        merged = list(roll_result.check_modifier_sources or [])
        merged.extend(sources)
        roll_result.check_modifier_sources = merged
        if roll_type == "attack" and roll_result.target_ac is not None:
            if roll_result.selected_roll == 20:
                roll_result.success = True
            elif roll_result.selected_roll == 1:
                roll_result.success = False
            else:
                roll_result.success = roll_result.total >= roll_result.target_ac
        elif roll_type == "save" and roll_result.dc is not None:
            roll_result.success = roll_result.total >= roll_result.dc
        elif roll_type in {"ability", "skill"} and roll_result.dc is not None:
            roll_result.success = roll_result.total >= roll_result.dc

        consumed_effect_ids: list[str] = []
        for source in sources:
            if source.get("consume_on_apply") is not True:
                continue
            effect_id = source.get("effect_id")
            if isinstance(effect_id, str) and effect_id and effect_id not in consumed_effect_ids:
                consumed_effect_ids.append(effect_id)
        if not consumed_effect_ids:
            return []

        effects = cls._get_participant_effects(participant)
        if effects:
            kept = [e for e in effects if e.get("id") not in set(consumed_effect_ids)]
            cls._set_participant_effects(participant, kept)
            if state is not None:
                flag_modified(state, "participants")
        return consumed_effect_ids

    @classmethod
    def _apply_roll_dice_modifiers_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        roll_result,
        roll_type: Literal["attack", "save", "ability", "skill"],
    ) -> list[str]:
        state = cls.get_state(db, session_id)
        if state is None or state.phase == CombatPhase.ended:
            return []
        participant = resolve_actor_participant(state, actor_ref_id)
        if not isinstance(participant, dict) or participant.get("kind") != actor_kind:
            return []
        consumed_effect_ids = cls._apply_roll_bonus_dice_to_roll_result(
            participant=participant,
            roll_result=roll_result,
            roll_type=roll_type,
            state=state,
        )
        if consumed_effect_ids:
            db.add(state)
            db.commit()
            db.refresh(state)
        return consumed_effect_ids

    @classmethod
    def _build_temp_hp_observability_from_metadata(
        cls,
        metadata: dict,
    ) -> dict | None:
        rolled = metadata.get("rolled_temp_hp")
        if not isinstance(rolled, int):
            return None
        observability = {
            "rolled_temp_hp": rolled,
            "applied_temp_hp": metadata.get("applied_temp_hp") is True,
            "previous_temp_hp": metadata.get("previous_temp_hp")
            if isinstance(metadata.get("previous_temp_hp"), int)
            else None,
            "final_temp_hp": metadata.get("final_temp_hp")
            if isinstance(metadata.get("final_temp_hp"), int)
            else None,
            "does_not_expire_temp_hp": metadata.get("does_not_expire_temp_hp") is True,
        }
        return observability

    @classmethod
    def _format_temp_hp_observability_compact(
        cls,
        observability: dict | None,
    ) -> str | None:
        if not isinstance(observability, dict):
            return None
        rolled = observability.get("rolled_temp_hp")
        previous = observability.get("previous_temp_hp")
        final = observability.get("final_temp_hp")
        if not isinstance(rolled, int):
            return None
        if isinstance(previous, int) and isinstance(final, int) and final <= previous:
            return f"PV temporários: {rolled} rolados, mantidos {previous} existentes"
        if isinstance(final, int):
            return f"PV temporários: +{rolled} (final: {final})"
        return f"PV temporários: +{rolled}"

    @classmethod
    def _format_applied_declarative_effects_for_log(
        cls,
        applied_declarative_effects_by_target: list[dict] | None,
    ) -> str:
        if not isinstance(applied_declarative_effects_by_target, list):
            return ""
        chunks: list[str] = []
        for entry in applied_declarative_effects_by_target:
            if not isinstance(entry, dict):
                continue
            target_name = entry.get("target_display_name")
            if not isinstance(target_name, str) or not target_name.strip():
                target_name = "Target"
            for effect in entry.get("effects") or []:
                if not isinstance(effect, dict) or effect.get("type") != "grant_temp_hp":
                    continue
                summary = cls._format_temp_hp_observability_compact(effect.get("observability"))
                if summary:
                    chunks.append(f"{target_name}: {summary}")
        return f" {'; '.join(chunks)}." if chunks else ""

    @classmethod
    def _build_applied_declarative_effects_by_target(
        cls,
        applied_effects: list[dict] | None,
    ) -> list[dict]:
        if not isinstance(applied_effects, list) or not applied_effects:
            return []

        grouped: dict[tuple[str | None, str | None, str], dict] = {}
        for active_effect in applied_effects:
            if not isinstance(active_effect, dict):
                continue
            metadata = cls._get_effect_metadata(active_effect)
            declarative = metadata.get("declarative_effect")
            if not isinstance(declarative, dict):
                continue

            target_participant_id = metadata.get("effect_target_participant_id")
            if not isinstance(target_participant_id, str):
                target_participant_id = None
            target_ref_id = metadata.get("effect_target_ref_id")
            if not isinstance(target_ref_id, str):
                target_ref_id = None
            target_display_name = metadata.get("effect_target_display_name")
            if not isinstance(target_display_name, str) or not target_display_name.strip():
                target_display_name = (
                    target_participant_id
                    or target_ref_id
                    or "Target"
                )
            key = (target_participant_id, target_ref_id, target_display_name)
            target_entry = grouped.setdefault(
                key,
                {
                    "target_display_name": target_display_name,
                    "target_participant_id": target_participant_id,
                    "target_ref_id": target_ref_id,
                    "variant_key": metadata.get("selected_variant_key"),
                    "variant_label": metadata.get("selected_variant_label"),
                    "effects": [],
                },
            )
            effect_summary = {
                "type": declarative.get("type"),
                "params": declarative.get("params")
                if isinstance(declarative.get("params"), dict)
                else {},
            }
            observability = (
                cls._build_temp_hp_observability_from_metadata(metadata)
                if declarative.get("type") == "grant_temp_hp"
                else None
            )
            if observability is not None:
                effect_summary["observability"] = observability
            target_entry["effects"].append(effect_summary)
        return list(grouped.values())

    @classmethod
    def _check_declarative_requires_unarmored_for_target(
        cls,
        db,
        session_id: str,
        *,
        spell_context: dict,
        target_participant: dict | None,
    ) -> None:
        """Raise CombatServiceError if any declarative effect requires unarmored and target has armor."""
        effects = spell_context.get("effects") or []
        if not isinstance(effects, list):
            return
        requires_unarmored = any(
            isinstance(e, dict) and (e.get("params") or {}).get("requires_unarmored") is True
            for e in effects
        )
        if not requires_unarmored:
            return
        if not isinstance(target_participant, dict) or target_participant.get("kind") != "player":
            return
        ref_id = target_participant.get("ref_id")
        if not ref_id:
            return
        from sqlmodel import select as sa_select
        session_state = db.exec(
            sa_select(SessionState).where(
                SessionState.session_id == session_id,
                SessionState.player_user_id == ref_id,
            )
        ).first()
        target_state_json = dict(session_state.state_json or {}) if session_state else {}
        if _target_has_armor(target_state_json):
            raise CombatServiceError(
                "Target is wearing armor and this spell requires an unarmored target", 400
            )

    @classmethod
    def _normalize_declarative_effects(cls, raw_effects: object) -> list[SpellDeclarativeEffect]:
        if not isinstance(raw_effects, list):
            return []
        normalized: list[SpellDeclarativeEffect] = []
        for entry in raw_effects:
            if not isinstance(entry, dict):
                continue
            normalized.append(SpellDeclarativeEffect.model_validate(entry))
        return normalized

    @classmethod
    def _spell_context_declarative_effects(cls, spell_context: dict) -> list[SpellDeclarativeEffect]:
        return cls._normalize_declarative_effects(spell_context.get("effects"))

    @classmethod
    def _spell_context_on_end_effects(cls, spell_context: dict) -> list[SpellDeclarativeEffect]:
        return cls._normalize_declarative_effects(spell_context.get("on_end_effects"))

    @classmethod
    def _spell_context_has_declarative_effects(cls, spell_context: dict) -> bool:
        return bool(cls._spell_context_declarative_effects(spell_context))

    @classmethod
    def _resolve_declarative_effect_target(
        cls,
        *,
        state,
        attacker: dict,
        target_participant: dict | None,
        effect: SpellDeclarativeEffect,
        metadata: dict,
    ) -> dict | None:
        participant_id = (
            metadata.get("selected_target_participant_id")
            if effect.target == "selected_target"
            else metadata.get("caster_participant_id")
        )
        if isinstance(participant_id, str):
            found = cls._find_participant_by_id(state, participant_id)
            if found is not None:
                return found
        if effect.target == "selected_target" and target_participant is None:
            raise CombatServiceError(
                "Declarative spell effect requires a selected target.", 400
            )
        if effect.target == "caster":
            return attacker
        return target_participant

    @classmethod
    def _declarative_duration_kwargs(
        cls,
        *,
        effect: SpellDeclarativeEffect,
        attacker: dict,
        target_participant: dict | None,
        game_time_seconds: int | None = None,
    ) -> dict:
        duration = effect.duration
        if duration is None:
            return {
                "duration_type": "manual",
                "remaining_rounds": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": None,
                "expires_at_game_time_seconds": None,
            }
        if duration.type == "timed":
            gt = game_time_seconds if isinstance(game_time_seconds, int) else 0
            return {
                "duration_type": "timed",
                "remaining_rounds": None,
                "expires_at_participant_id": None,
                "created_at_game_time_seconds": gt,
                "expires_at_game_time_seconds": gt + (duration.seconds or 0),
            }
        anchor = duration.anchor or "target"
        expires_at = (
            attacker.get("id")
            if anchor == "caster"
            else target_participant.get("id") if isinstance(target_participant, dict) else None
        )
        return {
            "duration_type": duration.type,
            "remaining_rounds": duration.rounds,
            "expires_at_participant_id": expires_at,
            "created_at_game_time_seconds": None,
            "expires_at_game_time_seconds": None,
        }

    @classmethod
    def _replace_matching_effects(cls, participant: dict, effect_type: str, params: dict) -> None:
        keep: list[dict] = []
        for existing in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(existing)
            declarative = metadata.get("declarative_effect")
            if (
                isinstance(declarative, dict)
                and declarative.get("type") == effect_type
                and declarative.get("params") == params
            ):
                continue
            keep.append(existing)
        cls._set_participant_effects(participant, keep)

    @classmethod
    def _replace_enlarge_reduce_size_modifier(cls, participant: dict) -> None:
        keep: list[dict] = []
        for existing in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(existing)
            declarative = metadata.get("declarative_effect")
            if (
                existing.get("kind") == "size_modifier"
                and metadata.get("source_spell_key") == "enlarge_reduce"
                and isinstance(declarative, dict)
                and declarative.get("type") == "size_modifier"
            ):
                continue
            keep.append(existing)
        cls._set_participant_effects(participant, keep)

    @classmethod
    def _apply_single_declarative_effect(
        cls,
        *,
        state,
        attacker: dict,
        target_participant: dict | None,
        spell_context: dict,
        effect: SpellDeclarativeEffect,
        effect_group_id: str,
        on_end_effects: list[SpellDeclarativeEffect],
        game_time_seconds: int | None = None,
    ) -> list[dict]:
        metadata = {
            "declarative_effect_group_id": effect_group_id,
            "declarative_effect": effect.model_dump(mode="json", exclude_none=True),
            "declarative_on_end_effects": [
                entry.model_dump(mode="json", exclude_none=True) for entry in on_end_effects
            ],
            "caster_participant_id": attacker.get("id"),
            "selected_target_participant_id": target_participant.get("id")
            if isinstance(target_participant, dict)
            else None,
            "selected_target_ref_id": target_participant.get("ref_id")
            if isinstance(target_participant, dict)
            else None,
            "selected_target_display_name": target_participant.get("display_name")
            if isinstance(target_participant, dict)
            else None,
            "source_spell_key": spell_context.get("spell_canonical_key"),
            "source_spell_name": spell_context.get("spell_name"),
            "selected_variant_key": spell_context.get("selected_variant_key"),
            "selected_variant_label": spell_context.get("selected_variant_label"),
            "target_assignment_source": spell_context.get("variant_scope"),
            "context_origin": spell_context.get("context_origin") or "initial_cast",
            "concentration": bool(spell_context.get("concentration")),
            "concentration_group": effect_group_id if spell_context.get("concentration") else None,
        }
        if effect.repeat_save is not None:
            metadata["repeat_save"] = effect.repeat_save.model_dump(mode="json")
        resolved_target = cls._resolve_declarative_effect_target(
            state=state,
            attacker=attacker,
            target_participant=target_participant,
            effect=effect,
            metadata=metadata,
        )
        if resolved_target is None:
            return []
        metadata["effect_target_participant_id"] = resolved_target.get("id")
        metadata["effect_target_ref_id"] = resolved_target.get("ref_id")
        metadata["effect_target_display_name"] = resolved_target.get("display_name")
        if effect.type == "attack_advantage_against_target":
            metadata["marked_target_participant_id"] = resolved_target.get("id")

        params = effect.params.model_dump(mode="json", exclude_none=True)
        if effect.type in {"advantage_on_checks", "disadvantage_on_checks"}:
            metadata["against"] = params.get("against") or "any"
        if effect.type == "size_modifier" and metadata.get("source_spell_key") == "enlarge_reduce":
            cls._replace_enlarge_reduce_size_modifier(resolved_target)
        if effect.stacking == "replace" and effect.type != "size_modifier":
            cls._replace_matching_effects(resolved_target, effect.type, params)

        duration_kwargs = cls._declarative_duration_kwargs(
            effect=effect,
            attacker=attacker,
            target_participant=resolved_target,
            game_time_seconds=game_time_seconds,
        )

        created: list[dict] = []
        if effect.type == "apply_condition":
            condition_type = params["condition"]
            if has_condition_immunity_from_source(resolved_target, condition_type, source_participant=attacker):
                return []
            active_effect = cls._build_active_effect(
                kind="condition",
                source_participant_id=attacker.get("id"),
                condition_type=condition_type,
                metadata=metadata,
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        elif effect.type == "condition_immunity":
            immune_conditions: list[str] = params.get("conditions") or []
            active_effect = cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker.get("id"),
                metadata={
                    **metadata,
                    "condition_immunity": True,
                    "immune_conditions": immune_conditions,
                },
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
            # Suppress any matching conditions already present on the target
            existing_effects = cls._get_participant_effects(resolved_target)
            kept = [
                e for e in existing_effects
                if not (e.get("kind") == "condition" and e.get("condition_type") in immune_conditions)
            ]
            cls._set_participant_effects(resolved_target, kept)
        elif effect.type == "modify_stat":
            active_effect = cls._build_active_effect(
                kind=params["stat"],
                source_participant_id=attacker.get("id"),
                numeric_value=params["value"],
                metadata=metadata,
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        elif effect.type == "grant_temp_hp":
            rolled = _roll_dice_expression(params["dice"])
            upcast_bonus = int(spell_context.get("effect_bonus") or 0)
            if upcast_bonus:
                rolled += upcast_bonus
            active_effect = cls._build_active_effect(
                kind="temp_hp_granted",
                source_participant_id=attacker.get("id"),
                numeric_value=rolled,
                metadata={
                    **metadata,
                    "rolled_temp_hp": rolled,
                    "does_not_expire_temp_hp": True,
                    "applied_temp_hp": False,
                },
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        elif effect.type == "size_modifier":
            active_effect = cls._build_active_effect(
                kind="size_modifier",
                source_participant_id=attacker.get("id"),
                numeric_value=params["value"],
                metadata=metadata,
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        elif effect.type == "recurring_temp_hp":
            amount_source = params.get("amount_source")
            if amount_source == "caster_spellcasting_modifier":
                temp_hp_per_turn = max(0, int(spell_context.get("caster_spell_mod") or 0))
            else:
                temp_hp_per_turn = 0
            active_effect = cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker.get("id"),
                metadata={
                    **metadata,
                    "recurring_temp_hp": True,
                    "temp_hp_per_turn": temp_hp_per_turn,
                    "last_granted_temp_hp": 0,
                    "remove_granted_temp_hp_on_end": params.get("remove_granted_temp_hp_on_end", True),
                },
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        else:
            active_effect = cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker.get("id"),
                metadata={**metadata, **params},
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        return created

    @classmethod
    def _apply_declarative_spell_effects(
        cls,
        *,
        state,
        attacker: dict,
        target_participant: dict | None,
        spell_context: dict,
        effect_group_id: str | None = None,
        game_time_seconds: int | None = None,
    ) -> dict:
        effects = cls._spell_context_declarative_effects(spell_context)
        on_end_effects = cls._spell_context_on_end_effects(spell_context)
        if not effects:
            return {"applied_effects": [], "effect_group_id": None}

        participant_snapshot = deepcopy(state.participants)
        effect_group_id = effect_group_id or str(uuid4())
        applied: list[dict] = []
        try:
            for effect in effects:
                applied.extend(
                    cls._apply_single_declarative_effect(
                        state=state,
                        attacker=attacker,
                        target_participant=target_participant,
                        spell_context=spell_context,
                        effect=effect,
                        effect_group_id=effect_group_id,
                        on_end_effects=on_end_effects,
                        game_time_seconds=game_time_seconds,
                    )
                )
            if any(effect.get("kind") == "size_modifier" for effect in applied):
                from .limiar_map_projection import maybe_sync_conditions_to_limiar_map

                maybe_sync_conditions_to_limiar_map(
                    state.session_id,
                    state,
                    raise_on_error=True,
                )
        except Exception:
            state.participants = participant_snapshot
            raise
        return {"applied_effects": applied, "effect_group_id": effect_group_id}

    @classmethod
    def _execute_on_end_effects_for_removed(
        cls,
        *,
        state,
        removed_effects: list[dict],
    ) -> list[dict]:
        executed: list[dict] = []
        processed_groups: set[str] = set()
        for removed in removed_effects:
            metadata = cls._get_effect_metadata(removed)
            group_id = metadata.get("declarative_effect_group_id")
            if isinstance(group_id, str) and group_id in processed_groups:
                continue
            if isinstance(group_id, str):
                processed_groups.add(group_id)

            raw_on_end = metadata.get("declarative_on_end_effects")
            if not isinstance(raw_on_end, list) or not raw_on_end:
                continue

            caster = cls._find_participant_by_id(state, metadata.get("caster_participant_id"))
            target = cls._find_participant_by_id(
                state, metadata.get("selected_target_participant_id")
            )
            if caster is None:
                continue

            pseudo_context = {
                "spell_canonical_key": metadata.get("source_spell_key"),
                "spell_name": metadata.get("source_spell_name"),
                "concentration": False,
            }
            for effect in cls._normalize_declarative_effects(raw_on_end):
                executed.extend(
                    cls._apply_single_declarative_effect(
                        state=state,
                        attacker=caster,
                        target_participant=target,
                        spell_context=pseudo_context,
                        effect=effect,
                        effect_group_id=str(uuid4()),
                        on_end_effects=[],
                    )
                )
        return executed

    @classmethod
    def _apply_temp_hp_from_granted_effects(cls, db, state, applied_effects: list[dict]) -> None:
        from app.services.session_state_finalize import finalize_session_state_data
        from sqlalchemy.orm.attributes import flag_modified

        for effect in applied_effects:
            if effect.get("kind") != "temp_hp_granted":
                continue
            metadata = cls._get_effect_metadata(effect)
            if metadata.get("applied_temp_hp"):
                continue
            rolled = metadata.get("rolled_temp_hp")
            if not isinstance(rolled, int) or rolled <= 0:
                continue
            target_participant_id = metadata.get("effect_target_participant_id")
            target_ref_id = metadata.get("effect_target_ref_id")
            target_kind = None
            for p in (state.participants if state else []):
                if p.get("id") == target_participant_id or p.get("ref_id") == target_ref_id:
                    target_kind = p.get("kind")
                    target_ref_id = p.get("ref_id")
                    break
            if not target_ref_id or not target_kind:
                continue
            previous_temp_hp = 0
            final_temp_hp = rolled
            if target_kind == "player":
                try:
                    target_model, *_ = cls._get_stats(db, target_ref_id, "player", state.session_id if state else "")
                    data = cls._as_dict(target_model.state_json)
                    previous_temp_hp = max(0, cls._safe_int(data.get("tempHP"), 0))
                    final_temp_hp = max(previous_temp_hp, rolled)
                    if final_temp_hp > previous_temp_hp:
                        data["tempHP"] = final_temp_hp
                        target_model.state_json = finalize_session_state_data(data)
                        flag_modified(target_model, "state_json")
                        db.add(target_model)
                        if state:
                            flag_modified(state, "participants")
                            db.add(state)
                except Exception:
                    pass
            metadata["applied_temp_hp"] = True
            metadata["previous_temp_hp"] = previous_temp_hp
            metadata["final_temp_hp"] = final_temp_hp

    @classmethod
    def _cleanup_recurring_temp_hp_effects(
        cls,
        db,
        state,
        removed_effects: list[dict],
    ) -> None:
        from app.services.session_state_finalize import finalize_session_state_data
        from sqlalchemy.orm.attributes import flag_modified as _flag_modified

        for effect in removed_effects:
            metadata = cls._get_effect_metadata(effect)
            if not metadata.get("recurring_temp_hp"):
                continue
            if not metadata.get("remove_granted_temp_hp_on_end"):
                continue
            last_granted = cls._safe_int(metadata.get("last_granted_temp_hp"), 0)
            if last_granted <= 0:
                continue
            target_ref_id = metadata.get("effect_target_ref_id")
            target_kind = None
            for p in (state.participants if state else []):
                if p.get("ref_id") == target_ref_id or p.get("id") == metadata.get("effect_target_participant_id"):
                    target_kind = p.get("kind")
                    target_ref_id = p.get("ref_id")
                    break
            if target_kind != "player" or not target_ref_id:
                continue
            try:
                session_id = state.session_id if state else ""
                target_model, *_ = cls._get_stats(db, target_ref_id, "player", session_id)
                data = cls._as_dict(target_model.state_json)
                current_temp_hp = max(0, cls._safe_int(data.get("tempHP"), 0))
                if current_temp_hp <= last_granted:
                    data["tempHP"] = 0
                    target_model.state_json = finalize_session_state_data(data)
                    _flag_modified(target_model, "state_json")
                    db.add(target_model)
            except Exception:
                pass

    @classmethod
    async def _cast_spell_via_declarative_effects(
        cls,
        db,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state,
        spell_context: dict,
        target_participant: dict | None,
        effect_group_id: str | None = None,
    ) -> dict | None:
        if not cls._spell_context_has_declarative_effects(spell_context):
            return None

        application = cls._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target_participant,
            spell_context=spell_context,
            effect_group_id=effect_group_id,
            game_time_seconds=get_game_time_seconds(session_id, db),
        )
        applied_effects = application["applied_effects"]
        cls._apply_temp_hp_from_granted_effects(db, state, applied_effects)
        applied_declarative_effects_by_target = cls._build_applied_declarative_effects_by_target(
            applied_effects
        )
        summary_target = target_participant or attacker
        summary_text = (
            f"{spell_context['spell_name']} aplicou {len(applied_effects)} efeito(s)."
            if applied_effects
            else f"{spell_context['spell_name']} nao aplicou efeitos."
        )
        return cls._base_spell_result(
            spell_name=spell_context["spell_name"],
            spell_context=spell_context,
            target_display_name=summary_target.get("display_name") or "Target",
            target_kind=summary_target.get("kind") or "player",
            action_kind=spell_context.get("spell_mode") or "utility",
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_context['spell_name']} em "
                f"{summary_target.get('display_name') or 'Target'}."
                f"{cls._format_applied_declarative_effects_for_log(applied_declarative_effects_by_target)}"
            ),
            extra={
                "__declarative_effect_group_id": application["effect_group_id"],
                "__applied_effect_count": len(applied_effects),
                "applied_declarative_effects_by_target": applied_declarative_effects_by_target,
                "concentration_group": application["effect_group_id"]
                if spell_context.get("concentration")
                else None,
            },
        )

    @classmethod
    def _resolve_check_advantage_mode_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        ability: AbilityName,
        target_participant_id: str | None = None,
        manual_mode: Literal["advantage", "normal", "disadvantage"] = "normal",
    ) -> str:
        state = cls.get_state(db, session_id)
        if state is None:
            logger.info("[_resolve_check_advantage_mode_for_actor] no combat state session_id=%s", session_id)
            return "normal"
        if state.phase == CombatPhase.ended:
            logger.info("[_resolve_check_advantage_mode_for_actor] combat ended session_id=%s", session_id)
            return "normal"
        participant = resolve_actor_participant(state, actor_ref_id)
        if not isinstance(participant, dict):
            logger.info("[_resolve_check_advantage_mode_for_actor] no participant session_id=%s actor_ref_id=%s", session_id, actor_ref_id)
            return "normal"
        if participant.get("kind") != actor_kind:
            logger.info(
                "[_resolve_check_advantage_mode_for_actor] kind mismatch session_id=%s actor_ref_id=%s expected=%s got=%s",
                session_id, actor_ref_id, actor_kind, participant.get("kind"),
            )
            return "normal"
        return resolve_check_advantage_mode(
            participant,
            ability,
            target_participant_id=target_participant_id,
            manual_mode=manual_mode,
        )

    @classmethod
    def _resolve_skill_check_advantage_mode_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        skill: SkillName,
        target_participant_id: str | None = None,
        manual_mode: Literal["advantage", "normal", "disadvantage"] = "normal",
    ) -> str:
        return cls._resolve_check_advantage_mode_for_actor(
            db,
            session_id,
            actor_kind=actor_kind,
            actor_ref_id=actor_ref_id,
            ability=SKILL_ABILITY_MAP[skill],
            target_participant_id=target_participant_id,
            manual_mode=manual_mode,
        )

    @classmethod
    def _explain_check_modifier_sources_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        ability: AbilityName,
        roll_type: Literal["ability", "skill"] = "ability",
        skill: SkillName | None = None,
        target_participant_id: str | None = None,
    ) -> list[dict]:
        state = cls.get_state(db, session_id)
        if state is None:
            logger.info("[_explain_check_modifier_sources_for_actor] no combat state session_id=%s", session_id)
            return []
        if state.phase == CombatPhase.ended:
            logger.info("[_explain_check_modifier_sources_for_actor] combat ended session_id=%s", session_id)
            return []
        participant = resolve_actor_participant(state, actor_ref_id)
        if not isinstance(participant, dict):
            logger.info("[_explain_check_modifier_sources_for_actor] no participant session_id=%s actor_ref_id=%s", session_id, actor_ref_id)
            return []
        if participant.get("kind") != actor_kind:
            logger.info(
                "[_explain_check_modifier_sources_for_actor] kind mismatch session_id=%s actor_ref_id=%s expected=%s got=%s",
                session_id, actor_ref_id, actor_kind, participant.get("kind"),
            )
            return []
        return explain_check_modifier_sources(
            participant,
            ability=ability,
            roll_type=roll_type,
            skill=skill,
            target_participant_id=target_participant_id,
        )

    @classmethod
    def _resolve_save_advantage_mode_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        ability: AbilityName,
        manual_mode: Literal["advantage", "normal", "disadvantage"] = "normal",
    ) -> str:
        state = cls.get_state(db, session_id)
        if state is None:
            logger.info("[_resolve_save_advantage_mode_for_actor] no combat state session_id=%s", session_id)
            return "normal"
        if state.phase == CombatPhase.ended:
            logger.info("[_resolve_save_advantage_mode_for_actor] combat ended session_id=%s", session_id)
            return "normal"
        participant = resolve_actor_participant(state, actor_ref_id)
        if not isinstance(participant, dict):
            logger.info("[_resolve_save_advantage_mode_for_actor] no participant session_id=%s actor_ref_id=%s", session_id, actor_ref_id)
            return "normal"
        if participant.get("kind") != actor_kind:
            logger.info(
                "[_resolve_save_advantage_mode_for_actor] kind mismatch session_id=%s actor_ref_id=%s expected=%s got=%s",
                session_id, actor_ref_id, actor_kind, participant.get("kind"),
            )
            return "normal"
        ctx = modify_saving_throw(
            participant,
            ability,
            manual_mode=manual_mode,
            source_kind="unknown_legacy",
        )
        return ctx.result

    @classmethod
    def _explain_save_modifier_sources_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        ability: AbilityName,
    ) -> list[dict]:
        state = cls.get_state(db, session_id)
        if state is None:
            logger.info("[_explain_save_modifier_sources_for_actor] no combat state session_id=%s", session_id)
            return []
        if state.phase == CombatPhase.ended:
            logger.info("[_explain_save_modifier_sources_for_actor] combat ended session_id=%s", session_id)
            return []
        participant = resolve_actor_participant(state, actor_ref_id)
        if not isinstance(participant, dict):
            logger.info("[_explain_save_modifier_sources_for_actor] no participant session_id=%s actor_ref_id=%s", session_id, actor_ref_id)
            return []
        if participant.get("kind") != actor_kind:
            logger.info(
                "[_explain_save_modifier_sources_for_actor] kind mismatch session_id=%s actor_ref_id=%s expected=%s got=%s",
                session_id, actor_ref_id, actor_kind, participant.get("kind"),
            )
            return []
        ctx = modify_saving_throw(
            participant,
            ability,
            manual_mode="normal",
            source_kind="unknown_legacy",
        )
        return [*ctx.advantage_source_details, *ctx.disadvantage_source_details]
