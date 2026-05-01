from __future__ import annotations

from typing import Literal

from app.schemas.campaign_entity_shared import AbilityName

_INCAPACITATING_CONDITIONS = frozenset(
    {"incapacitated", "paralyzed", "stunned", "unconscious", "petrified"}
)
_MOVEMENT_BLOCKING_CONDITIONS = frozenset(
    {
        "incapacitated",
        "paralyzed",
        "stunned",
        "unconscious",
        "petrified",
        "restrained",
        "grappled",
    }
)
_MOVEMENT_HALVING_CONDITIONS = frozenset({"prone"})


def _iter_declarative_spell_effects(participant: dict):
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if isinstance(declarative, dict):
            yield declarative


def has_condition(participant: dict, condition_type: str) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") == condition_type:
            return True
    return False


def is_action_blocked(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") in _INCAPACITATING_CONDITIONS:
            return True
    for declarative in _iter_declarative_spell_effects(participant):
        if declarative.get("type") == "restrict_action":
            params = declarative.get("params")
            if isinstance(params, dict) and params.get("action") == "actions":
                return True
    return False


def is_movement_blocked(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") in _MOVEMENT_BLOCKING_CONDITIONS:
            return True
    for declarative in _iter_declarative_spell_effects(participant):
        if declarative.get("type") == "restrict_action":
            params = declarative.get("params")
            if isinstance(params, dict) and params.get("action") == "movement":
                return True
    return False


def is_movement_halved(participant: dict) -> bool:
    if is_movement_blocked(participant):
        return False
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") in _MOVEMENT_HALVING_CONDITIONS:
            return True
    return False


def can_see(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        ctype = effect.get("condition_type") if effect.get("kind") == "condition" else None
        if ctype in ("blinded", "unconscious", "petrified"):
            return False
    return True


def is_invisible(participant: dict) -> bool:
    return has_condition(participant, "invisible")


def is_heavily_obscured(participant: dict) -> bool:
    return has_condition(participant, "heavily_obscured")


def is_lightly_obscured(participant: dict) -> bool:
    return has_condition(participant, "lightly_obscured")


def resolve_check_advantage_mode(
    participant: dict,
    ability: AbilityName,
    target_participant_id: str | None = None,
) -> Literal["advantage", "normal", "disadvantage"]:
    has_adv = False
    has_dis = False
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue

        effect_type = declarative.get("type")
        params = declarative.get("params")
        if not isinstance(params, dict) or params.get("ability") != ability:
            continue

        # Check "against" constraint if present
        against = params.get("against")
        if against == "selected_target":
            # Only applies if target matches the spell's selected target
            if target_participant_id != metadata.get("selected_target_participant_id"):
                continue
        elif against == "effect_target":
            # For advantage_on_checks applied to caster, effect_target is caster
            # (this constraint doesn't filter based on target_participant_id)
            pass
        # "any" or None means no constraint

        if effect_type == "advantage_on_checks":
            has_adv = True
        elif effect_type == "disadvantage_on_checks":
            has_dis = True
    if has_adv and not has_dis:
        return "advantage"
    if has_dis and not has_adv:
        return "disadvantage"
    return "normal"


def explain_check_modifier_sources(
    participant: dict,
    *,
    ability: AbilityName,
    roll_type: Literal["ability", "skill"] = "ability",
    skill: str | None = None,
    target_participant_id: str | None = None,
) -> list[dict]:
    explanations: list[dict] = []
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue

        effect_type = declarative.get("type")
        if effect_type not in {"advantage_on_checks", "disadvantage_on_checks"}:
            continue

        params = declarative.get("params")
        if not isinstance(params, dict):
            continue

        against = (
            params.get("against")
            if params.get("against") in {"any", "effect_target", "selected_target"}
            else "any"
        )
        effect_ability = params.get("ability")
        modifier_type = "advantage" if effect_type == "advantage_on_checks" else "disadvantage"
        entry = {
            "source_label": metadata.get("source_spell_name")
            or effect.get("display_label")
            or "Spell effect",
            "modifier_type": modifier_type,
            "roll_type": roll_type,
            "ability": effect_ability if isinstance(effect_ability, str) else None,
            "skill": skill if roll_type == "skill" else None,
            "against": against,
            "selected_target_participant_id": metadata.get("selected_target_participant_id")
            if isinstance(metadata.get("selected_target_participant_id"), str)
            else None,
            "selected_target_display_name": metadata.get("selected_target_display_name")
            if isinstance(metadata.get("selected_target_display_name"), str)
            else None,
            "applied": False,
            "skip_reason": None,
        }

        if effect_ability != ability:
            entry["skip_reason"] = "skill_mismatch" if roll_type == "skill" else "ability_mismatch"
            explanations.append(entry)
            continue

        if against == "selected_target":
            selected_target_id = metadata.get("selected_target_participant_id")
            if not isinstance(target_participant_id, str) or not target_participant_id.strip():
                entry["skip_reason"] = "missing_target"
                explanations.append(entry)
                continue
            if target_participant_id != selected_target_id:
                entry["skip_reason"] = "target_mismatch"
                explanations.append(entry)
                continue

        entry["applied"] = True
        explanations.append(entry)
    return explanations
