from __future__ import annotations

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


def has_condition(participant: dict, condition_type: str) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") == condition_type:
            return True
    return False


def is_action_blocked(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") in _INCAPACITATING_CONDITIONS:
            return True
    return False


def is_movement_blocked(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") in _MOVEMENT_BLOCKING_CONDITIONS:
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
