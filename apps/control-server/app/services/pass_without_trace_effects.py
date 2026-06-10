from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4


PASS_WITHOUT_TRACE_RADIUS_METERS = 9.0
PASS_WITHOUT_TRACE_BONUS_VALUE = 10
PASS_WITHOUT_TRACE_SKILL = "stealth"
PASS_WITHOUT_TRACE_ABILITY = "dexterity"
PASS_WITHOUT_TRACE_BONUS_APPLIES_TO = "dexterity_stealth_checks"
PASS_WITHOUT_TRACE_MAX_DURATION_MINUTES = 60

_INACTIVE_STATUSES = {"dead", "defeated", "removed", "stable"}


def build_pass_without_trace_metadata(
    *,
    spell_name: str,
    concentration_group: str,
    origin_caster_participant_id: str | None,
    origin_caster_ref_id: str | None,
    selected_participant_ids: list[str],
    selected_ref_ids: list[str],
    context_origin: str,
    caster_user_id: str | None = None,
    target_user_id: str | None = None,
    owner_participant_id: str | None = None,
    created_by_participant_id: str | None = None,
    concentration: bool = True,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "source_spell_key": "pass_without_trace",
        "source_spell_name": spell_name,
        "effect_role": "skill_check_bonus",
        "concentration": concentration,
        "concentration_group": concentration_group,
        "origin_caster_participant_id": origin_caster_participant_id,
        "origin_caster_ref_id": origin_caster_ref_id,
        "skill": PASS_WITHOUT_TRACE_SKILL,
        "ability": PASS_WITHOUT_TRACE_ABILITY,
        "bonus_value": PASS_WITHOUT_TRACE_BONUS_VALUE,
        "bonus_applies_to": PASS_WITHOUT_TRACE_BONUS_APPLIES_TO,
        "duration_type": "concentration",
        "max_duration_minutes": PASS_WITHOUT_TRACE_MAX_DURATION_MINUTES,
        "radius_m": PASS_WITHOUT_TRACE_RADIUS_METERS,
        "selected_participant_ids": list(selected_participant_ids),
        "selected_ref_ids": list(selected_ref_ids),
        "suppresses_tracks": True,
        "prevents_nonmagical_tracking": True,
        "tracking_exception": "magical_tracking",
        "context_origin": context_origin,
    }
    if isinstance(caster_user_id, str) and caster_user_id:
        metadata["caster_player_user_id"] = caster_user_id
    if isinstance(target_user_id, str) and target_user_id:
        metadata["target_player_user_id"] = target_user_id
    if isinstance(owner_participant_id, str) and owner_participant_id:
        metadata["owner_participant_id"] = owner_participant_id
    if isinstance(created_by_participant_id, str) and created_by_participant_id:
        metadata["created_by_participant_id"] = created_by_participant_id
    return metadata


def build_pass_without_trace_effect(
    *,
    source_participant_id: str | None,
    spell_name: str,
    concentration_group: str,
    origin_caster_participant_id: str | None,
    origin_caster_ref_id: str | None,
    selected_participant_ids: list[str],
    selected_ref_ids: list[str],
    duration_type: str,
    created_at_game_time_seconds: int | None,
    expires_at_game_time_seconds: int | None,
    context_origin: str,
    caster_user_id: str | None = None,
    target_user_id: str | None = None,
    owner_participant_id: str | None = None,
    created_by_participant_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "source_participant_id": source_participant_id,
        "kind": "spell_effect",
        "condition_type": None,
        "numeric_value": None,
        "duration_type": duration_type,
        "remaining_rounds": None,
        "expires_on": None,
        "expires_at_participant_id": None,
        "created_at_game_time_seconds": created_at_game_time_seconds,
        "expires_at_game_time_seconds": expires_at_game_time_seconds,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": build_pass_without_trace_metadata(
            spell_name=spell_name,
            concentration_group=concentration_group,
            origin_caster_participant_id=origin_caster_participant_id,
            origin_caster_ref_id=origin_caster_ref_id,
            selected_participant_ids=selected_participant_ids,
            selected_ref_ids=selected_ref_ids,
            context_origin=context_origin,
            caster_user_id=caster_user_id,
            target_user_id=target_user_id,
            owner_participant_id=owner_participant_id,
            created_by_participant_id=created_by_participant_id,
        ),
        "display_label": spell_name,
    }


def resolve_skill_check_bonus_sources_from_effects(
    effects: list[dict] | None,
    *,
    roll_type: str,
    ability: str | None,
    skill: str | None,
    participant_status: str | None,
    participant_ref_id: str | None = None,
    concentration_group_is_active: Callable[[str], bool] | None = None,
    distance_lookup: Callable[[str], float | None] | None = None,
) -> list[dict[str, Any]]:
    if roll_type != "skill":
        return []
    normalized_ability = str(ability or "").strip().lower()
    normalized_skill = str(skill or "").strip().lower()
    if normalized_ability != PASS_WITHOUT_TRACE_ABILITY or normalized_skill != PASS_WITHOUT_TRACE_SKILL:
        return []
    if str(participant_status or "").strip().lower() in _INACTIVE_STATUSES:
        return []

    best_by_key: dict[str, dict[str, Any]] = {}
    for effect in effects or []:
        if not isinstance(effect, dict) or effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("effect_role") or "").strip().lower() != "skill_check_bonus":
            continue
        if str(metadata.get("source_spell_key") or "").strip().lower() != "pass_without_trace":
            continue
        if str(metadata.get("skill") or "").strip().lower() != PASS_WITHOUT_TRACE_SKILL:
            continue
        if str(metadata.get("ability") or "").strip().lower() != PASS_WITHOUT_TRACE_ABILITY:
            continue
        if str(metadata.get("bonus_applies_to") or "").strip().lower() != PASS_WITHOUT_TRACE_BONUS_APPLIES_TO:
            continue

        concentration_group = metadata.get("concentration_group")
        if not isinstance(concentration_group, str) or not concentration_group.strip():
            continue
        if callable(concentration_group_is_active) and not concentration_group_is_active(concentration_group):
            continue

        origin_ref_id = metadata.get("origin_caster_ref_id")
        if (
            isinstance(origin_ref_id, str)
            and origin_ref_id
            and isinstance(participant_ref_id, str)
            and participant_ref_id
            and origin_ref_id != participant_ref_id
            and callable(distance_lookup)
        ):
            distance = distance_lookup(origin_ref_id)
            if not isinstance(distance, (int, float)) or float(distance) > PASS_WITHOUT_TRACE_RADIUS_METERS:
                continue

        bonus_value = metadata.get("bonus_value")
        if not isinstance(bonus_value, int) or bonus_value == 0:
            continue

        dedup_key = (
            f"{str(metadata.get('source_spell_key') or '').strip().lower()}|"
            f"{PASS_WITHOUT_TRACE_ABILITY}|{PASS_WITHOUT_TRACE_SKILL}"
        )
        current = best_by_key.get(dedup_key)
        if current is None or bonus_value > int(current.get("signed_total") or 0):
            source_label = metadata.get("source_spell_name") or effect.get("display_label") or "Spell effect"
            sign_label = "+" if bonus_value >= 0 else "-"
            best_by_key[dedup_key] = {
                "source_label": source_label,
                "modifier_type": "skill_flat_bonus",
                "roll_type": "skill",
                "ability": PASS_WITHOUT_TRACE_ABILITY,
                "skill": PASS_WITHOUT_TRACE_SKILL,
                "signed_total": bonus_value,
                "display_label": f"{source_label}: {sign_label}{abs(bonus_value)}",
                "effect_id": effect.get("id") if isinstance(effect.get("id"), str) else None,
                "concentration_group": concentration_group,
                "applied": True,
                "skip_reason": None,
            }

    return list(best_by_key.values())
