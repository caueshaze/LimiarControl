"""Pure roll resolution service — no DB access, no state mutation.

Receives pre-extracted actor stats and returns a standardised RollResult.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.campaign_entity_shared import (
    AbilityName,
    SkillName,
    ability_modifier,
    resolve_initiative_bonus,
    resolve_saving_throw_bonus,
    resolve_skill_bonus,
)
from app.schemas.roll import AdvantageMode, RollActorStats, RollResult, RollSource, RollType


# ---------------------------------------------------------------------------
# D20 helpers (reusable by combat service)
# ---------------------------------------------------------------------------

def roll_d20_pair() -> tuple[int, int]:
    """Roll two d20s and return both raw values."""
    return random.randint(1, 20), random.randint(1, 20)


def select_d20(d20_a: int, d20_b: int, mode: AdvantageMode) -> int:
    """Pick the appropriate d20 based on advantage mode."""
    if mode == "advantage":
        return max(d20_a, d20_b)
    if mode == "disadvantage":
        return min(d20_a, d20_b)
    return d20_a


def _resolve_d20s(
    advantage_mode: AdvantageMode,
    roll_source: RollSource = "system",
    manual_roll: int | None = None,
    manual_rolls: list[int] | None = None,
) -> tuple[int, int, int]:
    """Return (d20_a, d20_b, selected) from system RNG or manual input."""
    if roll_source == "manual":
        if manual_rolls and len(manual_rolls) >= 2:
            d20_a, d20_b = manual_rolls[0], manual_rolls[1]
        elif manual_roll is not None:
            d20_a = manual_roll
            d20_b = manual_roll  # duplicate for normal mode
        else:
            d20_a, d20_b = roll_d20_pair()  # fallback to system
    else:
        d20_a, d20_b = roll_d20_pair()

    # Normal rolls should behave like a single d20 roll in the UI/result payload.
    if advantage_mode == "normal":
        d20_b = d20_a

    selected = select_d20(d20_a, d20_b, advantage_mode)
    return d20_a, d20_b, selected


# ---------------------------------------------------------------------------
# Internal result builder
# ---------------------------------------------------------------------------

def _build_result(
    *,
    roll_type: RollType,
    stats: RollActorStats,
    rolls: tuple[int, int],
    selected_roll: int,
    advantage_mode: AdvantageMode,
    modifier: int,
    override_used: bool,
    roll_source: RollSource = "system",
    ability: AbilityName | None = None,
    skill: SkillName | None = None,
    dc: int | None = None,
    target_ac: int | None = None,
    success: bool | None = None,
) -> RollResult:
    total = selected_roll + modifier
    sign = "+" if modifier >= 0 else "-"
    formula = f"1d20 {sign} {abs(modifier)}"

    # Determine success against DC
    if success is None and dc is not None:
        success = total >= dc

    return RollResult(
        event_id=str(uuid4()),
        roll_type=roll_type,
        actor_kind=stats.actor_kind,
        actor_ref_id=stats.actor_ref_id,
        actor_display_name=stats.display_name,
        rolls=list(rolls),
        selected_roll=selected_roll,
        advantage_mode=advantage_mode,
        modifier_used=modifier,
        override_used=override_used,
        formula=formula,
        total=total,
        ability=ability,
        skill=skill,
        dc=dc,
        target_ac=target_ac,
        success=success,
        roll_source=roll_source,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Public resolution functions
# ---------------------------------------------------------------------------

def resolve_ability_check(
    stats: RollActorStats,
    ability: AbilityName,
    advantage_mode: AdvantageMode = "normal",
    bonus_override: int | None = None,
    dc: int | None = None,
    roll_source: RollSource = "system",
    manual_roll: int | None = None,
    manual_rolls: list[int] | None = None,
) -> RollResult:
    override_used = bonus_override is not None
    modifier = bonus_override if override_used else ability_modifier(stats.abilities.get(ability, 10))

    d20_a, d20_b, selected = _resolve_d20s(advantage_mode, roll_source, manual_roll, manual_rolls)

    return _build_result(
        roll_type="ability",
        stats=stats,
        rolls=(d20_a, d20_b),
        selected_roll=selected,
        advantage_mode=advantage_mode,
        modifier=modifier,
        override_used=override_used,
        roll_source=roll_source,
        ability=ability,
        dc=dc,
    )


def resolve_saving_throw(
    stats: RollActorStats,
    ability: AbilityName,
    advantage_mode: AdvantageMode = "normal",
    bonus_override: int | None = None,
    dc: int | None = None,
    roll_source: RollSource = "system",
    manual_roll: int | None = None,
    manual_rolls: list[int] | None = None,
) -> RollResult:
    override_used = bonus_override is not None
    modifier = (
        bonus_override
        if override_used
        else resolve_saving_throw_bonus(stats.abilities, stats.saving_throws, ability)
    )

    d20_a, d20_b, selected = _resolve_d20s(advantage_mode, roll_source, manual_roll, manual_rolls)

    return _build_result(
        roll_type="save",
        stats=stats,
        rolls=(d20_a, d20_b),
        selected_roll=selected,
        advantage_mode=advantage_mode,
        modifier=modifier,
        override_used=override_used,
        roll_source=roll_source,
        ability=ability,
        dc=dc,
    )


def resolve_skill_check(
    stats: RollActorStats,
    skill: SkillName,
    advantage_mode: AdvantageMode = "normal",
    bonus_override: int | None = None,
    dc: int | None = None,
    roll_source: RollSource = "system",
    manual_roll: int | None = None,
    manual_rolls: list[int] | None = None,
) -> RollResult:
    override_used = bonus_override is not None
    modifier = (
        bonus_override
        if override_used
        else resolve_skill_bonus(stats.abilities, stats.skills, skill)
    )

    d20_a, d20_b, selected = _resolve_d20s(advantage_mode, roll_source, manual_roll, manual_rolls)

    return _build_result(
        roll_type="skill",
        stats=stats,
        rolls=(d20_a, d20_b),
        selected_roll=selected,
        advantage_mode=advantage_mode,
        modifier=modifier,
        override_used=override_used,
        roll_source=roll_source,
        skill=skill,
        dc=dc,
    )


def resolve_initiative(
    stats: RollActorStats,
    advantage_mode: AdvantageMode = "normal",
    bonus_override: int | None = None,
    roll_source: RollSource = "system",
    manual_roll: int | None = None,
    manual_rolls: list[int] | None = None,
) -> RollResult:
    override_used = bonus_override is not None
    modifier = (
        bonus_override
        if override_used
        else resolve_initiative_bonus(stats.abilities, stats.initiative_bonus)
    )

    d20_a, d20_b, selected = _resolve_d20s(advantage_mode, roll_source, manual_roll, manual_rolls)

    return _build_result(
        roll_type="initiative",
        stats=stats,
        rolls=(d20_a, d20_b),
        selected_roll=selected,
        advantage_mode=advantage_mode,
        modifier=modifier,
        override_used=override_used,
        roll_source=roll_source,
    )


def resolve_attack_base(
    stats: RollActorStats,
    advantage_mode: AdvantageMode = "normal",
    bonus_override: int | None = None,
    target_ac: int | None = None,
    roll_source: RollSource = "system",
    manual_roll: int | None = None,
    manual_rolls: list[int] | None = None,
) -> RollResult:
    override_used = bonus_override is not None
    modifier = bonus_override if override_used else 0

    d20_a, d20_b, selected = _resolve_d20s(advantage_mode, roll_source, manual_roll, manual_rolls)

    # Natural 20 / natural 1 rules
    success: bool | None = None
    if target_ac is not None:
        if selected == 20:
            success = True
        elif selected == 1:
            success = False
        else:
            success = (selected + modifier) >= target_ac

    return _build_result(
        roll_type="attack",
        stats=stats,
        rolls=(d20_a, d20_b),
        selected_roll=selected,
        advantage_mode=advantage_mode,
        modifier=modifier,
        override_used=override_used,
        roll_source=roll_source,
        target_ac=target_ac,
        success=success,
    )
