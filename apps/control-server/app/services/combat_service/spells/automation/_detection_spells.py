from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.session_state_finalize import finalize_session_state_data
from ...exceptions import CombatServiceError


class DetectionSpellsAutomationMixin:
    @classmethod
    async def _cast_detect_magic_automation(
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
        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(
            session_id, state, result["removed_area_effects"],
        )
        concentration_group = str(uuid4())
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        cls._append_effect_to_participant(
            attacker,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                expires_at_participant_id=None,
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + 600,
                metadata={
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": "detect_magic",
                    "source_spell_name": spell_name,
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_magic",
                    "radius_meters": 9,
                    "can_reveal_aura_with_action": True,
                    "reveals_magic_school": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                display_label=spell_name,
            ),
        )
        flag_modified(state, "participants")

        summary_text = f"{spell_name} ativa: presença de magia em até 9m por até 10 minutos."
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} e abriu sentidos arcanos em 9m."
            ),
            extra={
                "concentration_group": concentration_group,
            },
        )

    @classmethod
    async def _cast_detect_poison_disease_automation(
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
        variant_key = getattr(req, "variant_key", None)
        if variant_key:
            raise CombatServiceError("detect_poison_disease não possui variantes.", status_code=400)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(session_id, state, result["removed_area_effects"])
        concentration_group = str(uuid4())
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        cls._append_effect_to_participant(
            attacker,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                expires_at_participant_id=None,
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + 600,
                metadata={
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": "detect_poison_disease",
                    "source_spell_name": spell_name,
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_poison_disease",
                    "radius_meters": 9,
                    "detects_poisons": True,
                    "detects_poisonous_creatures": True,
                    "detects_diseases": True,
                    "can_identify_poison_or_disease_with_action": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                display_label=spell_name,
            ),
        )
        flag_modified(state, "participants")

        summary_text = f"{spell_name} ativa: detecção de venenos e doenças em até 9m por até 10 minutos."
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} e abriu sentidos em 9m."
            ),
            extra={
                "concentration_group": concentration_group,
            },
        )

    @classmethod
    async def _cast_detect_evil_and_good_automation(
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
        variant_key = getattr(req, "variant_key", None)
        if variant_key:
            raise CombatServiceError("detect_evil_and_good não possui variantes.", 400)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(session_id, state, result["removed_area_effects"])
        concentration_group = str(uuid4())
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        cls._append_effect_to_participant(
            attacker,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                expires_at_participant_id=None,
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + 600,
                metadata={
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": "detect_evil_and_good",
                    "source_spell_name": spell_name,
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_evil_and_good",
                    "radius_meters": 9,
                    "detects_creature_types": [
                        "aberration", "celestial", "elemental",
                        "fey", "fiend", "undead",
                    ],
                    "detects_consecrated_or_desecrated": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                display_label=spell_name,
            ),
        )
        flag_modified(state, "participants")

        summary_text = (
            f"{spell_name} ativa: detecção de criaturas sobrenaturais e locais ou objetos "
            "consagrados/profanados em até 9m por até 10 minutos."
        )
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} e abriu sentidos em 9m."
            ),
            extra={
                "concentration_group": concentration_group,
            },
        )

    @classmethod
    async def _cast_comprehend_languages_automation(
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
        raw_variant = getattr(req, "variant_key", None)
        if raw_variant is not None:
            raise CombatServiceError(
                "Compreender Idiomas não possui variantes.",
                400,
            )

        attacker_data = cls._as_dict(attacker_model.state_json)
        existing = attacker_data.get("active_spell_effects") or []
        attacker_data["active_spell_effects"] = [
            e for e in existing
            if not (
                e.get("kind") == "spell_effect"
                and e.get("metadata", {}).get("source_spell_key") == "comprehend_languages"
            )
        ]

        game_time = get_game_time_seconds(session_id, db)
        effect_id = f"narrative_effect:{uuid4()}"
        spell_name = spell_context["spell_name"]
        effect = {
            "id": effect_id,
            "kind": "spell_effect",
            "duration_type": "timed",
            "expires_at_participant_id": None,
            "expires_at_game_time_seconds": game_time + 3600,
            "metadata": {
                "source_spell_key": "comprehend_languages",
                "source_spell_name": spell_name,
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "mechanical": False,
                "narrative": True,
                "visible_to_all": True,
                "utility": "comprehend_languages",
                "spell_level": 1,
                "duration_seconds": 3600,
                "understands_spoken_languages": True,
                "understands_written_languages": True,
                "requires_touch_for_written_text": True,
                "literal_meaning_only": True,
                "deciphers_secret_messages": False,
            },
            "display_label": spell_name,
        }

        attacker_data["active_spell_effects"].append(effect)
        attacker_model.state_json = finalize_session_state_data(
            attacker_data,
            game_time_seconds=game_time,
        )
        flag_modified(attacker_model, "state_json")
        db.add(attacker_model)

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=f"{spell_name} ativa: compreensão literal de idiomas por 1 hora.",
            log_message=f"{attacker['display_name']} conjurou {spell_name}.",
            extra={
                "created_effect_id": effect_id,
                "__player_state_ids_to_emit": {attacker["ref_id"]},
            },
        )
