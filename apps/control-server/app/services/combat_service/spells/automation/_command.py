from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.roll_resolution import resolve_saving_throw
from ...condition_effects_saves import modify_saving_throw
from ...exceptions import CombatServiceError


def _build_command_effect_metadata(
    variant_key: str, variant_label: str, caster: dict, target: dict
) -> dict:
    base: dict = {
        "source_spell_key": "command",
        "source_spell_name": "Comando",
        "mechanical": True,
        "utility": "command",
        "control_effect": True,
        "commanded": True,
        "command_word": variant_key,
        "command_label": variant_label,
        "source_participant_id": caster["id"],
        "owner_participant_id": target["id"],
        "created_by_participant_id": caster["id"],
        "concentration": False,
        "saving_throw_ability": "wisdom",
        "saving_throw_failed": True,
        "expires_on_target_turn_end": True,
    }
    if variant_key == "halt":
        base["action_blocked"] = True
        base["movement_blocked"] = True
    elif variant_key == "grovel":
        base["action_blocked"] = True
        base["movement_blocked"] = True
        base["apply_prone_on_turn_start"] = True
        base["ends_turn_after_prone"] = True
    elif variant_key == "drop":
        base["action_blocked"] = True
        base["movement_blocked"] = True
        base["must_drop_held_items"] = True
    elif variant_key == "flee":
        base["action_blocked"] = True
        base["must_use_movement"] = True
        base["forced_movement_intent"] = "away_from_caster"
        base["forced_movement_anchor_participant_id"] = caster["id"]
    elif variant_key == "approach":
        base["action_blocked"] = True
        base["must_use_movement"] = True
        base["forced_movement_intent"] = "toward_caster"
        base["forced_movement_anchor_participant_id"] = caster["id"]
    return base


class CommandAutomationMixin:
    @classmethod
    async def _cast_command_automation(
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
            COMMAND_VARIANTS,
            COMMAND_VARIANT_LABELS,
            is_undead_participant,
            target_cannot_understand_command,
        )

        if target_participant is None:
            raise CombatServiceError("Comando requer um alvo.", 400)

        variant_key = cls._normalize_lookup(getattr(req, "variant_key", None) or "")
        if not variant_key:
            raise CombatServiceError(
                "Comando exige variant_key (approach/drop/flee/grovel/halt).", 400
            )
        if variant_key not in COMMAND_VARIANTS:
            raise CombatServiceError(
                f"Comando não suporta '{variant_key}'. Valores válidos: {sorted(COMMAND_VARIANTS)}.",
                400,
            )

        spell_name = spell_context["spell_name"]
        target_name = target_participant["display_name"]
        variant_label = COMMAND_VARIANT_LABELS.get(variant_key, variant_key)

        if is_undead_participant(target_participant):
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=target_name,
                target_kind=target_participant["kind"],
                action_kind="saving_throw",
                summary_text=f"Comando não teve efeito em {target_name} (morto-vivo).",
                log_message=f"{attacker['display_name']} conjurou {spell_name}; {target_name} é morto-vivo e imune.",
                extra={"immune": True, "immune_reason": "undead", "command_word": variant_key},
            )

        if target_cannot_understand_command(attacker, target_participant):
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=target_name,
                target_kind=target_participant["kind"],
                action_kind="saving_throw",
                summary_text=f"Comando não teve efeito em {target_name} (não entende o idioma).",
                log_message=f"{attacker['display_name']} conjurou {spell_name}; {target_name} não entende a ordem.",
                extra={"immune": True, "immune_reason": "cannot_understand", "command_word": variant_key},
            )

        save_mod = modify_saving_throw(
            target_participant,
            spell_context.get("save_ability") or "wisdom",
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
            ability=spell_context.get("save_ability") or "wisdom",
            advantage_mode=save_mod.result,
            dc=cls._safe_int(spell_context.get("save_dc"), 0),
        )
        roll_result.check_modifier_sources = [
            *save_mod.advantage_source_details,
            *save_mod.disadvantage_source_details,
            *(roll_result.check_modifier_sources or []),
        ]
        roll_result.is_gm_roll = is_gm
        is_saved = bool(roll_result.success)

        if not is_saved:
            metadata = _build_command_effect_metadata(variant_key, variant_label, attacker, target_participant)
            effect = cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="until_turn_end",
                expires_at_participant_id=target_participant["id"],
                metadata=metadata,
                display_label=f"{spell_name}: {variant_label}",
            )
            cls._append_effect_to_participant(target_participant, effect)
            flag_modified(state, "participants")

        if is_saved:
            summary_text = f"{target_name} resistiu ao {spell_name}."
            log_msg = (
                f"{attacker['display_name']} conjurou {spell_name} ({variant_label}) em {target_name}: "
                f"salvaguarda bem-sucedida."
            )
        else:
            summary_text = (
                f"{target_name} falhou na salvaguarda e deve obedecer ao comando "
                f"'{variant_label}' no próximo turno."
            )
            log_msg = (
                f"{attacker['display_name']} conjurou {spell_name} ({variant_label}) em {target_name}: "
                f"falhou na salvaguarda."
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
                "roll": roll_result.total,
                "roll_result": roll_result,
                "save_ability": spell_context.get("save_ability") or "wisdom",
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": "none",
                "command_word": variant_key,
                "command_label": variant_label,
            },
        )
