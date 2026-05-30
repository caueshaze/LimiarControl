"""Sanctuary spell guard: pre-attack intercept and break-on-action helpers."""

from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified


def find_sanctuary_effect_on_participant(participant: dict) -> dict | None:
    """Return the active sanctuary spell_effect on participant, or None."""
    for e in (participant.get("active_effects") or []):
        if (
            e.get("kind") == "spell_effect"
            and (e.get("metadata") or {}).get("sanctuary") is True
        ):
            return e
    return None


def resolve_sanctuary_guard(
    *,
    db,
    session_id: str,
    attacker_participant: dict,
    target_participant: dict,
) -> dict | None:
    """Check if the target is protected by Sanctuary and the attacker fails their Wisdom save.

    Returns a block dict if the attacker fails (attack must not proceed against this target),
    or None if the attack may proceed normally.
    """
    from app.services.combat_service.condition_effects_saves import modify_saving_throw
    from app.services.roll_resolution import resolve_saving_throw
    from app.services.combat_service.core import CombatCoreMixin

    effect = find_sanctuary_effect_on_participant(target_participant)
    if effect is None:
        return None

    metadata = effect.get("metadata") or {}
    save_dc = int(metadata.get("guard_save_dc") or 0)
    if save_dc <= 0:
        return None

    attacker_stats = CombatCoreMixin._build_roll_actor_stats_for_save(
        db,
        session_id,
        attacker_participant["ref_id"],
        attacker_participant["kind"],
        attacker_participant.get("display_name", ""),
    )

    save_mod_ctx = modify_saving_throw(
        attacker_participant, "wisdom", source_kind="spell_effect"
    )
    save_result = resolve_saving_throw(
        attacker_stats,
        ability="wisdom",
        dc=save_dc,
        advantage_mode=save_mod_ctx.result,
    )
    if save_mod_ctx.auto_fail:
        save_result.success = False

    if save_result.success:
        return None

    return {
        "blocked": True,
        "blocked_by": "sanctuary",
        "retarget_required": True,
        "save_roll": save_result.total,
        "save_rolls": save_result.rolls,
        "guard_save_dc": save_dc,
        "attacker_display_name": attacker_participant.get("display_name", ""),
        "target_display_name": target_participant.get("display_name", ""),
    }


def break_sanctuary_if_active(participant: dict, state) -> bool:
    """Remove sanctuary from participant if they have it. Returns True if removed."""
    effects = participant.get("active_effects") or []
    remaining = [
        e for e in effects
        if not (
            e.get("kind") == "spell_effect"
            and (e.get("metadata") or {}).get("sanctuary") is True
        )
    ]
    if len(remaining) < len(effects):
        participant["active_effects"] = remaining
        flag_modified(state, "participants")
        return True
    return False
