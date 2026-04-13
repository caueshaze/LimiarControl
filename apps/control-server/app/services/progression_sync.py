from __future__ import annotations


def merge_class_resources_for_progression_sync(
    sheet_class_resources: object,
    session_class_resources: object,
) -> dict | None:
    if not isinstance(sheet_class_resources, dict):
        return None

    session_resources = session_class_resources if isinstance(session_class_resources, dict) else {}
    merged: dict = {}
    for key, raw_sheet_resource in sheet_class_resources.items():
        if not isinstance(raw_sheet_resource, dict):
            continue
        sheet_uses_max = int(raw_sheet_resource.get("usesMax") or 0)
        raw_session_resource = session_resources.get(key)
        session_uses_remaining = (
            int(raw_session_resource.get("usesRemaining") or 0)
            if isinstance(raw_session_resource, dict)
            else sheet_uses_max
        )
        merged[key] = {
            **raw_sheet_resource,
            "usesMax": sheet_uses_max,
            "usesRemaining": max(0, min(session_uses_remaining, sheet_uses_max)),
        }
    return merged or None


def merge_spell_slots_for_progression_sync(
    sheet_spellcasting: object,
    session_spellcasting: object,
) -> dict | None:
    """Rebuild spellcasting block: max values from sheet, used counts from session."""
    if not isinstance(sheet_spellcasting, dict):
        return None

    sheet_slots: dict = sheet_spellcasting.get("slots") or {}
    session_slots: dict = {}
    if isinstance(session_spellcasting, dict):
        session_slots = session_spellcasting.get("slots") or {}

    merged: dict = {}
    all_keys = set(sheet_slots) | set(session_slots)
    for key in all_keys:
        sheet_slot = sheet_slots.get(key)
        session_slot = session_slots.get(key)
        new_max = sheet_slot.get("max", 0) if isinstance(sheet_slot, dict) else 0
        old_used = session_slot.get("used", 0) if isinstance(session_slot, dict) else 0
        if new_max > 0 or sheet_slot is not None:
            merged[key] = {"max": new_max, "used": min(int(old_used), new_max)}

    return {**sheet_spellcasting, "slots": merged}


def merge_progression_session_state(
    current_state: dict | None,
    sheet_data: dict | None,
) -> dict:
    current = current_state if isinstance(current_state, dict) else {}
    sheet = sheet_data if isinstance(sheet_data, dict) else {}

    # Preserve session damage while applying the new HP delta from the sheet.
    new_max_hp = int(sheet.get("maxHP", 0))
    old_session_max_hp = int(current.get("maxHP", new_max_hp))
    hp_gain = max(0, new_max_hp - old_session_max_hp)
    new_current_hp = min(int(current.get("currentHP", 0)) + hp_gain, new_max_hp)

    # Preserve spent hit dice in the current session while applying the new total.
    new_hit_dice_total = int(sheet.get("hitDiceTotal", 1))
    old_session_total = int(current.get("hitDiceTotal", new_hit_dice_total))
    dice_gain = max(0, new_hit_dice_total - old_session_total)
    new_remaining = min(int(current.get("hitDiceRemaining", 0)) + dice_gain, new_hit_dice_total)

    merged_spellcasting = merge_spell_slots_for_progression_sync(
        sheet.get("spellcasting"),
        current.get("spellcasting"),
    )
    merged_class_resources = merge_class_resources_for_progression_sync(
        sheet.get("classResources"),
        current.get("classResources"),
    )

    updated: dict = {
        **current,
        "level": int(sheet.get("level", 1)),
        "experiencePoints": int(sheet.get("experiencePoints", 0)),
        "pendingLevelUp": bool(sheet.get("pendingLevelUp", False)),
        "subclass": sheet.get("subclass"),
        "subclassConfig": dict(sheet.get("subclassConfig") or {}) or None,
        "fightingStyle": sheet.get("fightingStyle"),
        "abilities": dict(sheet.get("abilities") or {}),
        "classFeatures": list(sheet.get("classFeatures") or []),
        "maxHP": new_max_hp,
        "currentHP": new_current_hp,
        "hitDiceTotal": new_hit_dice_total,
        "hitDiceRemaining": new_remaining,
    }
    if merged_spellcasting is not None:
        updated["spellcasting"] = merged_spellcasting
    if merged_class_resources is not None:
        updated["classResources"] = merged_class_resources
    else:
        updated.pop("classResources", None)

    return updated
