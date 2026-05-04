"""Test: encumbrance_tier sync into CombatState participants at combat start.

Validates _encumbrance_tier_for_player and compute_encumbrance_tier_from_lb.
STR 10 thresholds (in lb): normal ≤ 50, encumbered ≤ 100, heavily ≤ 150, overloaded > 150.
Uses `>` (strict), not `>=`.
"""

import unittest
from unittest.mock import MagicMock

from app.services.combat_service.condition_effects_predicates import (
    compute_encumbrance_tier_from_lb,
)
from app.services.combat_service.lifecycle_initiative import (
    _encumbrance_tier_for_player,
)

_LB_TO_KG = 0.45359237


def _kg_to_lb(kg: float) -> float:
    return kg / _LB_TO_KG


def _make_db(state_json: dict | None) -> MagicMock:
    db = MagicMock()
    if state_json is None:
        db.exec.return_value.first.return_value = None
    else:
        entry = MagicMock()
        entry.state_json = state_json
        db.exec.return_value.first.return_value = entry
    return db


def _state_json(strength: int = 10, items: list[dict] | None = None) -> dict:
    return {
        "abilities": {"strength": strength},
        "inventory": items or [],
    }


def _item(weight_lb: float, quantity: int = 1) -> dict:
    return {"weight": weight_lb, "quantity": quantity}


class TestComputeEncumbranceTierFromLb(unittest.TestCase):
    """Unit tests for the shared computation helper."""

    def test_normal(self):
        # STR 10 → normal max = 50 lb
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 30), "normal")

    def test_exact_normal_boundary(self):
        # 50 lb == normal threshold → still normal (uses >)
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 50), "normal")

    def test_just_above_normal_boundary(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 50.1), "encumbered")

    def test_encumbered(self):
        # 25 kg ≈ 55 lb → encumbered
        self.assertEqual(compute_encumbrance_tier_from_lb(10, _kg_to_lb(25)), "encumbered")

    def test_heavily_encumbered(self):
        # 50 kg ≈ 110 lb → heavily_encumbered
        self.assertEqual(compute_encumbrance_tier_from_lb(10, _kg_to_lb(50)), "heavily_encumbered")

    def test_overloaded(self):
        # 70 kg ≈ 154 lb → overloaded
        self.assertEqual(compute_encumbrance_tier_from_lb(10, _kg_to_lb(70)), "overloaded")

    def test_zero_weight(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 0), "normal")


class TestEncumbranceTierForPlayer(unittest.TestCase):
    """Tests for _encumbrance_tier_for_player helper."""

    def test_normal_load(self):
        db = _make_db(_state_json(10, [_item(20)]))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")

    def test_encumbered(self):
        # 25 kg ≈ 55.1 lb > 50 lb (STR 10 × 5)
        db = _make_db(_state_json(10, [_item(_kg_to_lb(25))]))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "encumbered")

    def test_heavily_encumbered(self):
        # 50 kg ≈ 110 lb → between 100 and 150 lb
        db = _make_db(_state_json(10, [_item(_kg_to_lb(50))]))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "heavily_encumbered")

    def test_overloaded(self):
        # 70 kg ≈ 154 lb > 150 lb (STR 10 × 15)
        db = _make_db(_state_json(10, [_item(_kg_to_lb(70))]))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "overloaded")

    def test_no_session_state_fallback(self):
        """No SessionState found → safe fallback to normal."""
        db = _make_db(None)
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")

    def test_missing_abilities_field(self):
        """state_json without abilities → defaults to STR 10."""
        db = _make_db({"inventory": []})
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")

    def test_missing_inventory_field(self):
        """state_json without inventory → zero weight → normal."""
        db = _make_db({"abilities": {"strength": 10}})
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")

    def test_quantity_multiplied(self):
        """Items with quantity > 1 have their weight multiplied."""
        # STR 10 → heavily max = 150 lb. 3 × 40 lb = 120 lb → heavily_encumbered
        db = _make_db(_state_json(10, [_item(40, quantity=3)]))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "heavily_encumbered")

    def test_multiple_items_summed(self):
        """Multiple items are summed."""
        # 30 + 30 = 60 lb → encumbered (STR 10 normal max = 50 lb)
        db = _make_db(_state_json(10, [_item(30), _item(30)]))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "encumbered")

    def test_high_strength_stays_normal(self):
        """High STR raises all thresholds."""
        # STR 20 → normal max = 100 lb. 25 kg ≈ 55 lb → still normal
        db = _make_db(_state_json(20, [_item(_kg_to_lb(25))]))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")
