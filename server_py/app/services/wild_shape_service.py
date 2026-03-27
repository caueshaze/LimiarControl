"""Wild Shape service — manages transform/revert lifecycle and HP routing.

State lives in session_state.state_json under the key "wildShape":
  {
    "active": bool,
    "formKey": str | null,
    "formCurrentHP": int,
    "savedHumanoidHP": int | null,
    "usesRemaining": int,
    "usesMax": int
  }

classResources in character_sheet.data is initialised here for druids:
  {
    "classResources": {
      "wildShape": { "usesMax": 2, "usesRemaining": 2 }
    }
  }
"""
from __future__ import annotations

from app.services.wild_shape_catalog import WildFormStats, get_form


class WildShapeError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Uses
# ---------------------------------------------------------------------------

def compute_wild_shape_uses_max(druid_level: int) -> int:
    """PHB: 2 uses, recharge on short rest. Archdruid (level 20) → unlimited (capped at 99)."""
    if druid_level >= 20:
        return 99
    return 2


# ---------------------------------------------------------------------------
# Block helpers
# ---------------------------------------------------------------------------

def _safe_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _is_druid(data: dict) -> bool:
    class_value = data.get("class")
    if not isinstance(class_value, str):
        return False
    return class_value.strip().lower() == "druid"


def ensure_wild_shape_block(data: dict) -> dict:
    """Return data with a valid wildShape block, creating it if absent."""
    level = _safe_int(data.get("level"), 1)
    uses_max = compute_wild_shape_uses_max(level)
    wild_shape = data.get("wildShape")
    if not isinstance(wild_shape, dict):
        return {
            **data,
            "wildShape": {
                "active": False,
                "formKey": None,
                "formCurrentHP": 0,
                "savedHumanoidHP": None,
                "usesRemaining": uses_max,
                "usesMax": uses_max,
            },
        }
    # Patch missing keys without overwriting existing values
    defaults: dict = {
        "active": False,
        "formKey": None,
        "formCurrentHP": 0,
        "savedHumanoidHP": None,
        "usesRemaining": uses_max,
        "usesMax": uses_max,
    }
    merged = {**defaults, **wild_shape}
    return {**data, "wildShape": merged}


def get_wild_shape_block(data: dict) -> dict:
    wild_shape = data.get("wildShape")
    return wild_shape if isinstance(wild_shape, dict) else {}


def is_active(data: dict) -> bool:
    return bool(get_wild_shape_block(data).get("active", False))


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def transform(data: dict, form_key: str) -> dict:
    """Consume one Wild Shape use and enter beast form.

    Returns updated session_state.state_json dict.
    Raises WildShapeError for invalid transitions.
    """
    if not _is_druid(data):
        raise WildShapeError("Only druids can use Wild Shape")

    form = get_form(form_key)
    if form is None:
        raise WildShapeError(f"Unknown beast form: {form_key!r}")

    level = _safe_int(data.get("level"), 1)
    if level < form.min_druid_level:
        raise WildShapeError(
            f"{form.display_name} requires druid level {form.min_druid_level} (current: {level})"
        )

    data = ensure_wild_shape_block(data)
    ws = data["wildShape"]

    if ws.get("active"):
        raise WildShapeError("Already in Wild Shape — revert first")

    uses_remaining = _safe_int(ws.get("usesRemaining"), 0)
    if uses_remaining <= 0:
        raise WildShapeError("No Wild Shape uses remaining")

    current_hp = _safe_int(data.get("currentHP"), 0)
    new_wild_shape = {
        **ws,
        "active": True,
        "formKey": form_key,
        "formCurrentHP": form.max_hp,
        "savedHumanoidHP": current_hp,
        "usesRemaining": uses_remaining - 1,
    }
    return {**data, "wildShape": new_wild_shape}


# ---------------------------------------------------------------------------
# Revert
# ---------------------------------------------------------------------------

def revert(data: dict) -> dict:
    """Leave beast form and restore humanoid HP.

    Raises WildShapeError if not in Wild Shape.
    """
    data = ensure_wild_shape_block(data)
    ws = data["wildShape"]

    if not ws.get("active"):
        raise WildShapeError("Not currently in Wild Shape")

    saved_hp = _safe_int(ws.get("savedHumanoidHP"), 0)
    max_hp = _safe_int(data.get("maxHP"), 0)
    restored_hp = min(saved_hp, max_hp)

    new_wild_shape = {
        **ws,
        "active": False,
        "formKey": None,
        "formCurrentHP": 0,
        "savedHumanoidHP": None,
    }
    return {**data, "wildShape": new_wild_shape, "currentHP": restored_hp}


def force_revert(data: dict) -> dict:
    """Revert regardless of current state (used by rest system). No-op if not active."""
    ws = get_wild_shape_block(data)
    if not ws.get("active"):
        return data
    return revert(data)


# ---------------------------------------------------------------------------
# Damage routing
# ---------------------------------------------------------------------------

def apply_damage_to_form(data: dict, amount: int) -> tuple[dict, bool]:
    """Route damage through Wild Shape HP pool.

    Returns (updated_data, reverted, overflow).
    - If form HP absorbs all damage: reverted=False, overflow=0.
    - If form HP is depleted: auto-revert, overflow > 0 is the excess damage
      that must be applied to the humanoid HP by the caller (PHB 5e rule).
    """
    if amount <= 0:
        return data, False, 0

    data = ensure_wild_shape_block(data)
    ws = data["wildShape"]

    if not ws.get("active"):
        # Not in form — caller should apply to humanoid HP normally
        return data, False, 0

    form_hp = _safe_int(ws.get("formCurrentHP"), 0)
    new_form_hp = form_hp - amount

    if new_form_hp > 0:
        new_ws = {**ws, "formCurrentHP": new_form_hp}
        return {**data, "wildShape": new_ws}, False, 0
    else:
        # Form HP depleted — revert; return overflow for the caller to apply
        overflow = abs(new_form_hp)  # excess damage beyond form HP
        return revert(data), True, overflow


def apply_healing_to_form(data: dict, amount: int, form: WildFormStats) -> dict:
    """Heal the beast form's HP up to the form's max_hp."""
    if amount <= 0:
        return data

    data = ensure_wild_shape_block(data)
    ws = data["wildShape"]

    if not ws.get("active"):
        return data

    form_hp = _safe_int(ws.get("formCurrentHP"), 0)
    new_form_hp = min(form_hp + amount, form.max_hp)
    new_ws = {**ws, "formCurrentHP": new_form_hp}
    return {**data, "wildShape": new_ws}


# ---------------------------------------------------------------------------
# Recharge (rest integration)
# ---------------------------------------------------------------------------

def recharge_wild_shape(data: dict) -> dict:
    """Restore all Wild Shape uses. Called on short and long rest."""
    data = ensure_wild_shape_block(data)
    ws = data["wildShape"]
    uses_max = _safe_int(ws.get("usesMax"), compute_wild_shape_uses_max(_safe_int(data.get("level"), 1)))
    new_ws = {**ws, "usesRemaining": uses_max}
    return {**data, "wildShape": new_ws}


# ---------------------------------------------------------------------------
# classResources initialiser (called from class_progression on level up)
# ---------------------------------------------------------------------------

def init_class_resources_for_druid(data: dict, level: int) -> dict:
    """Ensure classResources.wildShape is present and up-to-date for druids."""
    uses_max = compute_wild_shape_uses_max(level)
    class_resources = data.get("classResources")
    if not isinstance(class_resources, dict):
        class_resources = {}

    existing = class_resources.get("wildShape")
    if isinstance(existing, dict):
        # Update usesMax; preserve usesRemaining (don't zero mid-session)
        existing_remaining = _safe_int(existing.get("usesRemaining"), uses_max)
        new_ws = {"usesMax": uses_max, "usesRemaining": min(existing_remaining, uses_max)}
    else:
        new_ws = {"usesMax": uses_max, "usesRemaining": uses_max}

    return {**data, "classResources": {**class_resources, "wildShape": new_ws}}
