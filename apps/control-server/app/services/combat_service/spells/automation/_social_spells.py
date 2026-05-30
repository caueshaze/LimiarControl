from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.roll_resolution import resolve_saving_throw
from ...condition_effects_saves import modify_saving_throw
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _SocialSpellsBase = CombatServiceHostProtocol
else:
    _SocialSpellsBase = object


class SocialSpellsAutomationMixin(_SocialSpellsBase):
    @classmethod
    async def _cast_animal_friendship_automation(
        cls, db: Session, session_id: str, *, attacker: dict, attacker_model,
        actor_user_id: str, is_gm: bool, req, state: CombatState,
        spell_context: dict, target_participant: dict,
    ) -> dict:
        from ...condition_effects_predicates import has_condition_immunity_from_source

        spell_name = spell_context["spell_name"]
        target_name = target_participant["display_name"]

        if has_condition_immunity_from_source(target_participant, "charmed", source_participant=attacker):
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=target_name,
                target_kind=target_participant["kind"],
                action_kind="saving_throw",
                summary_text=f"{spell_name} não teve efeito em {target_name} (alvo protegido).",
                log_message=(
                    f"{attacker['display_name']} lançou {spell_name} em {target_name}; "
                    f"o alvo está protegido contra encantamentos dessa criatura."
                ),
                extra={"immune": True, "immune_reason": "protection_from_evil_and_good"},
            )

        save_mod = modify_saving_throw(
            target_participant,
            spell_context["save_ability"],
            source_participant=attacker,
            source_kind="participant",
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_participant["ref_id"],
                target_participant["kind"],
                target_participant["display_name"],
            ),
            ability=spell_context["save_ability"],
            advantage_mode=save_mod.result,
            dc=cls._safe_int(spell_context.get("save_dc"), 0),
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        roll_result.is_gm_roll = is_gm
        roll_total = roll_result.total
        is_saved = bool(roll_result.success)

        game_time = get_game_time_seconds(session_id, db)
        if not is_saved:
            cls._append_effect_to_participant(
                target_participant,
                cls._build_active_effect(
                    kind="condition",
                    condition_type="charmed",
                    source_participant_id=attacker["id"],
                    duration_type="timed",
                    created_at_game_time_seconds=game_time,
                    expires_at_game_time_seconds=game_time + 86400,
                    metadata={
                        "source_spell_key": "animal_friendship",
                        "caster_participant_id": attacker["id"],
                        "charmer_participant_id": attacker["id"],
                        "termination_conditions": [
                            {"type": "target_takes_damage_from_caster_or_allies"},
                        ],
                    },
                ),
            )
            flag_modified(state, "participants")

        if is_saved:
            summary_text = f"{target_name} passou na salvaguarda contra {spell_name}."
        else:
            summary_text = f"{target_name} falhou na salvaguarda e ficou enfeitiçado."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="saving_throw",
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} lançou {spell_name} em {target_name}: "
                f"{'o alvo passou na salvaguarda' if is_saved else 'o alvo falhou e ficou enfeitiçado'}."
            ),
            extra={
                "is_saved": is_saved,
                "roll": roll_total,
                "roll_result": roll_result,
                "save_ability": spell_context.get("save_ability"),
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": spell_context.get("save_success_outcome"),
            },
        )

    @classmethod
    async def _cast_charm_person_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict,
    ) -> dict:
        from ...condition_effects_predicates import has_condition_immunity_from_source

        spell_name = spell_context["spell_name"]
        target_name = target_participant["display_name"]

        if has_condition_immunity_from_source(target_participant, "charmed", source_participant=attacker):
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=target_name,
                target_kind=target_participant["kind"],
                action_kind="saving_throw",
                summary_text=f"{spell_name} não teve efeito em {target_name} (alvo protegido).",
                log_message=(
                    f"{attacker['display_name']} lançou {spell_name} em {target_name}; "
                    f"o alvo está protegido contra encantamentos dessa criatura."
                ),
                extra={"immune": True, "immune_reason": "protection_from_evil_and_good"},
            )

        is_hostile = cls._is_hostile_team_context(attacker, target_participant)
        advantage_mode = "advantage" if is_hostile else "normal"
        save_mod = modify_saving_throw(
            target_participant,
            spell_context["save_ability"],
            manual_mode=advantage_mode,
            source_participant=attacker,
            source_kind="participant",
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_participant["ref_id"],
                target_participant["kind"],
                target_participant["display_name"],
            ),
            ability=spell_context["save_ability"],
            dc=cls._safe_int(spell_context.get("save_dc"), 0),
            advantage_mode=save_mod.result,
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        roll_result.is_gm_roll = is_gm
        roll_total = roll_result.total
        is_saved = bool(roll_result.success)

        game_time = get_game_time_seconds(session_id, db)
        if not is_saved:
            cls._append_effect_to_participant(
                target_participant,
                cls._build_active_effect(
                    kind="condition",
                    condition_type="charmed",
                    source_participant_id=attacker["id"],
                    duration_type="timed",
                    created_at_game_time_seconds=game_time,
                    expires_at_game_time_seconds=game_time + 3600,
                    metadata={
                        "source_spell_key": "charm_person",
                        "caster_participant_id": attacker["id"],
                        "charmer_participant_id": attacker["id"],
                        "target_knows_charmed_by_caster": True,
                        "termination_conditions": [
                            {"type": "target_takes_damage_from_caster_or_allies"},
                        ],
                    },
                ),
            )
            flag_modified(state, "participants")

        if is_saved:
            summary_text = f"{target_name} passou na salvaguarda contra {spell_name}."
        else:
            summary_text = f"{target_name} falhou na salvaguarda e ficou enfeitiçado."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="saving_throw",
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} lançou {spell_name} em {target_name}: "
                f"{'o alvo passou na salvaguarda' if is_saved else 'o alvo falhou e ficou enfeitiçado'}."
            ),
            extra={
                "is_saved": is_saved,
                "roll": roll_total,
                "roll_result": roll_result,
                "save_ability": spell_context.get("save_ability"),
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": spell_context.get("save_success_outcome"),
            },
        )
