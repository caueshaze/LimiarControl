from __future__ import annotations

from enum import Enum
import logging
import random
from math import floor
import unicodedata
from uuid import uuid4

logger = logging.getLogger(__name__)

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.combat import CombatPhase, CombatState
from app.schemas.roll import RollActorStats
from app.services.session_state_finalize import calculate_player_armor_class_from_state

from .exceptions import CombatServiceError, _parse_dice
from .condition_effects import is_action_blocked, is_movement_blocked


class CombatCoreMixin:
    _PLAYER_SHIELD_BONUS = 2
    _SAVE_SUCCESS_OUTCOME_VALUES = {"none", "half_damage"}
    _COMBAT_SPELL_ACTION_COSTS = {"action", "bonus_action", "reaction"}

    @classmethod
    def _normalize_lookup(cls, value: object) -> str:
        if isinstance(value, Enum):
            value = value.value
        if not isinstance(value, str):
            return ""
        normalized = unicodedata.normalize("NFD", value.strip().lower())
        normalized = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
        normalized = normalized.replace("_", " ").replace("-", " ")
        return " ".join(normalized.split())

    @classmethod
    def _safe_optional_int(cls, value: object) -> int | None:
        return value if isinstance(value, int) else None

    @classmethod
    def _normalize_class_id(cls, value: object) -> str:
        return str(value or "").strip().lower()

    @classmethod
    def _get_player_class_feature_ids(cls, data: dict | None) -> set[str]:
        raw_features = (
            cls._as_dict(data).get("classFeatures") if isinstance(data, dict) else None
        )
        if not isinstance(raw_features, list):
            return set()
        return {
            str(feature.get("id"))
            for feature in raw_features
            if isinstance(feature, dict) and isinstance(feature.get("id"), str)
        }

    @classmethod
    def _get_player_fighting_style(cls, data: dict | None) -> str | None:
        payload = cls._as_dict(data)
        fighting_style = payload.get("fightingStyle")
        if isinstance(fighting_style, str) and fighting_style.strip():
            return fighting_style.strip().lower()

        class_id = cls._normalize_class_id(payload.get("class"))
        level = cls._safe_int(payload.get("level"), 1)
        if class_id == "guardian" and level >= 2:
            return "archery"
        return None

    @classmethod
    def _player_has_colossus_slayer(cls, data: dict | None) -> bool:
        payload = cls._as_dict(data)
        feature_ids = cls._get_player_class_feature_ids(payload)
        if "hunter_colossus_slayer" in feature_ids:
            return True
        class_id = cls._normalize_class_id(payload.get("class"))
        subclass = cls._normalize_class_id(payload.get("subclass"))
        level = cls._safe_int(payload.get("level"), 1)
        return class_id == "guardian" and subclass == "hunter" and level >= 3

    @classmethod
    def _resolve_save_damage_amount(
        cls,
        rolled_amount: int,
        *,
        is_saved: bool,
        save_success_outcome: object,
    ) -> int:
        total = max(0, rolled_amount)
        if not is_saved:
            return total
        if cls._normalize_save_success_outcome(save_success_outcome) == "half_damage":
            return floor(total / 2)
        return 0

    @classmethod
    def _get_player_ability_score(
        cls, data: dict, ability_name: str, default: int = 10
    ) -> int:
        abilities = cls._as_dict(data.get("abilities"))
        value = abilities.get(ability_name)
        return value if isinstance(value, int) else default

    @classmethod
    def calculate_player_armor_class_from_state(cls, data: dict | None) -> int:
        return calculate_player_armor_class_from_state(data)

    @classmethod
    def _build_roll_actor_stats_for_save(
        cls,
        db: Session,
        session_id: str,
        ref_id: str,
        kind: str,
        display_name: str,
    ) -> RollActorStats:
        if kind == "player":
            target_model, _, _, _, prof_bonus, _ = cls._get_stats(
                db, ref_id, kind, session_id
            )
            data = cls._as_dict(target_model.state_json)
            abilities = {
                ability_name: cls._safe_int(value, 10)
                for ability_name, value in cls._as_dict(data.get("abilities")).items()
                if ability_name in cls._ENTITY_ABILITY_ALIASES
            }
            saving_throw_proficiencies = cls._as_dict(
                data.get("savingThrowProficiencies")
            )
            saving_throws: dict[str, int] = {}
            for ability_name in cls._ENTITY_ABILITY_ALIASES:
                if saving_throw_proficiencies.get(ability_name) is True:
                    saving_throws[ability_name] = (
                        cls._ability_modifier(
                            cls._safe_int(abilities.get(ability_name), 10)
                        )
                        + prof_bonus
                    )
            return RollActorStats(
                display_name=display_name,
                abilities=abilities,
                saving_throws=saving_throws or None,
                proficiency_bonus=prof_bonus,
                actor_kind="player",
                actor_ref_id=ref_id,
            )

        session_entity, npc = cls._get_session_entity_and_campaign_entity(db, ref_id)
        overrides = cls._as_dict(session_entity.overrides)
        abilities = {
            ability_name: cls._get_entity_ability_score(
                cls._as_dict(npc.abilities), overrides, ability_name
            )
            for ability_name in cls._ENTITY_ABILITY_ALIASES
        }
        saving_throws = cls._get_entity_saving_throw_overrides(npc, overrides) or None
        _, _, _, _, prof_bonus, _ = cls._get_stats(db, ref_id, kind, session_id)
        return RollActorStats(
            display_name=display_name,
            abilities=abilities,
            saving_throws=saving_throws,
            proficiency_bonus=prof_bonus,
            actor_kind="session_entity",
            actor_ref_id=ref_id,
        )

    @classmethod
    def _clear_participant_pending_attack(cls, participant: dict | None) -> None:
        if not participant or not isinstance(participant, dict):
            return
        participant.pop("pending_attack", None)

    @classmethod
    def _create_pending_attack(
        cls,
        state: CombatState,
        participant: dict,
        payload: dict,
    ) -> str:
        pending_attack_id = str(uuid4())
        participant["pending_attack"] = {
            **payload,
            "id": pending_attack_id,
        }
        flag_modified(state, "participants")
        return pending_attack_id

    @classmethod
    def _create_pending_spell_effect(
        cls,
        state: CombatState,
        participant: dict,
        payload: dict,
    ) -> str:
        return cls._create_pending_attack(
            state,
            participant,
            {
                **payload,
                "type": "player_spell_effect",
            },
        )

    @classmethod
    def _require_pending_attack(
        cls,
        participant: dict,
        pending_attack_id: str,
        *,
        expected_type: str,
    ) -> dict:
        pending_attack = (
            participant.get("pending_attack") if isinstance(participant, dict) else None
        )
        if not isinstance(pending_attack, dict):
            raise CombatServiceError("No pending damage roll for this actor.", 404)
        if pending_attack.get("id") != pending_attack_id:
            raise CombatServiceError("Pending damage roll not found.", 404)
        if pending_attack.get("type") != expected_type:
            raise CombatServiceError("Pending damage roll type mismatch.", 400)
        return pending_attack

    @classmethod
    def _require_pending_spell_effect(
        cls,
        participant: dict,
        pending_spell_id: str,
    ) -> dict:
        return cls._require_pending_attack(
            participant,
            pending_spell_id,
            expected_type="player_spell_effect",
        )

    @classmethod
    def _resolve_damage_roll(
        cls,
        damage_dice: str,
        *,
        critical: bool = False,
        roll_source: str = "system",
        manual_rolls: list[int] | None = None,
    ) -> tuple[list[int], int]:
        if damage_dice == "unarmed":
            return [], 2 if critical else 1

        count, sides, expression_modifier = _parse_dice(damage_dice)
        if count <= 0 or sides <= 0:
            return [], max(0, expression_modifier)

        effective_count = count * (2 if critical else 1)
        if roll_source == "manual":
            manual_values = manual_rolls or []
            if len(manual_values) != effective_count:
                raise CombatServiceError(
                    f"Manual damage roll requires exactly {effective_count} result(s)."
                )
            for value in manual_values:
                if not isinstance(value, int) or value < 1 or value > sides:
                    raise CombatServiceError(
                        f"Manual damage roll values must be between 1 and {sides}."
                    )
            rolls = manual_values
        else:
            rolls = [random.randint(1, sides) for _ in range(effective_count)]

        return rolls, sum(rolls) + expression_modifier

    @classmethod
    def get_state(cls, db: Session, session_id: str) -> CombatState | None:
        return db.exec(
            select(CombatState).where(CombatState.session_id == session_id)
        ).first()

    @classmethod
    def _require_active(cls, state: CombatState | None):
        if not state:
            raise CombatServiceError("No combat active for this session", 404)
        if state.phase != CombatPhase.active:
            raise CombatServiceError("Combat is not in active phase")

    @classmethod
    def _resolve_actor_participant(
        cls,
        state: CombatState,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
    ) -> dict:
        current_p = cls._get_current_participant(state)

        if actor_participant_id and current_p.get("id") != actor_participant_id:
            raise CombatServiceError(
                "Selected actor is not the active participant", 403
            )

        if is_gm:
            return current_p

        if current_p.get("kind") != "player":
            raise CombatServiceError("It's not a player's turn")

        if current_p.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("Not your turn", 403)

        return current_p

    @classmethod
    def _require_actor_status(
        cls, attacker: dict, allowed_statuses: tuple[str, ...], message: str
    ):
        if attacker.get("status") not in allowed_statuses:
            raise CombatServiceError(message, 403)

    @classmethod
    def _require_action_capable(cls, actor: dict) -> None:
        if is_action_blocked(actor):
            raise CombatServiceError(
                "This participant is incapacitated and cannot take actions.", 403
            )

    @classmethod
    def _require_movement_capable(cls, actor: dict) -> None:
        if is_movement_blocked(actor):
            raise CombatServiceError(
                "This participant's movement is blocked by a condition.", 403
            )
