"""Test: encumbrance movement penalty applied to movement_speed_cells.

Validates apply_encumbrance_movement_penalty and its integration in
resolve_sync_entry — the function that sends movement_speed_cells to LimiarMap.
LimiarMap uses this value as the movement budget, so reducing it here
automatically enforces the encumbrance movement limit.
"""

import unittest
from unittest.mock import MagicMock

from app.integrations.limiar_map_client_types import LimiarMapStateResponse
from app.services.combat_service.condition_effects_predicates import (
    apply_encumbrance_movement_penalty,
)
from app.services.combat_service.token_resolution import resolve_sync_entry


def _map_state_empty() -> LimiarMapStateResponse:
    return LimiarMapStateResponse(session_id="s1", version=1, tokens=())


def _make_db(speed_meters: int) -> MagicMock:
    db = MagicMock()
    entry = MagicMock()
    entry.state_json = {"speedMeters": speed_meters}
    db.exec.return_value.first.return_value = entry
    return db


def _player(encumbrance_tier: str | None = None) -> dict:
    p: dict = {
        "id": "p1",
        "kind": "player",
        "ref_id": "user-1",
        "display_name": "Hero",
        "active_effects": [],
    }
    if encumbrance_tier is not None:
        p["encumbrance_tier"] = encumbrance_tier
    return p


class TestApplyEncumbranceMovementPenalty(unittest.TestCase):

    def test_normal_no_penalty(self):
        self.assertEqual(apply_encumbrance_movement_penalty(9.0, "normal"), 9.0)

    def test_encumbered_minus_3m(self):
        self.assertEqual(apply_encumbrance_movement_penalty(9.0, "encumbered"), 6.0)

    def test_encumbered_low_speed_clamped(self):
        self.assertEqual(apply_encumbrance_movement_penalty(2.0, "encumbered"), 0.0)

    def test_encumbered_exact_limit(self):
        # 3 - 3 = 0, not negative
        self.assertEqual(apply_encumbrance_movement_penalty(3.0, "encumbered"), 0.0)

    def test_heavily_encumbered_minus_6m(self):
        self.assertEqual(apply_encumbrance_movement_penalty(9.0, "heavily_encumbered"), 3.0)

    def test_heavily_encumbered_low_speed_clamped(self):
        self.assertEqual(apply_encumbrance_movement_penalty(5.0, "heavily_encumbered"), 0.0)

    def test_overloaded_any_speed_zero(self):
        self.assertEqual(apply_encumbrance_movement_penalty(9.0, "overloaded"), 0.0)

    def test_overloaded_zero_base(self):
        self.assertEqual(apply_encumbrance_movement_penalty(0.0, "overloaded"), 0.0)

    def test_unknown_tier_no_penalty(self):
        self.assertEqual(apply_encumbrance_movement_penalty(9.0, ""), 9.0)
        self.assertEqual(apply_encumbrance_movement_penalty(9.0, "unknown"), 9.0)


class TestResolveSyncEntryMovementSpeed(unittest.TestCase):
    """resolve_sync_entry applies encumbrance penalty to movement_speed_cells.

    9 m base speed:
      normal → 9 m → meters_to_movement_cells(9) = 6 cells
      encumbered → 6 m → meters_to_movement_cells(6) = 4 cells
      heavily_encumbered → 3 m → meters_to_movement_cells(3) = 2 cells
      overloaded → 0 m → meters_to_movement_cells(0) = 0 cells
    """

    def _get_speed_cells(self, participant: dict) -> int | None:
        db = _make_db(9)
        _, spawn = resolve_sync_entry(db, "s1", participant, _map_state_empty())
        self.assertIsNotNone(spawn)
        return spawn.movement_speed_cells

    def test_normal_tier(self):
        self.assertEqual(self._get_speed_cells(_player("normal")), 6)

    def test_encumbered_tier(self):
        self.assertEqual(self._get_speed_cells(_player("encumbered")), 4)

    def test_heavily_encumbered_tier(self):
        self.assertEqual(self._get_speed_cells(_player("heavily_encumbered")), 2)

    def test_overloaded_tier(self):
        self.assertEqual(self._get_speed_cells(_player("overloaded")), 0)

    def test_no_encumbrance_tier_field_defaults_normal(self):
        # participant dict without encumbrance_tier key → fallback to "normal"
        self.assertEqual(self._get_speed_cells(_player()), 6)
