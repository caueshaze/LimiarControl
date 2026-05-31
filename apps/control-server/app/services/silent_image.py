from __future__ import annotations

from typing import Any

SILENT_IMAGE_KEY = "silent_image"


def _is_illusion_effect(effect: dict[str, Any] | None) -> bool:
    if not isinstance(effect, dict):
        return False
    return str(effect.get("effect_kind") or "").strip().lower() == "illusion"


def find_silent_image_effect(state, illusion_id: str | None) -> dict | None:
    """Return the illusion area effect with the given id, if present and active."""
    if not illusion_id:
        return None
    for effect in getattr(state, "active_area_effects", None) or []:
        if _is_illusion_effect(effect) and effect.get("id") == illusion_id:
            return effect
    return None


def is_illusion_active(state, illusion_id: str | None) -> bool:
    return find_silent_image_effect(state, illusion_id) is not None


def mark_illusion_discerned(state, illusion_id: str | None, ref_id: str | None) -> bool:
    """Mark a creature (by ref_id) as having discerned the illusion.

    Per-creature and idempotent: returns True if the ref_id is now recorded,
    False if the illusion is missing or ref_id is empty.
    """
    effect = find_silent_image_effect(state, illusion_id)
    if effect is None or not ref_id:
        return False
    discerned = effect.get("discerned_by_ref_ids")
    if not isinstance(discerned, list):
        discerned = []
    if ref_id not in discerned:
        discerned.append(ref_id)
    effect["discerned_by_ref_ids"] = discerned
    return True


def update_illusion(
    state,
    illusion_id: str | None,
    *,
    point: dict | None = None,
    appearance: dict | None = None,
) -> dict | None:
    """Move and/or re-describe an illusion, preserving id, concentration group,
    and per-creature discernment. Returns the updated effect or None."""
    effect = find_silent_image_effect(state, illusion_id)
    if effect is None:
        return None
    if isinstance(point, dict) and "x" in point and "y" in point:
        cell = {"x": int(point["x"]), "y": int(point["y"])}
        effect["origin_point"] = cell
        effect["anchor_cell"] = cell
        effect["affected_cells"] = [cell]
    if isinstance(appearance, dict):
        effect["appearance"] = appearance
    return effect
