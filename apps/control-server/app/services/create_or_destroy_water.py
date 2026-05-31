from __future__ import annotations

from typing import Any

CREATE_OR_DESTROY_WATER_KEY = "create_or_destroy_water"

VALID_MODES = {"create", "destroy"}
VALID_TARGET_KINDS = {"container", "area"}

# variantKey (OOC) -> mode
VARIANT_MODE_MAP = {
    "create_water": "create",
    "destroy_water": "destroy",
}


def resolve_water_amount(slot_level: int | None) -> tuple[int, int]:
    """Return (gallons, liters) created or destroyed at the given slot level.

    Base 10 gal / 38 L at 1st level, +10 gal / +38 L per slot above 1st.
    """
    n = max(1, int(slot_level or 1))
    extra = n - 1
    return 10 + 10 * extra, 38 + 38 * extra


def resolve_cube_side_meters(slot_level: int | None) -> float:
    """Return the rain/fog cube side in meters: 9 m base, +1.5 m per slot above 1st."""
    n = max(1, int(slot_level or 1))
    return 9.0 + 1.5 * (n - 1)


def normalize_water_payload(payload: Any, *, has_anchor: bool = False) -> dict[str, str]:
    """Validate and normalize a Create or Destroy Water effect payload.

    Raises ValueError on missing/invalid fields. `has_anchor` indicates whether a
    map anchor/origin cell was supplied on the request (area mode needs a point).
    """
    if payload is not None and hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    if not isinstance(payload, dict):
        raise ValueError("Create or Destroy Water requires an effect payload.")

    mode = str(payload.get("mode") or "").strip().lower()
    target_kind = str(payload.get("target_kind") or payload.get("targetKind") or "").strip().lower()
    if mode not in VALID_MODES:
        raise ValueError("Effect payload 'mode' must be 'create' or 'destroy'.")
    if target_kind not in VALID_TARGET_KINDS:
        raise ValueError("Effect payload 'target_kind' must be 'container' or 'area'.")

    point = payload.get("point")
    description = str(payload.get("description") or "").strip()
    container_description = str(payload.get("container_description") or payload.get("containerDescription") or "").strip()

    if target_kind == "area" and not (has_anchor or point):
        raise ValueError("Area mode requires a target point.")
    if target_kind == "container" and not (description or container_description):
        raise ValueError("Container mode requires a description of the container.")

    return {"mode": mode, "target_kind": target_kind}


def _coordinate_keys(cells: Any) -> set[tuple[int, int]]:
    keys: set[tuple[int, int]] = set()
    for cell in cells or []:
        if isinstance(cell, dict):
            x, y = cell.get("x"), cell.get("y")
        else:
            x, y = getattr(cell, "x", None), getattr(cell, "y", None)
        if isinstance(x, int) and isinstance(y, int):
            keys.add((x, y))
    return keys


def select_obscurement_effects_in_cells(state, cells: Any) -> list[dict]:
    """Return active obscurement (fog) area-effects overlapping the given cube cells."""
    region = _coordinate_keys(cells)
    if not region:
        return []
    matches: list[dict] = []
    for effect in getattr(state, "active_area_effects", None) or []:
        if not isinstance(effect, dict):
            continue
        if str(effect.get("effect_kind") or "").strip().lower() != "obscurement":
            continue
        if _coordinate_keys(effect.get("affected_cells")) & region:
            matches.append(effect)
    return matches
