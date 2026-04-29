from __future__ import annotations

from typing import Any, Callable

from ..exceptions import CombatServiceError


def normalize_area_guardrail_reason(error: CombatServiceError) -> str:
    detail = error.detail if isinstance(error.detail, str) else str(error.detail or error)
    text = detail.strip()
    return text or "Target was excluded by a mechanical rule."


def evaluate_area_target_guardrail(
    *,
    db,
    session_id: str,
    attacker: dict[str, Any],
    target_participant: dict[str, Any],
    spell_canonical_key: str,
    assert_hostile_action_allowed: Callable[..., None],
    validate_spell_automation_target: Callable[..., None],
) -> str | None:
    try:
        assert_hostile_action_allowed(
            attacker,
            target_participant,
            action_label="a hostile spell",
        )
        validate_spell_automation_target(
            db,
            session_id,
            spell_canonical_key=spell_canonical_key,
            target_participant=target_participant,
        )
    except CombatServiceError as exc:
        return normalize_area_guardrail_reason(exc)
    return None


def build_area_guardrail_outcome(
    *,
    target_participant: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "target_ref_id": target_participant["ref_id"],
        "target_display_name": target_participant.get("display_name") or target_participant["ref_id"],
        "target_kind": target_participant["kind"],
        "excluded_by_guardrail": True,
        "guardrail_reason": reason,
    }
