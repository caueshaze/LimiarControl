from __future__ import annotations

import logging
from typing import Literal

from app.schemas.campaign_entity_shared import AbilityName

logger = logging.getLogger(__name__)

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

_LB_TO_KG = 0.45359237
_ENCUMBRANCE_AFFECTING_ABILITIES = frozenset({"strength", "dexterity", "constitution"})


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


def is_incapacitated(participant: dict) -> bool:
    return any(has_condition(participant, c) for c in _INCAPACITATING_CONDITIONS)


def get_fall_damage_immunity_threshold(participant: dict) -> tuple[float | None, str | None]:
    best: float | None = None
    label: str | None = None
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata") or {}
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue
        if declarative.get("type") != "fall_damage_immunity_threshold":
            continue
        params = declarative.get("params") or {}
        threshold = params.get("max_distance_meters")
        if not isinstance(threshold, (int, float)):
            continue
        if best is None or float(threshold) > best:
            best = float(threshold)
            label = (
                metadata.get("selected_variant_label")
                or effect.get("display_label")
                or metadata.get("source_spell_name")
                or "Graça do Gato"
            )
    return best, label


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


def compute_encumbrance_tier_from_lb(strength_score: float, weight_lb: float) -> str:
    if weight_lb > strength_score * 15:
        return "overloaded"
    if weight_lb > strength_score * 10:
        return "heavily_encumbered"
    if weight_lb > strength_score * 5:
        return "encumbered"
    return "normal"


def apply_encumbrance_movement_penalty(base_speed_meters: float, encumbrance_tier: str) -> float:
    if encumbrance_tier == "overloaded":
        return 0.0
    if encumbrance_tier == "heavily_encumbered":
        return max(0.0, base_speed_meters - 6)
    if encumbrance_tier == "encumbered":
        return max(0.0, base_speed_meters - 3)
    return base_speed_meters


def _get_encumbrance_tier_for_participant(participant: dict) -> str:
    tier = participant.get("encumbrance_tier")
    if isinstance(tier, str) and tier in ("normal", "encumbered", "heavily_encumbered", "overloaded"):
        return tier

    strength = participant.get("strength_score")
    weight_kg = participant.get("total_weight_kg")
    if isinstance(strength, (int, float)) and isinstance(weight_kg, (int, float)) and strength > 0:
        weight_lb = weight_kg / _LB_TO_KG
        return compute_encumbrance_tier_from_lb(strength, weight_lb)

    return "normal"


def resolve_check_advantage_mode(
    participant: dict,
    ability: AbilityName,
    skill: str | None = None,
    target_participant_id: str | None = None,
    manual_mode: Literal["advantage", "normal", "disadvantage"] = "normal",
) -> Literal["advantage", "normal", "disadvantage"]:
    automatic_mode = "normal"
    active_effects = participant.get("active_effects") or []
    logger.info(
        "[resolve_check_advantage_mode] participant_id=%s ability=%s skill=%s target_participant_id=%s active_effects_count=%s",
        participant.get("id") or participant.get("ref_id"),
        ability,
        skill,
        target_participant_id,
        len(active_effects),
    )
    matched = 0
    seen_keys: set[str] = set()
    for effect in active_effects:
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

        against = params.get("against")
        if against == "selected_target" and target_participant_id != metadata.get("selected_target_participant_id"):
            continue

        dedup_key = f"{_declarative_effect_group_key(metadata, effect, effect_type, ability)}|{effect_type}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        if effect_type == "advantage_on_checks":
            automatic_mode = combine_advantage_modes(automatic_mode, "advantage")
            matched += 1
        elif effect_type == "disadvantage_on_checks":
            automatic_mode = combine_advantage_modes(automatic_mode, "disadvantage")
            matched += 1
    encumbrance_tier = _get_encumbrance_tier_for_participant(participant)
    if encumbrance_tier in ("heavily_encumbered", "overloaded") and ability in _ENCUMBRANCE_AFFECTING_ABILITIES:
        automatic_mode = combine_advantage_modes(automatic_mode, "disadvantage")

    final = combine_advantage_modes(manual_mode, automatic_mode)
    logger.info(
        "[resolve_check_advantage_mode] matched=%s manual_mode=%s automatic_mode=%s final=%s",
        matched,
        manual_mode,
        automatic_mode,
        final,
    )
    return final


def explain_check_modifier_sources(
    participant: dict,
    *,
    ability: AbilityName,
    roll_type: Literal["ability", "skill"] = "ability",
    skill: str | None = None,
    target_participant_id: str | None = None,
) -> list[dict]:
    explanations: list[dict] = []
    active_effects = participant.get("active_effects") or []
    logger.info(
        "[explain_check_modifier_sources] participant_id=%s ability=%s roll_type=%s skill=%s target_participant_id=%s active_effects_count=%s",
        participant.get("id") or participant.get("ref_id"),
        ability,
        roll_type,
        skill,
        target_participant_id,
        len(active_effects),
    )
    seen_keys: set[str] = set()
    for effect in active_effects:
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

        dedup_key = f"{_declarative_effect_group_key(metadata, effect, effect_type, params.get('ability', ''))}|{effect_type}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

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
    encumbrance_tier = _get_encumbrance_tier_for_participant(participant)
    if encumbrance_tier in ("heavily_encumbered", "overloaded") and ability in _ENCUMBRANCE_AFFECTING_ABILITIES:
        explanations.append({
            "source_label": "Carga",
            "modifier_type": "disadvantage",
            "roll_type": roll_type,
            "ability": ability,
            "skill": skill if roll_type == "skill" else None,
            "against": "any",
            "selected_target_participant_id": None,
            "selected_target_display_name": None,
            "applied": True,
            "skip_reason": None,
            "reason": "encumbrance",
        })

    logger.info(
        "[explain_check_modifier_sources] explanations_count=%s applied_count=%s",
        len(explanations),
        sum(1 for e in explanations if e.get("applied")),
    )
    return explanations


def _declarative_effect_group_key(
    metadata: dict, effect: dict, effect_type: str, params_key: str
) -> str:
    group_id = metadata.get("declarative_effect_group_id")
    if isinstance(group_id, str) and group_id:
        return group_id
    source = metadata.get("source_spell_key") or metadata.get("source_spell_name")
    if isinstance(source, str) and source:
        variant = metadata.get("selected_variant_key") or ""
        return f"{source}|{variant}|{effect_type}|{params_key}"
    effect_id = effect.get("id")
    if isinstance(effect_id, str) and effect_id:
        return effect_id
    return f"__unknown_{id(effect)}"


def _passive_bonus_group_key(metadata: dict, effect: dict, params: dict) -> str:
    return _declarative_effect_group_key(
        metadata,
        effect,
        "passive_skill_bonus",
        f"{params.get('skill', '')}|{params.get('bonus', '')}",
    )


def _carrying_capacity_group_key(metadata: dict, effect: dict, params: dict) -> str:
    return _declarative_effect_group_key(
        metadata,
        effect,
        "carrying_capacity_multiplier",
        str(params.get("multiplier", "")),
    )


def _movement_speed_group_key(metadata: dict, effect: dict, params: dict) -> str:
    return _declarative_effect_group_key(
        metadata,
        effect,
        "modify_movement_speed",
        str(params.get("bonus_meters", "")),
    )


def get_passive_skill_bonus(participant: dict, skill: str) -> int:
    groups: dict[str, int] = {}
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue
        if declarative.get("type") != "passive_skill_bonus":
            continue
        params = declarative.get("params")
        if not isinstance(params, dict) or params.get("skill") != skill:
            continue
        bonus = params.get("bonus")
        if not isinstance(bonus, int):
            continue
        key = _passive_bonus_group_key(metadata, effect, params)
        current = groups.get(key)
        if current is None or bonus > current:
            groups[key] = bonus
    return sum(groups.values())


def get_carrying_capacity_multiplier(participant: dict) -> float:
    groups: dict[str, float] = {}
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue
        if declarative.get("type") != "carrying_capacity_multiplier":
            continue
        params = declarative.get("params")
        if not isinstance(params, dict):
            continue
        multiplier = params.get("multiplier")
        if not isinstance(multiplier, (int, float)):
            continue
        key = _carrying_capacity_group_key(metadata, effect, params)
        current = groups.get(key)
        if current is None or multiplier > current:
            groups[key] = float(multiplier)
    if not groups:
        return 1.0
    return max(groups.values())


def get_movement_speed_bonus_meters(participant: dict) -> tuple[float, list[dict]]:
    total_bonus = 0.0
    sources: list[dict] = []
    groups: dict[str, float] = {}
    group_sources: dict[str, dict] = {}
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue
        if declarative.get("type") != "modify_movement_speed":
            continue
        params = declarative.get("params")
        if not isinstance(params, dict):
            continue
        bonus = params.get("bonus_meters")
        if not isinstance(bonus, (int, float)):
            continue
        key = _movement_speed_group_key(metadata, effect, params)
        current = groups.get(key)
        if current is None or bonus > current:
            groups[key] = float(bonus)
            label = (
                metadata.get("selected_variant_label")
                or effect.get("display_label")
                or metadata.get("source_spell_name")
                or "Movement speed bonus"
            )
            group_sources[key] = {
                "label": label,
                "value": float(bonus),
                "type": "modify_movement_speed",
            }
    for source in group_sources.values():
        total_bonus += source["value"]
        sources.append(source)
    return total_bonus, sources
