from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.spell_effect_factories import build_barkskin_effect, build_blur_effect
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _BuffsDefenseBase = CombatServiceHostProtocol
else:
    _BuffsDefenseBase = object


class BuffsDefenseAutomationMixin(_BuffsDefenseBase):
    @classmethod
    async def _cast_barkskin_automation(
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
            raise CombatServiceError("Pele de Árvore exige um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Pele de Árvore não possui variantes.", 400)

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

        effect = build_barkskin_effect(
            cls._build_combat_spell_effect_context(
                spell_key="barkskin",
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
            source_spell_key="barkskin",
        )

        summary_text = (
            f"{spell_name}: a CA de {target_participant['display_name']} não pode ser menor que 16 por até 1 hora."
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
                "utility": "barkskin",
                "concentration_group": concentration_group,
                "armor_class_floor": 16,
                "sets_minimum_ac": True,
                "is_flat_bonus": False,
                "duration_seconds": 3600,
            },
        )

    @classmethod
    async def _cast_blur_automation(
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
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Reflexos não possui variantes.", 400)
        if target_participant is not None and target_participant.get("id") != attacker.get("id"):
            raise CombatServiceError("Reflexos só pode afetar o próprio conjurador.", 400)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(session_id, state, result["removed_area_effects"])

        spell_name = spell_context["spell_name"]
        concentration_group = str(uuid4())
        game_time = get_game_time_seconds(session_id, db)

        effect = build_blur_effect(
            cls._build_combat_spell_effect_context(
                spell_key="blur",
                spell_name=spell_name,
                caster_participant_id=attacker["id"],
                target_participant_id=attacker["id"],
                game_time_seconds=game_time,
                duration_seconds=60,
                concentration=True,
                concentration_group=concentration_group,
            )
        )
        cls._apply_factory_spell_effect_to_target(
            state=state,
            target_participant=attacker,
            effect=effect,
            source_spell_key="blur",
        )

        summary_text = (
            f"{spell_name}: ataques contra {attacker['display_name']} têm desvantagem "
            "enquanto a concentração for mantida."
        )
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            action_kind="utility",
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name}. "
                "Ataques contra ele têm desvantagem enquanto a concentração for mantida."
            ),
            extra={
                "utility": "blur",
                "concentration_group": concentration_group,
                "attack_disadvantage_against_target": True,
                "duration_seconds": 60,
            },
        )

    @classmethod
    async def _cast_feather_fall_automation(
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
            raise CombatServiceError("Queda Suave exige ao menos um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Queda Suave não possui variantes.", 400)

        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)
        active_effects = target_participant.get("active_effects")
        if not isinstance(active_effects, list):
            active_effects = []
            target_participant["active_effects"] = active_effects
        target_participant["active_effects"] = [
            effect
            for effect in active_effects
            if cls._normalize_lookup(
                (cls._get_effect_metadata(effect) or {}).get("source_spell_key")
            )
            != "feather_fall"
        ]
        effect = cls._build_active_effect(
            kind="spell_effect",
            source_participant_id=attacker["id"],
            duration_type="timed",
            created_at_game_time_seconds=game_time,
            expires_at_game_time_seconds=game_time + 60,
            metadata={
                "source_spell_key": "feather_fall",
                "source_spell_name": spell_name,
                "mechanical": True,
                "utility": "feather_fall",
                "movement_modifier": True,
                "fall_protection": True,
                "fall_speed_meters_per_round": 18,
                "prevents_fall_damage": True,
                "prevents_prone_from_fall": True,
                "lands_on_feet": True,
                "ends_on_landing": True,
                "grants_flight": False,
                "grants_extra_movement": False,
                "duration_seconds": 60,
                "source_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
            },
            display_label=spell_name,
        )
        cls._append_effect_to_participant(target_participant, effect)

        flag_modified(state, "participants")

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_participant["display_name"],
            target_kind=target_participant["kind"],
            action_kind="utility",
            summary_text=(
                f"{spell_name}: {target_participant['display_name']} foi protegido(a) contra dano de queda por 1 minuto."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em {target_participant['display_name']}."
            ),
            extra={
                "utility": "feather_fall",
                "targets_count": 1,
                "fall_speed_meters_per_round": 18,
                "prevents_fall_damage": True,
                "prevents_prone_from_fall": True,
                "ends_on_landing": True,
            },
        )
