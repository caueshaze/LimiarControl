from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

_INCAPACITATING_CONDITIONS = frozenset({"incapacitated", "paralyzed", "stunned", "unconscious", "petrified"})
_MOVEMENT_BLOCKING_CONDITIONS = frozenset({
    "incapacitated", "paralyzed", "stunned", "unconscious", "petrified", "restrained", "grappled",
})
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


def combine_advantage_modes(*modes: str | None) -> Literal["advantage", "normal", "disadvantage"]:
    advantage_count = 0
    disadvantage_count = 0
    for mode in modes:
        if mode == "advantage":
            advantage_count += 1
        elif mode == "disadvantage":
            disadvantage_count += 1
    if advantage_count > disadvantage_count:
        return "advantage"
    if disadvantage_count > advantage_count:
        return "disadvantage"
    return "normal"


def resolve_actor_participant(session_state, actor_ref_id: str) -> dict | None:
    if not actor_ref_id:
        logger.info("[resolve_actor_participant] empty actor_ref_id")
        return None
    participants = getattr(session_state, "participants", None)
    if not isinstance(participants, list):
        logger.info("[resolve_actor_participant] no participants list")
        return None

    def _match(entry: dict, key: str) -> bool:
        value = entry.get(key)
        return isinstance(value, str) and value == actor_ref_id

    for key in ("ref_id", "actor_user_id", "character_id"):
        for entry in participants:
            if not isinstance(entry, dict):
                continue
            if _match(entry, key):
                logger.info(
                    "[resolve_actor_participant] matched key=%s participant_id=%s ref_id=%s actor_user_id=%s character_id=%s",
                    key,
                    entry.get("id"),
                    entry.get("ref_id"),
                    entry.get("actor_user_id"),
                    entry.get("character_id"),
                )
                return entry
    logger.info("[resolve_actor_participant] no match for actor_ref_id=%s participants_count=%s", actor_ref_id, len(participants))
    return None


def has_condition(participant: dict, condition_type: str) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") == condition_type:
            return True
    return False


def has_condition_immunity(participant: dict, condition_type: str) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata") or {}
        if metadata.get("condition_immunity") and condition_type in (metadata.get("immune_conditions") or []):
            return True
    return False


def is_incapacitated(participant: dict) -> bool:
    return any(has_condition(participant, c) for c in _INCAPACITATING_CONDITIONS)


def is_action_blocked(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") in _INCAPACITATING_CONDITIONS:
            return True
        if effect.get("kind") == "spell_effect" and (effect.get("metadata") or {}).get("action_blocked") is True:
            return True
    for declarative in _iter_declarative_spell_effects(participant):
        if declarative.get("type") == "restrict_action":
            params = declarative.get("params")
            if isinstance(params, dict) and params.get("action") == "actions":
                return True
    return False


def is_reaction_blocked(participant: dict) -> bool:
    for declarative in _iter_declarative_spell_effects(participant):
        if declarative.get("type") != "restrict_action":
            continue
        params = declarative.get("params")
        if isinstance(params, dict) and params.get("action") == "reactions":
            return True
    return False


def is_movement_blocked(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") == "condition" and effect.get("condition_type") in _MOVEMENT_BLOCKING_CONDITIONS:
            return True
        if effect.get("kind") == "spell_effect" and (effect.get("metadata") or {}).get("movement_blocked") is True:
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


def suppresses_invisibility_benefit(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("suppresses_invisibility_benefit") is True:
            return True
    return False


def is_heavily_obscured(participant: dict) -> bool:
    return has_condition(participant, "heavily_obscured")


def is_lightly_obscured(participant: dict) -> bool:
    return has_condition(participant, "lightly_obscured")
