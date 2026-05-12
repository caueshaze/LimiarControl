from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import get_movement_speed_bonus_meters
from app.services.combat_service.persistent_effects import restore_persisted_effects
from app.services.session_state_finalize import calculate_player_armor_class_from_state


def _longstrider_effect(effect_id: str = "ls-1", group: str | None = None) -> dict:
    md = {
        "source_spell_key": "longstrider",
        "declarative_effect": {
            "type": "modify_movement_speed",
            "target": "selected_target",
            "params": {"bonus_meters": 3.0},
        },
        "concentration": False,
        "concentration_group": None,
    }
    if group:
        md["declarative_effect_group_id"] = group
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "duration_type": "timed",
        "created_at_game_time_seconds": 100,
        "expires_at_game_time_seconds": 3700,
        "metadata": md,
    }


class LongstriderSeedTests(unittest.TestCase):
    def test_seed_has_canonical_longstrider_shape(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("longstrider", spells)
        s = spells["longstrider"]
        self.assertEqual(s["level"], 1)
        self.assertEqual(s["school"], "transmutation")
        self.assertEqual(s["castingTimeType"], "action")
        self.assertEqual(s["rangeKind"], "touch")
        self.assertFalse(s["concentration"])
        self.assertEqual(s["selectionType"], "creature")
        self.assertNotIn("upcast", s)
        e = (s.get("effects") or [])[0]
        self.assertEqual(e.get("type"), "modify_movement_speed")
        self.assertEqual((e.get("params") or {}).get("bonus_meters"), 3.0)
        self.assertEqual((e.get("duration") or {}).get("type"), "timed")
        self.assertEqual((e.get("duration") or {}).get("seconds"), 3600)


class LongstriderRuntimeTests(unittest.TestCase):
    def test_bonus_meters_applies_exactly_three_meters(self):
        p = {"active_effects": [_longstrider_effect()]}
        total, sources = get_movement_speed_bonus_meters(p)
        self.assertEqual(total, 3.0)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["type"], "modify_movement_speed")

    def test_same_group_dedup_prevents_double_apply(self):
        p = {"active_effects": [_longstrider_effect("a", group="g1"), _longstrider_effect("b", group="g1")]}
        total, _ = get_movement_speed_bonus_meters(p)
        self.assertEqual(total, 3.0)

    def test_non_concentration_effect_has_no_group(self):
        eff = _longstrider_effect()
        md = eff["metadata"]
        self.assertFalse(md.get("concentration"))
        self.assertIsNone(md.get("concentration_group"))

    def test_does_not_affect_ac_or_roll_domains(self):
        state = {
            "abilities": {"dexterity": 14},
            "active_spell_effects": [_longstrider_effect()],
        }
        # default unarmored AC is still 12 for DEX 14
        self.assertEqual(calculate_player_armor_class_from_state(state), 12)


class LongstriderPersistenceRestoreTests(unittest.TestCase):
    def test_restore_into_combat_without_duplicate(self):
        session_state = SessionState(
            id="ss1",
            session_id="s1",
            player_user_id="u1",
            state_json={"active_spell_effects": [_longstrider_effect()]},
        )
        db = MagicMock()
        db.exec.return_value.first.return_value = session_state
        participant = {"id": "p1", "kind": "player", "ref_id": "u1", "active_effects": []}
        restore_persisted_effects(db, "s1", participant)
        restore_persisted_effects(db, "s1", participant)
        effects = participant.get("active_effects", [])
        self.assertEqual(len(effects), 1)
        self.assertEqual((effects[0].get("metadata") or {}).get("source_spell_key"), "longstrider")

    def test_expired_effect_removed_from_state(self):
        session_state = SessionState(
            id="ss1",
            session_id="s1",
            player_user_id="u1",
            state_json={"active_spell_effects": [_longstrider_effect()]},
        )
        db = MagicMock()
        db.exec.return_value.first.return_value = session_state
        # make current time beyond expiry
        with unittest.mock.patch("app.services.combat_service.persistent_effects.get_game_time_seconds", return_value=99999):
            participant = {"id": "p1", "kind": "player", "ref_id": "u1", "active_effects": []}
            restore_persisted_effects(db, "s1", participant)
        self.assertEqual(participant.get("active_effects", []), [])


if __name__ == "__main__":
    unittest.main()
