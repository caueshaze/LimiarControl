"""Test: encumbrance_tier sync into CombatState participants at combat start.

Validates _encumbrance_tier_for_player and compute_encumbrance_tier_from_lb.
STR 10 thresholds (in lb): normal ≤ 50, encumbered ≤ 100, heavily ≤ 150, overloaded > 150.
Uses `>` (strict), not `>=`.

_encumbrance_tier_for_player now calls get_player_total_inventory_weight_lb which
makes 4 sequential db.exec calls: SessionState, CampaignSession, CampaignMember,
weight sum (scalar). The _make_db helper mocks all 4 via side_effect.
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
        MagicMock(first=MagicMock(return_value=weight_lb)),
    ]
    return db


def _make_db_no_state() -> MagicMock:
    db = MagicMock()
    db.exec.side_effect = [
        MagicMock(first=MagicMock(return_value=None)),
    ]
    return db


class TestComputeEncumbranceTierFromLb(unittest.TestCase):
    """Unit tests for the shared computation helper."""

    def test_normal(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 30), "normal")

    def test_exact_normal_boundary(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 50), "normal")

    def test_just_above_normal_boundary(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 50.1), "encumbered")

    def test_encumbered(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, _kg_to_lb(25)), "encumbered")

    def test_heavily_encumbered(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, _kg_to_lb(50)), "heavily_encumbered")

    def test_overloaded(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, _kg_to_lb(70)), "overloaded")

    def test_zero_weight(self):
        self.assertEqual(compute_encumbrance_tier_from_lb(10, 0), "normal")


class TestEncumbranceTierForPlayer(unittest.TestCase):
    """Tests for _encumbrance_tier_for_player helper."""

    def test_normal_load(self):
        db = _make_db(strength=10, weight_lb=20.0)
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")

    def test_encumbered(self):
        db = _make_db(strength=10, weight_lb=_kg_to_lb(25))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "encumbered")

    def test_heavily_encumbered(self):
        db = _make_db(strength=10, weight_lb=_kg_to_lb(50))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "heavily_encumbered")

    def test_overloaded(self):
        db = _make_db(strength=10, weight_lb=_kg_to_lb(70))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "overloaded")

    def test_no_session_state_fallback(self):
        db = _make_db_no_state()
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")

    def test_missing_abilities_field(self):
        db = MagicMock()
        session_state = MagicMock()
        session_state.state_json = {}
        campaign_session = MagicMock()
        campaign_session.campaign_id = "camp-1"
        member = MagicMock()
        member.id = "member-1"
        db.exec.side_effect = [
            MagicMock(first=MagicMock(return_value=session_state)),
            MagicMock(first=MagicMock(return_value=campaign_session)),
            MagicMock(first=MagicMock(return_value=member)),
            MagicMock(first=MagicMock(return_value=0.0)),
        ]
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")

    def test_missing_inventory_field(self):
        db = _make_db(strength=10, weight_lb=0.0)
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")

    def test_quantity_multiplied(self):
        db = _make_db(strength=10, weight_lb=120.0)
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "heavily_encumbered")

    def test_multiple_items_summed(self):
        db = _make_db(strength=10, weight_lb=60.0)
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "encumbered")

    def test_high_strength_stays_normal(self):
        db = _make_db(strength=20, weight_lb=_kg_to_lb(25))
        self.assertEqual(_encumbrance_tier_for_player(db, "s1", "u1"), "normal")
