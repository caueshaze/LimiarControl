"""Test: carrying capacity multiplier applied to encumbrance tier recomputation.

Validates that:
- compute_encumbrance_tier_from_lb accepts capacity_multiplier and scales thresholds
- _encumbrance_tier_for_player reads active_effects and passes the multiplier
- _get_encumbrance_tier_for_participant uses get_carrying_capacity_multiplier
- recompute_participant_encumbrance_tier passes participant active_effects
- removing the effect reverts the tier
"""

import unittest
from unittest.mock import MagicMock

from app.models.combat import CombatPhase
from app.services.combat_service.condition_effects_predicates import (
    compute_encumbrance_tier_from_lb,
    _get_encumbrance_tier_for_participant,
)
from app.services.combat_service.lifecycle_initiative import (
    CombatLifecycleInitiativeMixin,
    _encumbrance_tier_for_player,
)

_LB_TO_KG = 0.45359237


def _kg_to_lb(kg: float) -> float:
    return kg / _LB_TO_KG


def _carry_effect(multiplier: float, group_id: str | None = None) -> dict:
    metadata: dict = {
        "source_spell_name": "Enhance Ability",
        "declarative_effect_group_id": group_id or "enhance_ability|bulls_strength|carrying_capacity_multiplier|2",
        "declarative_effect": {
            "type": "carrying_capacity_multiplier",
            "params": {"multiplier": multiplier},
        },
    }
    return {
        "id": f"eff-carry-{multiplier}",
        "kind": "spell_effect",
        "metadata": metadata,
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


class TestComputeEncumbranceTierWithMultiplier(unittest.TestCase):

    def test_default_multiplier_preserves_existing_behavior(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 30), "normal")
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 50), "normal")
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 50.1), "encumbered")
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 100), "encumbered")
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 100.1), "heavily_encumbered")
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 150), "heavily_encumbered")
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 150.1), "overloaded")

    def test_x2_multiplier_doubles_effective_strength(self):
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 100, capacity_multiplier=2.0),
            "normal",
        )
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 100.1, capacity_multiplier=2.0),
            "encumbered",
        )
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 200, capacity_multiplier=2.0),
            "encumbered",
        )
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 200.1, capacity_multiplier=2.0),
            "heavily_encumbered",
        )
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 300, capacity_multiplier=2.0),
            "heavily_encumbered",
        )
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 300.1, capacity_multiplier=2.0),
            "overloaded",
        )

    def test_x2_heavy_weight_becomes_encumbered_not_heavily(self):
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 120, capacity_multiplier=2.0),
            "encumbered",
        )

    def test_x2_light_weight_stays_normal(self):
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 80, capacity_multiplier=2.0),
            "normal",
        )

    def test_x3_multiplier_triples_effective_strength(self):
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 150, capacity_multiplier=3.0),
            "normal",
        )
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 150.1, capacity_multiplier=3.0),
            "encumbered",
        )
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 450.1, capacity_multiplier=3.0),
            "overloaded",
        )

    def test_boundary_exact_threshold_with_x2(self):
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 50.0, capacity_multiplier=2.0),
            "normal",
        )
        self.assertEqual(
            compute_encumbrance_tier_from_lb(10, 100.0, capacity_multiplier=2.0),
            "normal",
        )


class TestEncumbranceTierForPlayerWithMultiplier(unittest.TestCase):

    def test_no_effects_uses_default_multiplier(self):
        db = _make_db(strength=10, weight_lb=120.0)
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", active_effects=[]),
            "heavily_encumbered",
        )

    def test_x2_effect_downgrades_from_heavily_to_encumbered(self):
        db = _make_db(strength=10, weight_lb=120.0)
        effects = [_carry_effect(2.0)]
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", active_effects=effects),
            "encumbered",
        )

    def test_x2_effect_light_weight_normal(self):
        db = _make_db(strength=10, weight_lb=80.0)
        effects = [_carry_effect(2.0)]
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", active_effects=effects),
            "normal",
        )

    def test_x2_effect_on_boundary(self):
        db = _make_db(strength=10, weight_lb=100.1)
        effects = [_carry_effect(2.0)]
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", active_effects=effects),
            "encumbered",
        )

    def test_x2_effect_heavy_weight_heavily_encumbered(self):
        db = _make_db(strength=10, weight_lb=250.0)
        effects = [_carry_effect(2.0)]
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", active_effects=effects),
            "heavily_encumbered",
        )

    def test_x2_effect_overloaded_still_overloaded(self):
        db = _make_db(strength=10, weight_lb=350.0)
        effects = [_carry_effect(2.0)]
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", active_effects=effects),
            "overloaded",
        )

    def test_none_active_effects_uses_default_multiplier(self):
        db = _make_db(strength=10, weight_lb=120.0)
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1", active_effects=None),
            "heavily_encumbered",
        )

    def test_without_active_effects_kwarg_preserves_behavior(self):
        db = _make_db(strength=10, weight_lb=120.0)
        self.assertEqual(
            _encumbrance_tier_for_player(db, "s1", "u1"),
            "heavily_encumbered",
        )


class TestGetEncumbranceTierForParticipantWithMultiplier(unittest.TestCase):

    def test_with_x2_effect_and_fallback_computation(self):
        participant = {
            "id": "p1",
            "strength_score": 10,
            "total_weight_kg": 45.0,
            "active_effects": [_carry_effect(2.0)],
        }
        self.assertEqual(
            _get_encumbrance_tier_for_participant(participant),
            "normal",
        )

    def test_without_effect_uses_default(self):
        participant = {
            "id": "p1",
            "strength_score": 10,
            "total_weight_kg": 45.0,
            "active_effects": [],
        }
        self.assertEqual(
            _get_encumbrance_tier_for_participant(participant),
            "encumbered",
        )

    def test_with_x2_effect_medium_weight_encumbered(self):
        participant = {
            "id": "p1",
            "strength_score": 10,
            "total_weight_kg": 55.0,
            "active_effects": [_carry_effect(2.0)],
        }
        self.assertEqual(
            _get_encumbrance_tier_for_participant(participant),
            "encumbered",
        )


def _state_with_effects(
    encumbrance_tier: str = "normal",
    phase=CombatPhase.active,
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


class TestRecomputeWithMultiplier(unittest.TestCase):

    def test_x2_effect_changes_tier_from_heavily_to_encumbered(self):
        db = _make_db(strength=10, weight_lb=120.0)
        state = _state_with_effects(
            encumbrance_tier="heavily_encumbered",
            active_effects=[_carry_effect(2.0)],
        )
        changed = _recompute(db, state)
        self.assertTrue(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "encumbered")

    def test_x2_effect_keeps_normal_when_weight_within_doubled_threshold(self):
        db = _make_db(strength=10, weight_lb=80.0)
        state = _state_with_effects(
            encumbrance_tier="normal",
            active_effects=[_carry_effect(2.0)],
        )
        changed = _recompute(db, state)
        self.assertFalse(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "normal")

    def test_no_effect_preserves_existing_tier(self):
        db = _make_db(strength=10, weight_lb=120.0)
        state = _state_with_effects(
            encumbrance_tier="heavily_encumbered",
            active_effects=[],
        )
        changed = _recompute(db, state)
        self.assertFalse(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "heavily_encumbered")

    def test_removing_effect_reverts_tier(self):
        db = _make_db(strength=10, weight_lb=120.0)
        state = _state_with_effects(
            encumbrance_tier="encumbered",
            active_effects=[],
        )
        changed = _recompute(db, state)
        self.assertTrue(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "heavily_encumbered")

    def test_x2_effect_heavy_weight_still_overloaded(self):
        db = _make_db(strength=10, weight_lb=350.0)
        state = _state_with_effects(
            encumbrance_tier="overloaded",
            active_effects=[_carry_effect(2.0)],
        )
        changed = _recompute(db, state)
        self.assertFalse(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "overloaded")

    def test_x2_effect_medium_weight_becomes_encumbered(self):
        db = _make_db(strength=10, weight_lb=150.0)
        state = _state_with_effects(
            encumbrance_tier="overloaded",
            active_effects=[_carry_effect(2.0)],
        )
        changed = _recompute(db, state)
        self.assertTrue(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "encumbered")

    def test_phase_ignored_during_initiative(self):
        db = _make_db(strength=10, weight_lb=120.0)
        state = _state_with_effects(
            encumbrance_tier="heavily_encumbered",
            phase=CombatPhase.initiative,
            active_effects=[_carry_effect(2.0)],
        )
        changed = _recompute(db, state)
        self.assertFalse(changed)
