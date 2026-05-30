from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.session_state_finalize import finalize_session_state_data
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _NatureCantripsBase = CombatServiceHostProtocol
else:
    _NatureCantripsBase = object


class NatureCantripsAutomationMixin(_NatureCantripsBase):
    @classmethod
    async def _cast_druidcraft_automation(
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
        raw_description = getattr(req, "description", None)
        if not isinstance(raw_description, str):
            raise CombatServiceError("Druidismo exige descrição textual.", 400)
        description = raw_description.strip()
        if not description:
            raise CombatServiceError("Druidismo exige descrição textual não vazia.", 400)
        if len(description) > 300:
            raise CombatServiceError("Descrição de Druidismo deve ter no máximo 300 caracteres.", 400)

        _ALLOWED_EFFECTS = frozenset({
            "weather_prediction",
            "minor_natural_sensory_effect",
            "plant_bloom",
            "harmless_natural_effect",
            "ignite_or_extinguish_small_flame",
        })
        raw_variant = getattr(req, "variant_key", None)
        if raw_variant is not None:
            if not isinstance(raw_variant, str) or raw_variant.strip().lower() not in _ALLOWED_EFFECTS:
                raise CombatServiceError(
                    f"Druidismo aceita apenas variantes: {', '.join(sorted(_ALLOWED_EFFECTS))}.",
                    400,
                )
            variant_key = raw_variant.strip().lower()
        else:
            variant_key = "minor_natural_sensory_effect"

        game_time = get_game_time_seconds(session_id, db)
        effect_id = f"narrative_effect:{uuid4()}"
        effect = {
            "id": effect_id,
            "kind": "spell_effect",
            "duration_type": "timed",
            "expires_at_participant_id": None,
            "expires_at_game_time_seconds": game_time + 3600,
            "metadata": {
                "source_spell_key": "druidcraft",
                "source_spell_name": spell_context["spell_name"],
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "description": description,
                "mechanical": False,
                "narrative": True,
                "visible_to_all": True,
                "freeform": True,
                "spell_level": 0,
                "selected_variant_key": variant_key,
                "allowed_effects": sorted(_ALLOWED_EFFECTS),
            },
            "display_label": spell_context["spell_name"],
        }

        attacker_data = cls._as_dict(attacker_model.state_json)
        effects = attacker_data.get("active_spell_effects")
        if not isinstance(effects, list):
            effects = []
        effects.append(effect)
        attacker_data["active_spell_effects"] = effects
        attacker_model.state_json = finalize_session_state_data(
            attacker_data,
            game_time_seconds=game_time,
        )
        flag_modified(attacker_model, "state_json")
        db.add(attacker_model)

        short = description if len(description) <= 120 else f"{description[:117]}..."
        spell_name = spell_context["spell_name"]
        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=f"{spell_name}: \"{short}\"",
            log_message=f"{attacker['display_name']} conjurou {spell_name}: \"{short}\".",
            extra={
                "created_effect_id": effect_id,
                "selected_variant_key": variant_key,
                "__player_state_ids_to_emit": {attacker["ref_id"]},
            },
        )

    _THAUMATURGY_ALLOWED_EFFECTS: frozenset[str] = frozenset({
        "booming_voice",
        "flame_omen",
        "harmless_tremor",
        "instantaneous_sound",
        "open_or_close_unlocked_door",
        "alter_eyes",
    })
    _THAUMATURGY_DEFAULT_EFFECT: str = "booming_voice"

    @classmethod
    async def _cast_thaumaturgy_automation(
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
        raw_description = getattr(req, "description", None)
        if not isinstance(raw_description, str):
            raise CombatServiceError("Taumaturgia exige descrição textual.", 400)
        description = raw_description.strip()
        if not description:
            raise CombatServiceError("Taumaturgia exige descrição textual não vazia.", 400)
        if len(description) > 300:
            raise CombatServiceError("Descrição de Taumaturgia deve ter no máximo 300 caracteres.", 400)

        raw_variant = getattr(req, "variant_key", None)
        if raw_variant is not None:
            if not isinstance(raw_variant, str) or raw_variant.strip().lower() not in cls._THAUMATURGY_ALLOWED_EFFECTS:
                raise CombatServiceError(
                    f"Taumaturgia aceita apenas variantes: {', '.join(sorted(cls._THAUMATURGY_ALLOWED_EFFECTS))}.",
                    400,
                )
            variant_key = raw_variant.strip().lower()
        else:
            variant_key = cls._THAUMATURGY_DEFAULT_EFFECT

        game_time = get_game_time_seconds(session_id, db)
        effect_id = f"narrative_effect:{uuid4()}"
        effect = {
            "id": effect_id,
            "kind": "spell_effect",
            "duration_type": "timed",
            "expires_at_participant_id": None,
            "expires_at_game_time_seconds": game_time + 60,
            "metadata": {
                "source_spell_key": "thaumaturgy",
                "source_spell_name": spell_context["spell_name"],
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "description": description,
                "mechanical": False,
                "narrative": True,
                "visible_to_all": True,
                "freeform": True,
                "spell_level": 0,
                "selected_variant_key": variant_key,
                "utility": "thaumaturgy",
                "allowed_effects": sorted(cls._THAUMATURGY_ALLOWED_EFFECTS),
            },
            "display_label": spell_context["spell_name"],
        }

        attacker_data = cls._as_dict(attacker_model.state_json)
        effects = attacker_data.get("active_spell_effects")
        if not isinstance(effects, list):
            effects = []
        effects.append(effect)
        attacker_data["active_spell_effects"] = effects
        attacker_model.state_json = finalize_session_state_data(
            attacker_data,
            game_time_seconds=game_time,
        )
        flag_modified(attacker_model, "state_json")
        db.add(attacker_model)

        short = description if len(description) <= 120 else f"{description[:117]}..."
        spell_name = spell_context["spell_name"]
        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=f"{spell_name}: \"{short}\"",
            log_message=f"{attacker['display_name']} conjurou {spell_name}: \"{short}\".",
            extra={
                "created_effect_id": effect_id,
                "selected_variant_key": variant_key,
                "__player_state_ids_to_emit": {attacker["ref_id"]},
            },
        )
