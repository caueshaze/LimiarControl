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
) -> Literal["advantage", "normal", "disadvantage"]:
    has_adv = False
    has_dis = False
    for declarative in _iter_declarative_spell_effects(participant):
        effect_type = declarative.get("type")
        params = declarative.get("params")
        if not isinstance(params, dict) or params.get("ability") != ability:
            continue
        if effect_type == "advantage_on_checks":
            has_adv = True
        elif effect_type == "disadvantage_on_checks":
            has_dis = True
    if has_adv and not has_dis:
        return "advantage"
    if has_dis and not has_adv:
        return "disadvantage"
    return "normal"
