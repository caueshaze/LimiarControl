"""Test: recompute_participant_encumbrance_tier during active combat.

Validates that the method correctly updates encumbrance_tier in the participant
dict when the player's inventory changes, and that it respects combat phase guards.
"""

import unittest
from unittest.mock import MagicMock

from app.models.combat import CombatPhase
from app.services.combat_service.lifecycle_initiative import (
    CombatLifecycleInitiativeMixin,
    _encumbrance_tier_for_player,
)

_LB_TO_KG = 0.45359237


def _kg_to_lb(kg: float) -> float:
    return kg / _LB_TO_KG


def _make_db(strength: int = 10, weight_lb: float = 0.0) -> MagicMock:
    db = MagicMock()
    entry = MagicMock()
    entry.state_json = {
        "abilities": {"strength": strength},
        "inventory": [{"weight": weight_lb, "quantity": 1}] if weight_lb > 0 else [],
    }
    db.exec.return_value.first.return_value = entry
    return db


def _state(encumbrance_tier: str = "normal", phase=CombatPhase.active) -> MagicMock:
    s = MagicMock()
    s.phase = phase
    s.participants = [
        {
            "id": "p1",
            "ref_id": "user-1",
            "kind": "player",
            "encumbrance_tier": encumbrance_tier,
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


class TestRecomputeParticipantEncumbranceTier(unittest.TestCase):

    def test_tier_rises_when_inventory_gets_heavier(self):
        """After adding heavy items, tier goes from normal to heavily_encumbered."""
        # STR 10 → normal max = 50 lb. 55 lb → encumbered
        db = _make_db(strength=10, weight_lb=_kg_to_lb(50))  # ≈110 lb → heavily
        state = _state(encumbrance_tier="normal")
        changed = _recompute(db, state)
        self.assertTrue(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "heavily_encumbered")

    def test_tier_drops_when_item_removed(self):
        """After removing items, tier goes from encumbered to normal."""
        db = _make_db(strength=10, weight_lb=10.0)  # 10 lb → normal
        state = _state(encumbrance_tier="encumbered")
        changed = _recompute(db, state)
        self.assertTrue(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "normal")

    def test_no_change_when_tier_unchanged(self):
        """Returns False and leaves participant untouched if tier is the same."""
        db = _make_db(strength=10, weight_lb=10.0)  # normal
        state = _state(encumbrance_tier="normal")
        changed = _recompute(db, state)
        self.assertFalse(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "normal")

    def test_participant_not_found_returns_false(self):
        """Returns False without error when player is not in combat."""
        db = _make_db(strength=10, weight_lb=_kg_to_lb(50))
        state = _state()
        changed = _recompute(db, state, player_user_id="unknown-user")
        self.assertFalse(changed)

    def test_phase_ended_returns_false(self):
        """Does not update participants when combat is ended."""
        db = _make_db(strength=10, weight_lb=_kg_to_lb(50))
        state = _state(encumbrance_tier="normal", phase=CombatPhase.ended)
        changed = _recompute(db, state)
        self.assertFalse(changed)
        self.assertEqual(state.participants[0]["encumbrance_tier"], "normal")

    def test_phase_initiative_returns_false(self):
        """Does not update during initiative phase — guard only allows active."""
        db = _make_db(strength=10, weight_lb=_kg_to_lb(50))
        state = _state(encumbrance_tier="normal", phase=CombatPhase.initiative)
        changed = _recompute(db, state)
        self.assertFalse(changed)

    def test_phase_string_active_accepted(self):
        """Accepts 'active' as a string for robustness."""
        db = _make_db(strength=10, weight_lb=_kg_to_lb(50))
        state = _state(encumbrance_tier="normal")
        state.phase = "active"
        changed = _recompute(db, state)
        self.assertTrue(changed)
