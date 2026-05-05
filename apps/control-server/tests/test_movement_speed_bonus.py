"""Tests for modify_movement_speed declarative effect.

Covers:
- get_movement_speed_bonus_meters predicate
- Integration into resolve_sync_entry (token_resolution)
- Encumbrance + bonus ordering
- Dedup by group key
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.integrations.limiar_map_client_types import LimiarMapStateResponse
from app.services.combat_service.condition_effects_predicates import (
    get_movement_speed_bonus_meters,
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


def _player(
    *,
    encumbrance_tier: str | None = None,
    active_effects: list[dict] | None = None,
) -> dict:
    p: dict = {
        "id": "p1",
        "kind": "player",
        "ref_id": "user-1",
        "display_name": "Hero",
        "active_effects": active_effects or [],
    }
    if encumbrance_tier is not None:
        p["encumbrance_tier"] = encumbrance_tier
    return p


def _movement_speed_effect(
    *,
    bonus_meters: float = 3,
    group_id: str = "g1",
    spell_name: str = "Passos Longos",
    effect_id: str = "eff-1",
) -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "condition_type": None,
        "numeric_value": None,
        "duration_type": "until_long_rest",
        "display_label": spell_name,
        "metadata": {
            "declarative_effect_group_id": group_id,
            "declarative_effect": {
                "type": "modify_movement_speed",
                "params": {"bonus_meters": bonus_meters},
            },
            "source_spell_name": spell_name,
        },
    }


class TestGetMovementSpeedBonusMeters(unittest.TestCase):

    def test_single_effect_adds_bonus(self):
        participant = _player(active_effects=[_movement_speed_effect(bonus_meters=3)])
        total, sources = get_movement_speed_bonus_meters(participant)
        self.assertEqual(total, 3.0)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["label"], "Passos Longos")
        self.assertEqual(sources[0]["value"], 3.0)

    def test_ignores_non_spell_effects(self):
        participant = _player(active_effects=[
            {"kind": "condition", "condition_type": "blinded"},
        ])
        total, sources = get_movement_speed_bonus_meters(participant)
        self.assertEqual(total, 0.0)
        self.assertEqual(len(sources), 0)

    def test_ignores_wrong_type(self):
        participant = _player(active_effects=[{
            "id": "e1",
            "kind": "spell_effect",
            "metadata": {
                "declarative_effect": {
                    "type": "passive_skill_bonus",
                    "params": {"skill": "perception", "bonus": 5},
                },
                "source_spell_name": "Other",
            },
        }])
        total, sources = get_movement_speed_bonus_meters(participant)
        self.assertEqual(total, 0.0)

    def test_ignores_invalid_bonus_meters(self):
        participant = _player(active_effects=[{
            "id": "e1",
            "kind": "spell_effect",
            "metadata": {
                "declarative_effect": {
                    "type": "modify_movement_speed",
                    "params": {"bonus_meters": "not_a_number"},
                },
                "source_spell_name": "Bad",
            },
        }])
        total, sources = get_movement_speed_bonus_meters(participant)
        self.assertEqual(total, 0.0)

    def test_multiple_effects_stack(self):
        participant = _player(active_effects=[
            _movement_speed_effect(bonus_meters=3, group_id="g1", spell_name="Passos Longos"),
            _movement_speed_effect(bonus_meters=2, group_id="g2", spell_name="Outro Buff", effect_id="eff-2"),
        ])
        total, sources = get_movement_speed_bonus_meters(participant)
        self.assertEqual(total, 5.0)
        self.assertEqual(len(sources), 2)

    def test_dedup_same_group_id(self):
        participant = _player(active_effects=[
            _movement_speed_effect(bonus_meters=3, group_id="g1", effect_id="eff-1"),
            _movement_speed_effect(bonus_meters=3, group_id="g1", effect_id="eff-1-dup"),
        ])
        total, sources = get_movement_speed_bonus_meters(participant)
        self.assertEqual(total, 3.0)
        self.assertEqual(len(sources), 1)

    def test_no_active_effects(self):
        participant = _player()
        total, sources = get_movement_speed_bonus_meters(participant)
        self.assertEqual(total, 0.0)
        self.assertEqual(len(sources), 0)


class TestResolveSyncEntryMovementSpeedBonus(unittest.TestCase):

    def _get_speed_cells(self, participant: dict, speed_meters: int = 9) -> int | None:
        db = _make_db(speed_meters)
        _, spawn = resolve_sync_entry(db, "s1", participant, _map_state_empty())
        self.assertIsNotNone(spawn)
        return spawn.movement_speed_cells

    def test_normal_no_bonus(self):
        speed = self._get_speed_cells(_player())
        self.assertEqual(speed, 6)

    def test_bonus_adds_to_speed(self):
        participant = _player(active_effects=[_movement_speed_effect(bonus_meters=3)])
        speed = self._get_speed_cells(participant, speed_meters=9)
        self.assertEqual(speed, 8)

    def test_encumbrance_before_bonus(self):
        participant = _player(
            encumbrance_tier="encumbered",
            active_effects=[_movement_speed_effect(bonus_meters=3)],
        )
        speed = self._get_speed_cells(participant, speed_meters=9)
        self.assertEqual(speed, 6)

    def test_heavily_encumbered_with_bonus(self):
        participant = _player(
            encumbrance_tier="heavily_encumbered",
            active_effects=[_movement_speed_effect(bonus_meters=3)],
        )
        speed = self._get_speed_cells(participant, speed_meters=9)
        self.assertEqual(speed, 4)

    def test_overloaded_with_bonus_clamped(self):
        participant = _player(
            encumbrance_tier="overloaded",
            active_effects=[_movement_speed_effect(bonus_meters=3)],
        )
        speed = self._get_speed_cells(participant, speed_meters=9)
        self.assertEqual(speed, 2)

    def test_large_bonus_converts_correctly(self):
        participant = _player(active_effects=[_movement_speed_effect(bonus_meters=6)])
        speed = self._get_speed_cells(participant, speed_meters=9)
        self.assertEqual(speed, 10)


class TestEncumbranceOrder(unittest.TestCase):

    def test_penalty_first_then_bonus(self):
        db = _make_db(9)
        participant = _player(
            encumbrance_tier="encumbered",
            active_effects=[_movement_speed_effect(bonus_meters=3)],
        )
        _, spawn = resolve_sync_entry(db, "s1", participant, _map_state_empty())
        self.assertIsNotNone(spawn)
        self.assertEqual(spawn.movement_speed_cells, 6)
