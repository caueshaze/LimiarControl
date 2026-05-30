from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .condition_effects_predicates import (
    _get_save_declarative_context,
    combine_advantage_modes,
    has_condition,
)

_AUTO_FAIL_SAVE_CONDITIONS = frozenset({"paralyzed", "stunned", "unconscious"})
_AUTO_FAIL_SAVE_ABILITIES = frozenset({"strength", "dexterity"})


@dataclass
class SaveModifierContext:
    auto_fail: bool = False
    auto_fail_source: str = ""
    advantage_sources: list[str] = field(default_factory=list)
    disadvantage_sources: list[str] = field(default_factory=list)
    advantage_source_details: list[dict] = field(default_factory=list)
    disadvantage_source_details: list[dict] = field(default_factory=list)
    result: Literal["advantage", "normal", "disadvantage"] = "normal"


def modify_saving_throw(
    actor: dict,
    ability: str,
    manual_mode: Literal["advantage", "normal", "disadvantage"] = "normal",
    *,
    source_participant: dict | None = None,
    source_kind: Literal[
        "participant",
        "passive_condition",
        "manual_gm",
        "environment",
        "spell_effect",
        "preview",
    ],
) -> SaveModifierContext:
    if source_kind == "participant" and source_participant is None:
        raise ValueError("source_kind='participant' requires source_participant")
    if source_kind != "participant" and source_participant is not None:
        raise ValueError("source_participant is only valid with source_kind='participant'")

    normalized = ability.lower()
    if normalized in _AUTO_FAIL_SAVE_ABILITIES:
        for cond in _AUTO_FAIL_SAVE_CONDITIONS:
            if has_condition(actor, cond):
                return SaveModifierContext(auto_fail=True, auto_fail_source=f"actor_{cond}")

    dis: list[str] = []
    if normalized == "dexterity" and has_condition(actor, "restrained"):
        dis.append("actor_restrained")

    # Declarative active effects
    auto_mode, decl_adv_strs, decl_dis_strs, decl_details = _get_save_declarative_context(
        actor, normalized, source_participant=source_participant
    )

    # Merge hardcoded + declarative automatic sources
    automatic_mode = combine_advantage_modes(
        "disadvantage" if dis else "normal",
        auto_mode,
    )

    # Merge with manual mode
    result = combine_advantage_modes(automatic_mode, manual_mode)

    return SaveModifierContext(
        advantage_sources=decl_adv_strs,
        disadvantage_sources=[*dis, *decl_dis_strs],
        advantage_source_details=[d for d in decl_details if d.get("modifier_type") == "advantage"],
        disadvantage_source_details=[d for d in decl_details if d.get("modifier_type") == "disadvantage"],
        result=result,
    )
