"""Test: effective size affects carrying capacity and encumbrance tiers.

Validates that:
- size_carrying_capacity_multiplier returns correct multiplier per size
- get_effective_capacity_multiplier combines size + effect multipliers
- _get_encumbrance_tier_for_participant uses effective_size
- _encumbrance_tier_for_player accepts effective_size
- recompute_participant_encumbrance_tier passes effective_size
"""

import unittest
from unittest.mock import MagicMock

from app.models.combat import CombatPhase
from app.services.combat_service.entity_size import (
    SizeCategory,
    size_carrying_capacity_multiplier,
)
from app.services.combat_service.condition_effects_predicates import (
    _get_encumbrance_tier_for_participant,
    get_effective_capacity_multiplier,
)
from app.services.combat_service.lifecycle_initiative import (
    CombatLifecycleInitiativeMixin,
    _encumbrance_tier_for_player,
)

_LB_TO_KG = 0.45359237


def _kg_to_lb(kg: float) -> float:
    return kg / _LB_TO_KG


def _carry_effect(multiplier: float) -> dict:
    return {
        "id": f"eff-carry-{multiplier}",
        "kind": "spell_effect",
        "metadata": {
            "source_spell_name": "Enhance Ability",
            "declarative_effect_group_id": "enhance_ability|bulls_strength|carrying_capacity_multiplier|2",
            "declarative_effect": {
                "type": "carrying_capacity_multiplier",
                "params": {"multiplier": multiplier},
            },
        },
    }


def _make_db(strength: int = 10, weight_lb: float = 0.0) -> MagicMock:
    db = MagicMock()
    session_state = MagicMock()
    session_state.state_json = {"abilities": {"strength": strength}}
    campaign_session = MagicMock()
    campaign_session.campaign_id = "camp-1"
    member = MagicMock()
    member.id = "member-1"
    db.exec.side_effect = [
        MagicMock(first=MagicMock(return_value=session_state)),
        MagicMock(first=MagicMock(return_value=campaign_session)),
        MagicMock(first=MagicMock(return_value=member)),
        MagicMock(scalar=MagicMock(return_value=weight_lb)),
    ]
    return db


class TestSizeCarryingCapacityMultiplier(unittest.TestCase):

    def test_tiny(self):
        self.assertEqual(size_carrying_capacity_multiplier(SizeCategory.TINY), 0.5)

    def test_small(self):
        self.assertEqual(size_carrying_capacity_multiplier(SizeCategory.SMALL), 1.0)

    def test_medium(self):
        self.assertEqual(size_carrying_capacity_multiplier(SizeCategory.MEDIUM), 1.0)

    def test_large(self):
        self.assertEqual(size_carrying_capacity_multiplier(SizeCategory.LARGE), 2.0)

    def test_huge(self):
        self.assertEqual(size_carrying_capacity_multiplier(SizeCategory.HUGE), 4.0)

    def test_gargantuan(self):
        self.assertEqual(size_carrying_capacity_multiplier(SizeCategory.GARGANTUAN), 8.0)


class TestGetEffectiveCapacityMultiplier(unittest.TestCase):

    def test_medium_no_effects(self):
        p = {"active_effects": [], "base_size": "Medium"}
        self.assertEqual(get_effective_capacity_multiplier(p), 1.0)

    def test_large_no_effects(self):
        p = {"active_effects": [], "base_size": "Large"}
        self.assertEqual(get_effective_capacity_multiplier(p), 2.0)

    def test_tiny_no_effects(self):
        p = {"active_effects": [], "base_size": "Tiny"}
        self.assertEqual(get_effective_capacity_multiplier(p), 0.5)

    def test_effective_size_overrides_base(self):
        p = {"active_effects": [], "base_size": "Medium", "effective_size": "Large"}
        self.assertEqual(get_effective_capacity_multiplier(p), 2.0)

    def test_bulls_strength_medium(self):
        p = {"active_effects": [_carry_effect(2.0)], "base_size": "Medium"}
        self.assertEqual(get_effective_capacity_multiplier(p), 2.0)

    def test_large_plus_bulls_strength(self):
        p = {"active_effects": [_carry_effect(2.0)], "base_size": "Large"}
        self.assertEqual(get_effective_capacity_multiplier(p), 4.0)

    def test_huge_plus_bulls_strength(self):
        p = {"active_effects": [_carry_effect(2.0)], "base_size": "Huge"}
        self.assertEqual(get_effective_capacity_multiplier(p), 8.0)

    def test_effective_size_large_plus_bulls_strength(self):
        p = {
            "active_effects": [_carry_effect(2.0)],
            "base_size": "Medium",
            "effective_size": "Large",
        }
        self.assertEqual(get_effective_capacity_multiplier(p), 4.0)

    def test_no_size_field_defaults_medium(self):
        p = {"active_effects": []}
        self.assertEqual(get_effective_capacity_multiplier(p), 1.0)

    def test_effective_size_none_falls_back_to_base(self):
        p = {"active_effects": [], "base_size": "Large", "effective_size": None}
        self.assertEqual(get_effective_capacity_multiplier(p), 2.0)


class TestGetEncumbranceTierForParticipantWithSize(unittest.TestCase):

    def test_large_size_doubles_thresholds(self):
        participant = {
            "id": "p1",
            "strength_score": 10,
            "total_weight_kg": 40.0,
            "active_effects": [],
            "base_size": "Large",
        }
        self.assertEqual(
            _get_encumbrance_tier_for_participant(participant),
            "normal",
        )

    def test_tiny_size_halves_thresholds(self):
        participant = {
            "id": "p1",
            "strength_score": 10,
            "total_weight_kg": 15.0,
            "active_effects": [],
            "base_size": "Tiny",
        }
        self.assertEqual(
            _get_encumbrance_tier_for_participant(participant),
            "encumbered",
        )

    def test_effective_size_large_applied(self):
        participant = {
            "id": "p1",
            "strength_score": 10,
            "total_weight_kg": 40.0,
            "active_effects": [],
            "base_size": "Medium",
            "effective_size": "Large",
        }
        self.assertEqual(
            _get_encumbrance_tier_for_participant(participant),
            "normal",
        )

    def test_large_plus_bulls_strength(self):
        participant = {
            "id": "p1",
            "strength_score": 10,
            "total_weight_kg": 100.0,
            "active_effects": [_carry_effect(2.0)],
            "base_size": "Large",
        }
        self.assertEqual(
            _get_encumbrance_tier_for_participant(participant),
            "encumbered",
        )


class TestEncumbranceTierForPlayerWithSize(unittest.TestCase):

    def test_large_effective_size(self):
        db = _make_db(strength=10, weight_lb=120.0)
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", effective_size="Large"),
            "encumbered",
        )

    def test_large_light_weight_normal(self):
        db = _make_db(strength=10, weight_lb=80.0)
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", effective_size="Large"),
            "normal",
        )

    def test_tiny_effective_size(self):
        db = _make_db(strength=10, weight_lb=30.0)
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", effective_size="Tiny"),
            "encumbered",
        )

    def test_large_plus_bulls_strength(self):
        db = _make_db(strength=10, weight_lb=250.0)
        self.assertEqual(
            _encumbrance_tier_for_player(
                db, "s1", "u1",
                active_effects=[_carry_effect(2.0)],
                effective_size="Large",
            ),
            "encumbered",
        )

    def test_medium_unchanged(self):
        db = _make_db(strength=10, weight_lb=120.0)
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", effective_size="Medium"),
            "heavily_encumbered",
        )


def _state_with_size(
    encumbrance_tier: str = "normal",
    phase=CombatPhase.active,
    effective_size: str | None = None,
    active_effects: list | None = None,
) -> MagicMock:
    s = MagicMock()
    s.phase = phase
    s.participants = [
        {
            "id": "p1",
            "ref_id": "user-1",
            "kind": "player",
            "encumbrance_tier": encumbrance_tier,
            "effective_size": effective_size,
            "base_size": "Medium",
            "active_effects": active_effects or [],
        }
    ]
    return s


class _CombatMixin(CombatLifecycleInitiativeMixin):
    @classmethod
    def _get_participant_by_ref(cls, state, ref_id):
        return next(
            (p for p in state.participants if p.get("ref_id") == ref_id), None
        )


def _recompute(db, state, player_user_id="user-1") -> bool:
    return _CombatMixin.recompute_participant_encumbrance_tier(db, "s1", state, player_user_id)


class TestRecomputeWithSize(unittest.TestCase):

    def test_large_effective_size_downgrades_tier(self):
        db = _make_db(strength=10, weight_lb=120.0)
        state = _state_with_size(
            encumbrance_tier="heavily_encumbered",
            effective_size="Large",
        )
        changed = _recompute(db, state)
        self.assertTrue(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "encumbered")

    def test_tiny_effective_size_upgrades_tier(self):
        db = _make_db(strength=10, weight_lb=30.0)
        state = _state_with_size(
            encumbrance_tier="normal",
            effective_size="Tiny",
        )
        changed = _recompute(db, state)
        self.assertTrue(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "encumbered")

    def test_large_plus_bulls_strength(self):
        db = _make_db(strength=10, weight_lb=200.0)
        state = _state_with_size(
            encumbrance_tier="overloaded",
            effective_size="Large",
            active_effects=[_carry_effect(2.0)],
        )
        changed = _recompute(db, state)
        self.assertTrue(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "normal")

    def test_medium_unchanged(self):
        db = _make_db(strength=10, weight_lb=120.0)
        state = _state_with_size(
            encumbrance_tier="heavily_encumbered",
            effective_size="Medium",
        )
        changed = _recompute(db, state)
        self.assertFalse(changed)
