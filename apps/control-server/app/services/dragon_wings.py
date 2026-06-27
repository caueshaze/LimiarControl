from __future__ import annotations

from typing import Any

from app.services.sorcerer_progression import is_draconic_bloodline_sorcerer


DRAGON_WINGS_MIN_LEVEL = 14


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def is_dragon_wings_eligible(data: dict | None) -> bool:
    """Dragon Wings (Draconic Bloodline 14+): only a draconic sorcerer of at
    least level 14 can manifest dragon wings."""
    payload = data if isinstance(data, dict) else {}
    if not is_draconic_bloodline_sorcerer(payload):
        return False
    return _safe_int(payload.get("level"), 1) >= DRAGON_WINGS_MIN_LEVEL


def is_dragon_wings_active(data: dict | None) -> bool:
    payload = data if isinstance(data, dict) else {}
    if not is_dragon_wings_eligible(payload):
        return False
    wings = payload.get("dragonWings")
    return isinstance(wings, dict) and bool(wings.get("active"))


def _walking_speed_meters(data: dict) -> int:
    for key in ("speedMeters", "speed_meters"):
        value = data.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return 0


def resolve_dragon_wings_state(data: dict | None) -> dict[str, Any]:
    payload = data if isinstance(data, dict) else {}
    eligible = is_dragon_wings_eligible(payload)
    active = is_dragon_wings_active(payload)
    return {
        "eligible": eligible,
        "active": active,
        "flySpeedMeters": _walking_speed_meters(payload) if active else 0,
    }


def apply_dragon_wings_canonical_state(data: dict | None) -> dict:
    """Normalize the Dragon Wings flag and derived flight fields.

    - Ineligible characters never carry an active flag or flight fields.
    - While active, ``flying`` is True and ``flySpeedMeters`` equals the
      walking speed (RAW: flying speed equal to current speed).
    """
    next_data = dict(data) if isinstance(data, dict) else {}

    if not is_dragon_wings_eligible(next_data):
        next_data.pop("dragonWings", None)
        next_data.pop("flying", None)
        next_data.pop("flySpeedMeters", None)
        return next_data

    wings_raw = next_data.get("dragonWings")
    active = isinstance(wings_raw, dict) and bool(wings_raw.get("active"))
    next_data["dragonWings"] = {"active": active}
    if active:
        next_data["flying"] = True
        next_data["flySpeedMeters"] = _walking_speed_meters(next_data)
    else:
        next_data.pop("flying", None)
        next_data.pop("flySpeedMeters", None)
    return next_data
