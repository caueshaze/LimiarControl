from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.spell_effect_factories import build_jump_effect, build_spider_climb_effect
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _BuffsPhysicalBase = CombatServiceHostProtocol
else:
    _BuffsPhysicalBase = object


class BuffsPhysicalAutomationMixin(_BuffsPhysicalBase):
    @classmethod
    async def _cast_jump_automation(
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
            raise CombatServiceError("Salto exige um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Salto não possui variantes.", 400)

        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        effect = build_jump_effect(
            cls._build_combat_spell_effect_context(
                spell_key="jump",
                spell_name=spell_name,
                caster_participant_id=attacker["id"],
                target_participant_id=target_participant["id"],
                game_time_seconds=game_time,
                duration_seconds=60,
                concentration=False,
                concentration_group=None,
            )
        )
        cls._apply_factory_spell_effect_to_target(
            state=state,
            target_participant=target_participant,
            effect=effect,
            source_spell_key="jump",
        )

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_participant["display_name"],
            target_kind=target_participant["kind"],
            action_kind="utility",
            summary_text=(
                f"{spell_name}: a distância de salto de {target_participant['display_name']} foi triplicada por 1 minuto."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em {target_participant['display_name']}."
            ),
            extra={
                "utility": "jump",
                "jump_distance_multiplier": 3,
                "duration_seconds": 60,
                "grants_extra_movement": False,
                "grants_flight": False,
                "prevents_fall_damage": False,
            },
        )

    @classmethod
    async def _cast_spider_climb_automation(
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
            raise CombatServiceError("Escalada de Aranha exige um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Escalada de Aranha não possui variantes.", 400)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(
            session_id, state, result["removed_area_effects"],
        )

        spell_name = spell_context["spell_name"]
        concentration_group = str(uuid4())
        game_time = get_game_time_seconds(session_id, db)

        effect = build_spider_climb_effect(
            cls._build_combat_spell_effect_context(
                spell_key="spider_climb",
                spell_name=spell_name,
                caster_participant_id=attacker["id"],
                target_participant_id=target_participant["id"],
                game_time_seconds=game_time,
                duration_seconds=3600,
                concentration=True,
                concentration_group=concentration_group,
            )
        )
        cls._apply_factory_spell_effect_to_target(
            state=state,
            target_participant=target_participant,
            effect=effect,
            source_spell_key="spider_climb",
        )

        summary_text = (
            f"{spell_name}: {target_participant['display_name']} pode escalar superfícies e tetos por até 1 hora."
        )
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_participant["display_name"],
            target_kind=target_participant["kind"],
            action_kind="utility",
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em {target_participant['display_name']}."
            ),
            extra={
                "utility": "spider_climb",
                "concentration_group": concentration_group,
                "movement_mode": "spider_climb",
                "duration_seconds": 3600,
                "grants_climb_speed": True,
                "can_move_on_vertical_surfaces": True,
                "can_move_on_ceilings": True,
                "grants_flight": False,
                "prevents_fall_damage": False,
            },
        )
