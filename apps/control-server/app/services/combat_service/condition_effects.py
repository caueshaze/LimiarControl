"""condition_effects.py — Centralized condition-state resolver for Phase 12+.

Barrel module kept for backward compatibility after code-splitting.
"""

from .condition_effects_attacks import (
    AttackAdvantageContext,
    get_attack_advantage_penalty,
    get_attack_auto_crit,
    get_effective_reach,
    resolve_attack_advantage,
    resolve_spell_attack_kind,
)
from .condition_effects_predicates import (
    can_see,
    has_condition,
    is_action_blocked,
    is_heavily_obscured,
    is_invisible,
    is_lightly_obscured,
    is_movement_blocked,
    is_movement_halved,
)
from .condition_effects_saves import SaveModifierContext, modify_saving_throw
