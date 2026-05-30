from __future__ import annotations

from typing import Literal

from app.services.combat_service.exceptions import _roll_dice_expression


def target_wearing_metal_armor(participant: dict | None) -> bool:
    if not isinstance(participant, dict):
        return False

    equipped_armor = participant.get("equippedArmor")
    if isinstance(equipped_armor, dict):
        armor_type = equipped_armor.get("armorType")
        armor_material = equipped_armor.get("armorMaterial")
        if isinstance(armor_type, str) and armor_type != "none" and armor_material == "metal":
            return True

    return participant.get("wearingMetalArmor") is True


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


def _declarative_effect_group_key(metadata: dict, effect: dict, effect_type: str, params_key: str) -> str:
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


def resolve_jump_distance_multiplier(participant: dict) -> int:
    multiplier = 1
    for effect in participant.get("active_effects") or []:
        if not isinstance(effect, dict):
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("source_spell_key") or "").strip().lower() != "jump":
            continue
        raw = metadata.get("jump_distance_multiplier")
        if isinstance(raw, (int, float)) and raw > multiplier:
            multiplier = int(raw)
    return multiplier


def has_spider_climb(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if not isinstance(effect, dict):
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("source_spell_key") or "").strip().lower() == "spider_climb":
            return True
    return False


def resolve_climb_speed_mode(participant: dict) -> dict:
    enabled = has_spider_climb(participant)
    return {
        "hasSpiderClimb": enabled,
        "grantsClimbSpeed": enabled,
        "climbSpeedEqualsWalkingSpeed": enabled,
        "canMoveOnVerticalSurfaces": enabled,
        "canMoveOnCeilings": enabled,
        "canMoveUpsideDown": enabled,
        "handsFreeWhileClimbing": enabled,
        "grantsExtraMovement": False,
        "grantsFlight": False,
        "preventsFallDamage": False,
    }


def has_feather_fall_protection(participant: dict) -> bool:
    for effect in participant.get("active_effects") or []:
        if not isinstance(effect, dict):
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("source_spell_key") or "").strip().lower() != "feather_fall":
            continue
        if metadata.get("prevents_fall_damage") is True:
            return True
    return False


def resolve_armor_class_floor(participant: dict) -> int | None:
    floor_value: int | None = None
    for effect in participant.get("active_effects") or []:
        if not isinstance(effect, dict):
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("sets_minimum_ac") is not True:
            continue
        raw = metadata.get("armor_class_floor")
        if not isinstance(raw, int):
            raw = metadata.get("ac_floor")
        if isinstance(raw, int):
            floor_value = raw if floor_value is None else max(floor_value, raw)
    return floor_value


def _normalize_roll_dice_modifier_declarative(declarative: dict) -> dict | None:
    raw_type = declarative.get("type")
    params = declarative.get("params")
    if not isinstance(params, dict):
        return None
    if raw_type == "roll_bonus_dice":
        mode = "bonus"
        roll_types = params.get("roll_types")
        dice = params.get("dice")
    elif raw_type == "roll_dice_modifier":
        mode = params.get("mode")
        roll_types = params.get("roll_types")
        dice = params.get("dice")
        consume_on_apply = params.get("consume_on_apply") is True
    else:
        return None
    if raw_type == "roll_bonus_dice":
        consume_on_apply = False
    if mode not in {"bonus", "penalty"}:
        return None
    if not isinstance(roll_types, list) or not all(isinstance(rt, str) for rt in roll_types):
        return None
    if not isinstance(dice, str) or not dice.strip():
        return None
    return {
        "type": "roll_dice_modifier",
        "mode": mode,
        "roll_types": roll_types,
        "dice": dice.strip(),
        "consume_on_apply": consume_on_apply,
    }


def get_roll_bonus_dice_sources(
    participant: dict,
    *,
    roll_type: Literal["attack", "save", "ability", "skill"],
) -> list[dict]:
    sources: list[dict] = []
    seen_keys: set[str] = set()
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue
        normalized = _normalize_roll_dice_modifier_declarative(declarative)
        if not isinstance(normalized, dict):
            continue
        roll_types = normalized.get("roll_types")
        dice = normalized.get("dice")
        mode = normalized.get("mode")
        consume_on_apply = normalized.get("consume_on_apply") is True
        if not isinstance(roll_types, list) or roll_type not in roll_types:
            continue
        if not isinstance(dice, str) or not dice.strip():
            continue
        dedup_key = f"{_declarative_effect_group_key(metadata, effect, 'roll_dice_modifier', roll_type)}|{dice.strip()}|{mode}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        # _roll_dice_expression returns the rolled total (int); individual die
        # results are not exposed, so rolls stays empty in the source payload.
        total = _roll_dice_expression(dice.strip())
        signed_total = -abs(total) if mode == "penalty" else abs(total)
        source_label = metadata.get("source_spell_name") or effect.get("display_label") or "Spell effect"
        sign_label = "-" if mode == "penalty" else "+"
        sources.append(
            {
                "source_label": source_label,
                "modifier_type": "roll_dice_modifier",
                "roll_type": roll_type,
                "mode": mode,
                "dice": dice.strip(),
                "rolls": [],
                "signed_total": signed_total,
                "display_label": f"{source_label}: {sign_label}{dice.strip()}",
                "effect_id": effect.get("id") if isinstance(effect.get("id"), str) else None,
                "concentration_group": metadata.get("concentration_group") if isinstance(metadata.get("concentration_group"), str) else None,
                "consume_on_apply": consume_on_apply,
                "applied": True,
                "skip_reason": None,
            }
        )
    return sources


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
        key = _declarative_effect_group_key(
            metadata,
            effect,
            "passive_skill_bonus",
            f"{params.get('skill', '')}|{params.get('bonus', '')}",
        )
        current = groups.get(key)
        if current is None or bonus > current:
            groups[key] = bonus
    return sum(groups.values())
