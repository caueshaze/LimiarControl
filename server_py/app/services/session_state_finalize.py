from __future__ import annotations

import unicodedata

from app.services.session_rest import ensure_rest_state


_PLAYER_SHIELD_BONUS = 2


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


def calculate_player_armor_class_from_state(data: dict | None) -> int:
    payload = _as_dict(data)
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

    if armor_type == "heavy":
        base_total = base_ac
    elif armor_type == "medium":
        dex_contribution = dex_mod if dex_cap is None else min(dex_mod, dex_cap)
        base_total = base_ac + (dex_contribution if allows_dex else 0)
    elif armor_type == "light":
        base_total = base_ac + (dex_mod if allows_dex else 0)
    else:
        base_total = 10 + dex_mod
        player_class = _normalize_lookup(payload.get("class"))
        if player_class == "barbarian":
            base_total = max(base_total, 10 + dex_mod + con_mod)
        if player_class == "monk" and not isinstance(payload.get("equippedShield"), dict):
            base_total = max(base_total, 10 + dex_mod + wis_mod)

    shield = _as_dict(payload.get("equippedShield"))
    shield_bonus = _safe_int(shield.get("bonus"), 0) if shield else 0
    if shield and shield_bonus == 0:
        shield_bonus = _PLAYER_SHIELD_BONUS

    misc_bonus = _safe_int(payload.get("miscACBonus"), 0)
    fighting_style = _normalize_lookup(payload.get("fightingStyle"))
    defense_bonus = 1 if fighting_style == "defense" and armor_type in {"light", "medium", "heavy"} else 0

    return max(0, base_total + shield_bonus + misc_bonus + defense_bonus)


def finalize_session_state_data(data: dict | None) -> dict:
    next_data = ensure_rest_state(data)

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
