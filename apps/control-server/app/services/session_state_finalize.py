from __future__ import annotations

import unicodedata

from app.services.persistent_effect_expiry import prune_expired_persisted_effects_from_state
from app.services.dragonborn_breath_weapon import apply_dragonborn_breath_weapon_canonical_state
from app.services.session_rest import ensure_rest_state
from app.services.declarative_effect_lifecycle import terminate_armor_don_effects_from_state


_PLAYER_SHIELD_BONUS = 2
_ARMOR_BASE_PRIORITY = {
    "heavy_armor": 70,
    "medium_armor": 60,
    "light_armor": 50,
    "active_formula": 40,
    "barbarian_unarmored_defense": 30,
    "monk_unarmored_defense": 20,
    "default": 10,
}


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _safe_int(value: object, fallback: int = 0) -> int:
    return value if isinstance(value, int) else fallback


def _safe_optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _normalize_lookup(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("_", " ").replace("-", " ")
    return " ".join(normalized.split())


def _get_ability_score(data: dict, ability_name: str, default: int = 10) -> int:
    abilities = _as_dict(data.get("abilities"))
    value = abilities.get(ability_name)
    return value if isinstance(value, int) else default


def _ability_modifier(score: int) -> int:
    return (score - 10) // 2


def _active_effects_from_state(
    payload: dict,
    active_effects: list[dict] | None,
) -> list[dict]:
    if isinstance(active_effects, list):
        return active_effects
    effects = payload.get("active_spell_effects")
    return effects if isinstance(effects, list) else []


def _normalize_armor_type(payload: dict) -> str:
    armor = _as_dict(payload.get("equippedArmor"))
    return _normalize_lookup(armor.get("armorType"))


def _has_equipped_armor(payload: dict) -> bool:
    return _normalize_armor_type(payload) in {"light", "medium", "heavy"}


def _sum_temp_ac_bonus_effects(effects: list[dict]) -> int:
    total = 0
    for effect in effects:
        if (
            isinstance(effect, dict)
            and effect.get("kind") == "temp_ac_bonus"
            and isinstance(effect.get("numeric_value"), int)
        ):
            total += effect["numeric_value"]
    return total


def _iter_active_armor_class_formula_effects(effects: list[dict]):
    for effect in effects:
        if not isinstance(effect, dict) or effect.get("kind") != "spell_effect":
            continue
        metadata = _as_dict(effect.get("metadata"))
        declarative = _as_dict(metadata.get("declarative_effect"))
        if declarative.get("type") != "armor_class_formula":
            continue
        params = _as_dict(declarative.get("params"))
        base_value = params.get("base_value")
        ability = params.get("ability")
        if not isinstance(base_value, int) or not isinstance(ability, str):
            continue
        yield {
            "base_value": base_value,
            "ability": ability,
            "requires_unarmored": params.get("requires_unarmored") is True,
        }


def _is_armor_class_formula_applicable(payload: dict, formula: dict) -> bool:
    if formula.get("requires_unarmored") is True and _has_equipped_armor(payload):
        return False
    return True


def calculate_player_armor_class_from_state(
    data: dict | None,
    *,
    active_effects: list[dict] | None = None,
) -> int:
    payload = _as_dict(data)
    effects = _active_effects_from_state(payload, active_effects)
    dex_mod = _ability_modifier(_get_ability_score(payload, "dexterity"))
    con_mod = _ability_modifier(_get_ability_score(payload, "constitution"))
    wis_mod = _ability_modifier(_get_ability_score(payload, "wisdom"))
    armor = _as_dict(payload.get("equippedArmor"))

    armor_type = _normalize_lookup(armor.get("armorType"))
    base_ac = _safe_int(armor.get("baseAC"), 0)
    dex_cap = _safe_optional_int(armor.get("dexCap"))
    allows_dex = armor.get("allowsDex")
    if not isinstance(allows_dex, bool):
        allows_dex = armor_type != "heavy"

    candidates: list[dict] = []

    if armor_type == "heavy":
        candidates.append({"value": base_ac, "priority": _ARMOR_BASE_PRIORITY["heavy_armor"], "order": len(candidates)})
    elif armor_type == "medium":
        dex_contribution = dex_mod if dex_cap is None else min(dex_mod, dex_cap)
        candidates.append(
            {
                "value": base_ac + (dex_contribution if allows_dex else 0),
                "priority": _ARMOR_BASE_PRIORITY["medium_armor"],
                "order": len(candidates),
            }
        )
    elif armor_type == "light":
        candidates.append(
            {
                "value": base_ac + (dex_mod if allows_dex else 0),
                "priority": _ARMOR_BASE_PRIORITY["light_armor"],
                "order": len(candidates),
            }
        )
    else:
        candidates.append(
            {
                "value": 10 + dex_mod,
                "priority": _ARMOR_BASE_PRIORITY["default"],
                "order": len(candidates),
            }
        )
        player_class = _normalize_lookup(payload.get("class"))
        if player_class == "barbarian":
            candidates.append(
                {
                    "value": 10 + dex_mod + con_mod,
                    "priority": _ARMOR_BASE_PRIORITY["barbarian_unarmored_defense"],
                    "order": len(candidates),
                }
            )
        if player_class == "monk" and not isinstance(payload.get("equippedShield"), dict):
            candidates.append(
                {
                    "value": 10 + dex_mod + wis_mod,
                    "priority": _ARMOR_BASE_PRIORITY["monk_unarmored_defense"],
                    "order": len(candidates),
                }
            )

    for formula in _iter_active_armor_class_formula_effects(effects):
        if not _is_armor_class_formula_applicable(payload, formula):
            continue
        candidates.append(
            {
                "value": formula["base_value"] + _ability_modifier(_get_ability_score(payload, formula["ability"])),
                "priority": _ARMOR_BASE_PRIORITY["active_formula"],
                "order": len(candidates),
            }
        )

    winning_base = max(
        candidates,
        key=lambda candidate: (
            candidate["value"],
            candidate["priority"],
            -candidate["order"],
        ),
    )

    shield = _as_dict(payload.get("equippedShield"))
    shield_bonus = _safe_int(shield.get("bonus"), 0) if shield else 0
    if shield and shield_bonus == 0:
        shield_bonus = _PLAYER_SHIELD_BONUS

    misc_bonus = _safe_int(payload.get("miscACBonus"), 0)
    fighting_style = _normalize_lookup(payload.get("fightingStyle"))
    defense_bonus = 1 if fighting_style == "defense" and armor_type in {"light", "medium", "heavy"} else 0
    temp_ac_bonus = _sum_temp_ac_bonus_effects(effects)

    return max(0, winning_base["value"] + shield_bonus + misc_bonus + defense_bonus + temp_ac_bonus)


def finalize_session_state_data(
    data: dict | None,
    *,
    game_time_seconds: int | None = None,
) -> dict:
    next_data = ensure_rest_state(data)
    if isinstance(game_time_seconds, int):
        next_data = prune_expired_persisted_effects_from_state(next_data, game_time_seconds)
    next_data = terminate_armor_don_effects_from_state(next_data)
    next_data = apply_dragonborn_breath_weapon_canonical_state(next_data)

    # Wild Shape: use beast form AC instead of equipment-derived AC
    wild_shape = next_data.get("wildShape")
    if isinstance(wild_shape, dict) and wild_shape.get("active"):
        from app.services.wild_shape_catalog import get_form
        form_key = wild_shape.get("formKey")
        form = get_form(form_key) if isinstance(form_key, str) else None
        next_data["armorClass"] = form.armor_class if form is not None else calculate_player_armor_class_from_state(next_data)
    else:
        next_data["armorClass"] = calculate_player_armor_class_from_state(next_data)

    return next_data
