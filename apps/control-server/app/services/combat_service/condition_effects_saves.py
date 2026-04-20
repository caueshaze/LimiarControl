from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .condition_effects_predicates import has_condition

_AUTO_FAIL_SAVE_CONDITIONS = frozenset({"paralyzed", "stunned", "unconscious"})
_AUTO_FAIL_SAVE_ABILITIES = frozenset({"strength", "dexterity"})


@dataclass
class SaveModifierContext:
    auto_fail: bool = False
    auto_fail_source: str = ""
    advantage_sources: list[str] = field(default_factory=list)
    disadvantage_sources: list[str] = field(default_factory=list)
    result: Literal["advantage", "normal", "disadvantage"] = "normal"


def modify_saving_throw(actor: dict, ability: str) -> SaveModifierContext:
    normalized = ability.lower()
    if normalized in _AUTO_FAIL_SAVE_ABILITIES:
        for cond in _AUTO_FAIL_SAVE_CONDITIONS:
            if has_condition(actor, cond):
                return SaveModifierContext(auto_fail=True, auto_fail_source=f"actor_{cond}")
    dis: list[str] = []
    if normalized == "dexterity" and has_condition(actor, "restrained"):
        dis.append("actor_restrained")
    result: Literal["advantage", "normal", "disadvantage"] = "disadvantage" if dis else "normal"
    return SaveModifierContext(disadvantage_sources=dis, result=result)
