from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from app.schemas.roll import RollResult
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import get_roll_bonus_dice_sources


class BaneSeedTests(unittest.TestCase):
    def test_seed_has_bane_with_upcast_and_cha_save(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("bane", spells)
        s = spells["bane"]
        self.assertEqual(s["level"], 1)
        self.assertEqual(s["savingThrow"], "cha")
        self.assertEqual(s["maxTargets"], 3)
        self.assertEqual(s["upcast"]["mode"], "additional_targets")
        self.assertEqual(s["upcast"]["perLevel"], 1)


class BaneRollPenaltyTests(unittest.TestCase):
    def _bane_effect(self, effect_id: str = "eff-bane") -> dict:
        return {
            "id": effect_id,
            "kind": "spell_effect",
            "metadata": {
                "declarative_effect_group_id": "grp-bane",
                "source_spell_key": "bane",
                "source_spell_name": "Perdição",
                "declarative_effect": {
                    "type": "roll_dice_modifier",
                    "params": {"mode": "penalty", "roll_types": ["attack", "save"], "dice": "1d4"},
                },
            },
        }

    @patch("app.services.combat_service.condition_effects_predicates._roll_dice_expression", return_value=([3], 3))
    def test_penalty_sources_for_attack_and_save(self, _mock_roll):
        participant = {"active_effects": [self._bane_effect()]}
        attack_sources = get_roll_bonus_dice_sources(participant, roll_type="attack")
        save_sources = get_roll_bonus_dice_sources(participant, roll_type="save")
        self.assertEqual(len(attack_sources), 1)
        self.assertEqual(len(save_sources), 1)
        self.assertEqual(attack_sources[0]["modifier_type"], "roll_dice_modifier")
        self.assertEqual(attack_sources[0]["mode"], "penalty")
        self.assertEqual(attack_sources[0]["signed_total"], -3)
        self.assertEqual(attack_sources[0]["display_label"], "Perdição: -1d4")

    @patch("app.services.combat_service.condition_effects_predicates._roll_dice_expression", return_value=([4], 4))
    def test_penalty_recalculates_attack_success_to_failure(self, _mock_roll):
        participant = {"active_effects": [self._bane_effect()]}
        result = RollResult(
            event_id="atk-1",
            roll_type="attack",
            actor_kind="player",
            actor_ref_id="p1",
            actor_display_name="Lia",
            rolls=[11, 11],
            selected_roll=11,
            advantage_mode="normal",
            modifier_used=5,
            override_used=False,
            formula="1d20 + 5",
            total=16,
            target_ac=16,
            success=True,
            roll_source="system",
            timestamp="2026-01-01T00:00:00Z",
        )
        CombatService._apply_roll_bonus_dice_to_roll_result(participant=participant, roll_result=result, roll_type="attack")
        self.assertEqual(result.total, 12)
        self.assertFalse(result.success)

    @patch("app.services.combat_service.condition_effects_predicates._roll_dice_expression", return_value=([2], 2))
    def test_penalty_recalculates_save_success_to_failure(self, _mock_roll):
        participant = {"active_effects": [self._bane_effect()]}
        result = RollResult(
            event_id="save-1",
            roll_type="save",
            actor_kind="player",
            actor_ref_id="p1",
            actor_display_name="Lia",
            rolls=[12, 12],
            selected_roll=12,
            advantage_mode="normal",
            modifier_used=2,
            override_used=False,
            formula="1d20 + 2",
            total=14,
            ability="wisdom",
            dc=13,
            success=True,
            roll_source="system",
            timestamp="2026-01-01T00:00:00Z",
        )
        CombatService._apply_roll_bonus_dice_to_roll_result(participant=participant, roll_result=result, roll_type="save")
        self.assertEqual(result.total, 12)
        self.assertFalse(result.success)

    @patch("app.services.combat_service.condition_effects_predicates._roll_dice_expression", return_value=([4], 4))
    def test_not_applied_to_ability_or_skill_roll_types(self, _mock_roll):
        participant = {"active_effects": [self._bane_effect()]}
        self.assertEqual(get_roll_bonus_dice_sources(participant, roll_type="attack")[0]["signed_total"], -4)
        # Contract only supports attack/save in this issue.
        # No extra invocation path for ability/skill in this helper signature.


if __name__ == "__main__":
    unittest.main()
