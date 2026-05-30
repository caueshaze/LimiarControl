from __future__ import annotations

from ..entity_size import normalize_size_category, size_carrying_capacity_multiplier
from .predicates_spell_metadata import _declarative_effect_group_key

_LB_TO_KG = 0.45359237


def compute_encumbrance_tier_from_lb(
    strength_score: float,
    weight_lb: float,
    *,
    capacity_multiplier: float = 1.0,
) -> str:
    effective = strength_score * capacity_multiplier
    if weight_lb > effective * 15:
        return "overloaded"
    if weight_lb > effective * 10:
        return "heavily_encumbered"
    if weight_lb > effective * 5:
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
        key = _declarative_effect_group_key(
            metadata,
            effect,
            "carrying_capacity_multiplier",
            str(params.get("multiplier", "")),
        )
        current = groups.get(key)
        if current is None or multiplier > current:
            groups[key] = float(multiplier)
    if not groups:
        return 1.0
    return max(groups.values())


def get_effective_capacity_multiplier(participant: dict) -> float:
    effect_mult = get_carrying_capacity_multiplier(participant)
    raw_size = participant.get("effective_size") or participant.get("base_size")
    size_cat = normalize_size_category(raw_size)
    size_mult = size_carrying_capacity_multiplier(size_cat)
    return effect_mult * size_mult


def _get_encumbrance_tier_for_participant(participant: dict) -> str:
    tier = participant.get("encumbrance_tier")
    if isinstance(tier, str) and tier in ("normal", "encumbered", "heavily_encumbered", "overloaded"):
        return tier

    strength = participant.get("strength_score")
    weight_kg = participant.get("total_weight_kg")
    if isinstance(strength, (int, float)) and isinstance(weight_kg, (int, float)) and strength > 0:
        weight_lb = weight_kg / _LB_TO_KG
        multiplier = get_effective_capacity_multiplier(participant)
        return compute_encumbrance_tier_from_lb(strength, weight_lb, capacity_multiplier=multiplier)

    return "normal"


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
        key = _declarative_effect_group_key(
            metadata,
            effect,
            "modify_movement_speed",
            str(params.get("bonus_meters", "")),
        )
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


def get_participant_encumbrance_tier(participant: dict) -> str:
    return _get_encumbrance_tier_for_participant(participant)
