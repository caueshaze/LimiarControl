from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.roll import RollSource

from .exceptions import CombatServiceError
from .host_protocol import CombatServiceHostProtocol

logger = logging.getLogger(__name__)


class CombatConcentrationMixin(CombatServiceHostProtocol):
    @classmethod
    def _get_effect_metadata(cls, effect: dict | None) -> dict:
        metadata = (
            cls._as_dict(effect).get("metadata") if isinstance(effect, dict) else None
        )
        return metadata if isinstance(metadata, dict) else {}

    @classmethod
    def _find_participant_by_id(
        cls, state: CombatState | None, participant_id: str | None
    ) -> dict | None:
        if state is None or not participant_id:
            return None
        return next(
            (
                participant
                for participant in state.participants
                if participant.get("id") == participant_id
            ),
            None,
        )

    @classmethod
    def _build_active_effect(
        cls,
        *,
        kind: str,
        source_participant_id: str | None,
        condition_type: str | None = None,
        numeric_value: int | None = None,
        duration_type: str = "manual",
        remaining_rounds: int | None = None,
        expires_at_participant_id: str | None = None,
        created_at_game_time_seconds: int | None = None,
        expires_at_game_time_seconds: int | None = None,
        metadata: dict | None = None,
        display_label: str | None = None,
    ) -> dict:
        expires_on = None
        if duration_type == "until_turn_start":
            expires_on = "turn_start"
        elif duration_type == "until_turn_end":
            expires_on = "turn_end"
        elif duration_type == "rounds":
            expires_on = "turn_start"

        return {
            "id": str(uuid4()),
            "source_participant_id": source_participant_id,
            "kind": kind,
            "condition_type": condition_type if kind == "condition" else None,
            "numeric_value": numeric_value,
            "duration_type": duration_type,
            "remaining_rounds": remaining_rounds,
            "expires_on": expires_on,
            "expires_at_participant_id": expires_at_participant_id,
            "created_at_game_time_seconds": created_at_game_time_seconds,
            "expires_at_game_time_seconds": expires_at_game_time_seconds,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or None,
            "display_label": display_label,
        }

    @classmethod
    def _append_effect_to_participant(cls, participant: dict, effect: dict) -> None:
        effects = cls._get_participant_effects(participant)
        effects.append(effect)
        cls._set_participant_effects(participant, effects)

    @classmethod
    def _remove_area_effects_for_concentration_group(
        cls,
        state: CombatState,
        *,
        concentration_group: str,
    ) -> list[dict]:
        removed: list[dict] = []
        remaining: list[dict] = []
        for effect in state.active_area_effects or []:
            if (
                isinstance(effect, dict)
                and effect.get("concentration_group") == concentration_group
            ):
                removed.append(effect)
            else:
                remaining.append(effect)
        if removed:
            state.active_area_effects = remaining
        return removed

    @classmethod
    def _sync_area_effects_if_changed(
        cls,
        session_id: str,
        state: CombatState,
        area_removed: list[dict],
    ) -> None:
        if not area_removed:
            return
        flag_modified(state, "active_area_effects")
        from .limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map

        maybe_sync_active_area_effects_to_limiar_map(session_id, state)

    @classmethod
    def _remove_effect_group(
        cls,
        state: CombatState,
        *,
        concentration_group: str,
    ) -> dict:
        removed: list[dict] = []
        for participant in state.participants:
            effects = cls._get_participant_effects(participant)
            if not effects:
                continue
            kept: list[dict] = []
            for effect in effects:
                metadata = cls._get_effect_metadata(effect)
                if metadata.get("concentration_group") == concentration_group:
                    removed.append(
                        {
                            **effect,
                            "target_participant_id": participant.get("id"),
                            "target_display_name": participant.get("display_name", ""),
                        }
                    )
                    continue
                kept.append(effect)
            cls._set_participant_effects(participant, kept)
        area_removed = cls._remove_area_effects_for_concentration_group(
            state, concentration_group=concentration_group
        )
        return {"removed_effects": removed, "removed_area_effects": area_removed}

    @classmethod
    def _clear_concentration_for_source(
        cls,
        state: CombatState,
        *,
        source_participant_id: str,
        db=None,
    ) -> dict:
        groups: set[str] = set()
        for participant in state.participants:
            for effect in cls._get_participant_effects(participant):
                metadata = cls._get_effect_metadata(effect)
                if (
                    effect.get("source_participant_id") == source_participant_id
                    and metadata.get("concentration") is True
                    and isinstance(metadata.get("concentration_group"), str)
                ):
                    groups.add(metadata["concentration_group"])

        all_removed: list[dict] = []
        all_area_removed: list[dict] = []
        for group_id in groups:
            result = cls._remove_effect_group(state, concentration_group=group_id)
            all_removed.extend(result["removed_effects"])
            all_area_removed.extend(result["removed_area_effects"])
        if all_removed:
            cls._execute_on_end_effects_for_removed(
                state=state,
                removed_effects=all_removed,
            )
        if db is not None and all_removed:
            cls._cleanup_recurring_temp_hp_effects(db, state, all_removed)
        return {
            "removed_effects": all_removed,
            "removed_area_effects": all_area_removed,
        }

    @classmethod
    def _clear_concentration_for_participant_status(
        cls,
        state: CombatState | None,
        *,
        source_participant_id: str | None,
        db=None,
    ) -> dict:
        empty = {"removed_effects": [], "removed_area_effects": []}
        if not state or not source_participant_id:
            return empty
        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=source_participant_id,
            db=db,
        )
        if result["removed_effects"]:
            flag_modified(state, "participants")
        if result["removed_area_effects"]:
            flag_modified(state, "active_area_effects")
            from .limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map

            maybe_sync_active_area_effects_to_limiar_map(state.session_id, state)
        return result

    @classmethod
    def _get_hunters_mark_effect_for_target(
        cls,
        participant: dict,
        *,
        target_participant_id: str,
    ) -> dict | None:
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if (
                effect.get("kind") == "spell_effect"
                and metadata.get("source_spell_key") == "hunters_mark"
                and metadata.get("marked_target_participant_id")
                == target_participant_id
            ):
                return effect
        return None

    @classmethod
    def _get_charmed_effect_against_target(
        cls,
        participant: dict,
        *,
        target_participant_id: str,
    ) -> dict | None:
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if (
                effect.get("kind") == "condition"
                and effect.get("condition_type") == "charmed"
                and metadata.get("charmer_participant_id") == target_participant_id
            ):
                return effect
        return None

    @classmethod
    def _assert_hostile_action_allowed(
        cls,
        actor: dict,
        target: dict | None,
        *,
        action_label: str,
    ) -> None:
        if not target or not isinstance(target.get("id"), str):
            return
        blocked_effect = cls._get_charmed_effect_against_target(
            actor,
            target_participant_id=target["id"],
        )
        if blocked_effect is None:
            return
        raise CombatServiceError(
            f"You cannot use {action_label} against {target['display_name']} while charmed.",
            400,
        )

    @classmethod
    def _get_concentration_group_ids(cls, participant: dict | None) -> list[str]:
        if not isinstance(participant, dict):
            return []

        groups: list[str] = []
        seen: set[str] = set()
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if metadata.get("concentration") is not True:
                continue
            group_id = metadata.get("concentration_group")
            if not isinstance(group_id, str) or not group_id or group_id in seen:
                continue
            seen.add(group_id)
            groups.append(group_id)
        return groups

    @classmethod
    def _resolve_concentration_check_after_damage(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState | None,
        target_participant: dict | None,
        target_ref_id: str,
        target_kind: str,
        damage_taken: int,
        roll_source: str = "system",
        manual_roll: int | None = None,
    ) -> dict | None:
        if (
            state is None
            or not isinstance(target_participant, dict)
            or damage_taken <= 0
        ):
            return None

        concentration_groups = cls._get_concentration_group_ids(target_participant)
        if not concentration_groups:
            return None

        from . import spell_automation as spell_automation_module

        dc = max(10, damage_taken // 2)
        if roll_source == "manual":
            validated_roll_source: RollSource = "manual"
        else:
            validated_roll_source = "system"
        roll_result = spell_automation_module.resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_ref_id,
                target_kind,
                target_participant.get("display_name") or "Target",
            ),
            ability="constitution",
            dc=dc,
            roll_source=validated_roll_source,
            manual_roll=manual_roll,
        )
        roll_result.roll_source = validated_roll_source
        succeeded = bool(roll_result.success)

        broken_effect_labels: list[str] = []
        source_spell_keys: set[str] = set()
        if not succeeded:
            result = cls._clear_concentration_for_source(
                state,
                source_participant_id=target_participant.get("id", ""),
                db=db,
            )
            removed = result["removed_effects"]
            area_removed = result["removed_area_effects"]
            if removed:
                flag_modified(state, "participants")
            if area_removed:
                flag_modified(state, "active_area_effects")
                from .limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map

                maybe_sync_active_area_effects_to_limiar_map(session_id, state)
            for effect in removed:
                label = effect.get("display_label")
                if not isinstance(label, str) or not label.strip():
                    label = cls._effect_label(effect)
                if label and label not in broken_effect_labels:
                    broken_effect_labels.append(label)
                metadata = cls._get_effect_metadata(effect)
                spell_key = metadata.get("source_spell_key")
                if isinstance(spell_key, str) and spell_key.strip():
                    source_spell_keys.add(spell_key)
            for area_effect in area_removed:
                label = area_effect.get("source_spell_name")
                if isinstance(label, str) and label.strip() and label not in broken_effect_labels:
                    broken_effect_labels.append(label)
                spell_key = area_effect.get("source_spell_canonical_key")
                if isinstance(spell_key, str) and spell_key.strip():
                    source_spell_keys.add(spell_key)

        if succeeded:
            summary_text = (
                f"{target_participant['display_name']} manteve a concentração "
                f"({roll_result.total} no save de CON contra CD {dc})."
            )
        else:
            broken_text = (
                f" Efeitos encerrados: {', '.join(broken_effect_labels)}."
                if broken_effect_labels
                else ""
            )
            summary_text = (
                f"{target_participant['display_name']} perdeu a concentração "
                f"({roll_result.total} no save de CON contra CD {dc}).{broken_text}"
            )

        return {
            "actor_participant_id": target_participant.get("id"),
            "actor_display_name": target_participant.get("display_name") or "Target",
            "damage_taken": damage_taken,
            "dc": dc,
            "success": succeeded,
            "roll_result": roll_result,
            "broken_effect_labels": broken_effect_labels,
            "source_spell_keys": sorted(source_spell_keys),
            "summary_text": summary_text,
        }
