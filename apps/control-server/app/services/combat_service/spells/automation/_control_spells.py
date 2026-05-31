from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.roll_resolution import resolve_saving_throw
from app.services.spell_effect_factories import build_compelled_duel_effect
from app.services.compelled_duel import find_compelled_duel_effect_on_target
from ...condition_effects_saves import modify_saving_throw
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _ControlSpellsBase = CombatServiceHostProtocol
else:
    _ControlSpellsBase = object


class ControlSpellsAutomationMixin(_ControlSpellsBase):
    @classmethod
    async def _cast_entangle_automation(
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
        target_participant: dict | None,
    ) -> dict:
        raise CombatServiceError(
            "Entangle is resolved via the area-cast pipeline.",
            400,
        )

    @classmethod
    async def _cast_compelled_duel_automation(
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
        target_participant: dict | None,
    ) -> dict:
        if target_participant is None:
            raise CombatServiceError("Duelo Compelido requer um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Duelo Compelido não possui variantes.", 400)
        if target_participant["ref_id"] == attacker["ref_id"]:
            raise CombatServiceError(
                "Duelo Compelido deve ser conjurado em outra criatura.", 400
            )

        spell_name = spell_context["spell_name"]
        target_name = target_participant["display_name"]
        save_ability = spell_context.get("save_ability") or "wisdom"
        save_dc = cls._safe_int(spell_context.get("save_dc"), 0)

        save_mod = modify_saving_throw(
            target_participant,
            save_ability,
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
            ability=save_ability,
            advantage_mode=save_mod.result,
            dc=save_dc,
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        roll_result.is_gm_roll = is_gm
        is_saved = bool(roll_result.success)

        concentration_group = None
        if not is_saved:
            # New concentration spell: end the caster's prior concentration first.
            result = cls._clear_concentration_for_source(
                state,
                source_participant_id=attacker["id"],
                db=db,
            )
            cls._sync_area_effects_if_changed(
                session_id, state, result["removed_area_effects"],
            )

            concentration_group = str(uuid4())
            game_time = get_game_time_seconds(session_id, db)
            effect = build_compelled_duel_effect(
                cls._build_combat_spell_effect_context(
                    spell_key="compelled_duel",
                    spell_name=spell_name,
                    caster_participant_id=attacker["id"],
                    target_participant_id=target_participant["id"],
                    game_time_seconds=game_time,
                    duration_seconds=60,
                    concentration=True,
                    concentration_group=concentration_group,
                    spell_save_dc=save_dc,
                    extra_metadata={
                        "duel_caster_ref_id": attacker["ref_id"],
                        "duel_target_ref_id": target_participant["ref_id"],
                    },
                )
            )
            cls._apply_factory_spell_effect_to_target(
                state=state,
                target_participant=target_participant,
                effect=effect,
                source_spell_key="compelled_duel",
            )
            flag_modified(state, "participants")

        if is_saved:
            summary_text = f"{target_name} resistiu ao {spell_name}."
            log_msg = (
                f"{attacker['display_name']} conjurou {spell_name} em {target_name}: "
                f"salvaguarda de Sabedoria bem-sucedida."
            )
        else:
            summary_text = (
                f"{target_name} falhou na salvaguarda e está compelido a duelar com "
                f"{attacker['display_name']}: desvantagem em ataques contra outras criaturas."
            )
            log_msg = (
                f"{attacker['display_name']} conjurou {spell_name} em {target_name}: "
                f"falhou na salvaguarda de Sabedoria."
            )

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="saving_throw",
            summary_text=summary_text,
            log_message=log_msg,
            extra={
                "is_saved": is_saved,
                "effect_applied": not is_saved,
                "roll": roll_result.total,
                "roll_result": roll_result,
                "save_ability": save_ability,
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": "none",
                "concentration": not is_saved,
                "concentration_group": concentration_group,
                "duration_seconds": 60,
            },
        )

    @classmethod
    async def resolve_compelled_duel_movement_save(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_participant_id: str | None,
        actor_user_id: str,
        is_gm: bool,
        manual_roll: int | None = None,
    ) -> dict:
        """GM-adjudicated Wisdom save when a compelled target tries to move >9m
        from the caster. On success, movement is unrestricted for the rest of the
        actor's turn (a per-turn flag, reset at turn start)."""
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)

        actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)
        effect = find_compelled_duel_effect_on_target(actor)
        if effect is None:
            raise CombatServiceError("Esta criatura não está sob Duelo Compelido.", 400)

        metadata = effect.get("metadata") or {}
        save_dc = cls._safe_int(metadata.get("movement_restriction_save_dc"), 0)
        actor_name = actor.get("display_name") or "Alvo"

        resources = cls._get_turn_resources(actor)
        if resources.get("compelled_duel_movement_free"):
            return {
                "allowed": True,
                "rolled": False,
                "already_free_this_turn": True,
                "save_dc": save_dc,
            }

        save_mod = modify_saving_throw(
            actor,
            "wisdom",
            source_kind="passive_condition",
        )
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                actor["ref_id"],
                actor["kind"],
                actor_name,
            ),
            ability="wisdom",
            advantage_mode=save_mod.result,
            dc=save_dc,
            manual_roll=manual_roll,
        )
        cls._apply_flat_save_effect_bonus_to_roll_result(participant=actor, roll_result=roll_result)
        roll_result.is_gm_roll = is_gm
        succeeded = bool(roll_result.success)

        if succeeded:
            resources["compelled_duel_movement_free"] = True
            actor["turn_resources"] = resources
            flag_modified(state, "participants")
            db.add(state)
            db.commit()
            db.refresh(state)
            await cls._emit_state(session_id, state)
            await cls._emit_log(
                session_id,
                {
                    "message": (
                        f"{actor_name} passou na salvaguarda de Sabedoria (CD {save_dc}) do "
                        f"Duelo Compelido e pode se mover livremente neste turno."
                    ),
                    "source": "compelled_duel",
                },
            )
        else:
            await cls._emit_log(
                session_id,
                {
                    "message": (
                        f"{actor_name} falhou na salvaguarda de Sabedoria (CD {save_dc}) do "
                        f"Duelo Compelido e não pode se mover a mais de 9m do conjurador."
                    ),
                    "source": "compelled_duel",
                },
            )

        return {
            "allowed": succeeded,
            "rolled": True,
            "save_ability": "wisdom",
            "save_dc": save_dc,
            "roll": roll_result.total,
            "roll_result": roll_result,
        }
