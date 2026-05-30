"""Test: get_player_total_inventory_weight_lb reads weight from InventoryItem + Item.

Validates the single-source-of-truth weight function that replaced state_json["inventory"]
weight computation. All scenarios mock 3 sequential db.exec calls:
  1. CampaignSession lookup (first)
  2. CampaignMember lookup (first)
  3. Weight sum query (scalar)
"""

import unittest
from unittest.mock import MagicMock

from app.services.combat_service.lifecycle_initiative import (
    get_player_total_inventory_weight_lb,
)


def _make_db(campaign_id="camp-1", member_id="member-1", weight_lb=0.0, no_session=False, no_member=False):
    db = MagicMock()

    if no_session:
        db.exec.side_effect = [
            MagicMock(first=MagicMock(return_value=None)),
        ]
        return db

    campaign_session = MagicMock()
    campaign_session.campaign_id = campaign_id

    if no_member:
        db.exec.side_effect = [
            MagicMock(first=MagicMock(return_value=campaign_session)),
            MagicMock(first=MagicMock(return_value=None)),
        ]
        return db

    member = MagicMock()
    member.id = member_id

    db.exec.side_effect = [
        MagicMock(first=MagicMock(return_value=campaign_session)),
        MagicMock(first=MagicMock(return_value=member)),
        MagicMock(first=MagicMock(return_value=weight_lb)),
    ]
    return db


class TestGetPlayerTotalInventoryWeightLb(unittest.TestCase):

    def test_single_item_weight(self):
        db = _make_db(weight_lb=10.0)
        result = get_player_total_inventory_weight_lb(db, "s1", "u1")
        self.assertAlmostEqual(result, 10.0)

    def test_null_weight_coalesces_to_zero(self):
        db = _make_db(weight_lb=0.0)
        result = get_player_total_inventory_weight_lb(db, "s1", "u1")
        self.assertAlmostEqual(result, 0.0)

    def test_multiple_items_summed(self):
        db = _make_db(weight_lb=75.5)
        result = get_player_total_inventory_weight_lb(db, "s1", "u1")
        self.assertAlmostEqual(result, 75.5)

    def test_empty_inventory(self):
        db = _make_db(weight_lb=0.0)
        result = get_player_total_inventory_weight_lb(db, "s1", "u1")
        self.assertAlmostEqual(result, 0.0)

    def test_no_session_returns_zero(self):
        db = _make_db(no_session=True)
        result = get_player_total_inventory_weight_lb(db, "s1", "u1")
        self.assertAlmostEqual(result, 0.0)

    def test_no_member_returns_zero(self):
        db = _make_db(no_member=True)
        result = get_player_total_inventory_weight_lb(db, "s1", "u1")
        self.assertAlmostEqual(result, 0.0)

    def test_none_scalar_returns_zero(self):
        db = _make_db(weight_lb=None)
        result = get_player_total_inventory_weight_lb(db, "s1", "u1")
        self.assertAlmostEqual(result, 0.0)
