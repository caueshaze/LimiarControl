from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from app.services.combat import CombatService


class TargetCreatureTypeTests(unittest.TestCase):
    def test_normalize_creature_type_casing(self):
        self.assertEqual(CombatService.normalize_creature_type("humanoid"), "humanoid")
        self.assertEqual(CombatService.normalize_creature_type("Humanoid"), "humanoid")
        self.assertEqual(CombatService.normalize_creature_type("HUMANOID"), "humanoid")

    def test_normalize_creature_type_known_non_humanoid(self):
        self.assertEqual(CombatService.normalize_creature_type("Dragon"), "dragon")

    def test_normalize_creature_type_invalid(self):
        self.assertIsNone(CombatService.normalize_creature_type(""))
        self.assertIsNone(CombatService.normalize_creature_type("humanoide"))
        self.assertIsNone(CombatService.normalize_creature_type(None))

    def test_player_without_wildshape_is_humanoid(self):
        db = MagicMock()
        ss_result = MagicMock()
        ss_result.first.return_value = MagicMock(state_json={"wildShape": {"active": False}})
        db.exec.return_value = ss_result
        participant = {"kind": "player", "ref_id": "player-1"}
        self.assertEqual(
            CombatService.resolve_effective_creature_type(db, "s1", participant),
            "humanoid",
        )

    def test_player_with_wildshape_beast_is_beast(self):
        db = MagicMock()
        ss_result = MagicMock()
        ss_result.first.return_value = MagicMock(state_json={"wildShape": {"active": True, "formKey": "wolf"}})
        db.exec.return_value = ss_result
        participant = {"kind": "player", "ref_id": "player-1"}
        self.assertEqual(
            CombatService.resolve_effective_creature_type(db, "s1", participant),
            "beast",
        )

    def test_session_entity_type_is_normalized(self):
        db = MagicMock()
        se_result = MagicMock()
        se_result.first.return_value = MagicMock(campaign_entity_id="ce-1")
        ce_result = MagicMock()
        ce_result.first.return_value = MagicMock(creature_type="Humanoid")
        db.exec.side_effect = [se_result, ce_result]
        participant = {"kind": "session_entity", "ref_id": "enemy-1"}
        self.assertEqual(
            CombatService.resolve_effective_creature_type(db, "s1", participant),
            "humanoid",
        )

    def test_session_entity_dragon(self):
        db = MagicMock()
        se_result = MagicMock()
        se_result.first.return_value = MagicMock(campaign_entity_id="ce-1")
        ce_result = MagicMock()
        ce_result.first.return_value = MagicMock(creature_type="Dragon")
        db.exec.side_effect = [se_result, ce_result]
        participant = {"kind": "session_entity", "ref_id": "enemy-1"}
        self.assertEqual(
            CombatService.resolve_effective_creature_type(db, "s1", participant),
            "dragon",
        )


if __name__ == "__main__":
    unittest.main()
