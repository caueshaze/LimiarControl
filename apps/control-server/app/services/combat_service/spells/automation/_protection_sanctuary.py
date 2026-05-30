from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.spell_effect_factories import (
    build_protection_from_evil_and_good_effect,
    build_sanctuary_effect,
)
from ...exceptions import CombatServiceError


class ProtectionSanctuaryAutomationMixin:
    @classmethod
    async def _cast_protection_from_evil_and_good_automation(
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
        from ...condition_effects_predicates import (
            PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES,
            PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS,
            get_participant_creature_type,
        )

        if target_participant is None:
            raise CombatServiceError("Proteção Contra Mal e Bem requer um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Proteção Contra Mal e Bem não possui variantes.", 400)

        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(
            session_id,
            state,
            result["removed_area_effects"],
        )
        concentration_group = str(uuid4())

        suppressed_conditions: list[str] = []
        remaining_effects = []
        for e in (target_participant.get("active_effects") or []):
            if (
                e.get("kind") == "condition"
                and e.get("condition_type") in PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS
            ):
                source_id = e.get("source_participant_id")
                source_p = (
                    next(
                        (p for p in (state.participants or []) if p.get("id") == source_id),
                        None,
                    )
                    if source_id
                    else None
                )
                if (
                    source_p
                    and get_participant_creature_type(source_p)
                    in PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES
                ):
                    suppressed_conditions.append(e.get("condition_type", ""))
                    continue
            remaining_effects.append(e)
        target_participant["active_effects"] = remaining_effects

        protected_types = sorted(PROTECTION_FROM_EVIL_AND_GOOD_CREATURE_TYPES)
        immune_conditions = sorted(PROTECTION_FROM_EVIL_AND_GOOD_CONDITIONS)
        effect = build_protection_from_evil_and_good_effect(
            cls._build_combat_spell_effect_context(
                spell_key="protection_from_evil_and_good",
                spell_name=spell_name,
                caster_participant_id=attacker["id"],
                target_participant_id=target_participant["id"],
                game_time_seconds=game_time,
                duration_seconds=600,
                concentration=True,
                concentration_group=concentration_group,
            )
        )
        cls._apply_factory_spell_effect_to_target(
            state=state,
            target_participant=target_participant,
            effect=effect,
            source_spell_key="protection_from_evil_and_good",
        )

        suppression_note = ""
        if suppressed_conditions:
            unique = sorted(set(suppressed_conditions))
            suppression_note = f" Condições removidas: {', '.join(unique)}."

        target_name = target_participant["display_name"]
        summary_text = (
            f"{spell_name} ativa em {target_name}. "
            f"Criaturas protegidas têm desvantagem em ataques contra o alvo."
            + suppression_note
        )
        log_message = (
            f"{attacker['display_name']} conjurou {spell_name} em {target_name}. "
            f"Proteção ativa contra: {', '.join(protected_types)}."
            + suppression_note
        )

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="utility",
            summary_text=summary_text,
            log_message=log_message,
            extra={
                "utility": "protection_from_evil_and_good",
                "concentration_group": concentration_group,
                "protected_creature_types": protected_types,
                "immune_conditions": immune_conditions,
                "suppressed_conditions": suppressed_conditions,
            },
        )

    @classmethod
    async def _cast_sanctuary_automation(
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
            raise CombatServiceError("Santuário requer um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Santuário não possui variantes.", 400)

        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)
        save_dc = int((attacker.get("spellcasting") or {}).get("saveDc") or 0)
        if save_dc <= 0:
            raise CombatServiceError("Santuário requer uma CD de conjuração válida.", 400)

        effect = build_sanctuary_effect(
            cls._build_combat_spell_effect_context(
                spell_key="sanctuary",
                spell_name=spell_name,
                caster_participant_id=attacker["id"],
                target_participant_id=target_participant["id"],
                game_time_seconds=game_time,
                duration_seconds=60,
                concentration=False,
                concentration_group=None,
                spell_save_dc=save_dc,
            )
        )
        cls._apply_factory_spell_effect_to_target(
            state=state,
            target_participant=target_participant,
            effect=effect,
            source_spell_key="sanctuary",
        )

        target_name = target_participant["display_name"]
        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="utility",
            summary_text=(
                f"{spell_name} ativa em {target_name}. "
                f"Atacantes devem passar em um teste de Sabedoria (CD {save_dc}) para alvejá-la."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em {target_name} (CD {save_dc})."
            ),
            extra={
                "utility": "sanctuary",
                "guard_save_dc": save_dc,
                "duration_seconds": 60,
            },
        )
