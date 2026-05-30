from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.roll import RollResult
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import get_roll_bonus_dice_sources


def _guidance_effect(effect_id: str = "eff-guid") -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "metadata": {
            "declarative_effect_group_id": "grp-guid",
            "source_spell_key": "guidance",
            "source_spell_name": "Orientação",
            "concentration": True,
            "concentration_group": "grp-guid",
            "declarative_effect": {
                "type": "roll_dice_modifier",
                "params": {
                    "mode": "bonus",
                    "roll_types": ["ability", "skill"],
                    "dice": "1d4",
                    "consume_on_apply": True,
                },
            },
        },
    }


class GuidanceSeedTests(unittest.TestCase):
    def test_seed_has_guidance_roll_dice_modifier_consumable(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("guidance", spells)
        s = spells["guidance"]
        self.assertEqual(s["level"], 0)
        eff = s.get("effects", [])[0]
        self.assertEqual(eff.get("type"), "roll_dice_modifier")
        self.assertEqual(eff.get("params", {}).get("roll_types"), ["ability", "skill"])
        self.assertTrue(eff.get("params", {}).get("consume_on_apply"))


class GuidanceRuntimeTests(unittest.TestCase):
    @patch("app.services.combat_service.condition_effects_predicates_parts.predicates_spell_metadata._roll_dice_expression", return_value=3)
    def test_applies_to_ability_and_consumes_effect_id_only(self, _mock_roll):
        participant = {"id": "p1", "kind": "player", "active_effects": [_guidance_effect(), {"id": "other", "kind": "spell_effect", "metadata": {"source_spell_key": "bless", "declarative_effect": {"type": "roll_dice_modifier", "params": {"mode": "bonus", "roll_types": ["attack", "save"], "dice": "1d4"}}}}]}
        state = CombatState(id="c1", session_id="s1", phase=CombatPhase.active, round=1, current_turn_index=0, participants=[participant], use_map=False)
        result = RollResult(event_id="e1", roll_type="ability", actor_kind="player", actor_ref_id="p1", actor_display_name="Lia", rolls=[10, 10], selected_roll=10, advantage_mode="normal", modifier_used=2, override_used=False, formula="1d20 + 2", total=12, ability="wisdom", dc=12, success=True, roll_source="system", timestamp="2026-01-01T00:00:00Z")
        consumed = CombatService._apply_roll_bonus_dice_to_roll_result(participant=participant, roll_result=result, roll_type="ability", state=state)
        self.assertEqual(result.total, 15)
        self.assertEqual(consumed, ["eff-guid"])
        self.assertEqual(len(participant.get("active_effects", [])), 1)
        self.assertEqual(participant["active_effects"][0]["id"], "other")
        self.assertEqual(result.check_modifier_sources[0]["display_label"], "Orientação: +1d4")

    @patch("app.services.combat_service.condition_effects_predicates_parts.predicates_spell_metadata._roll_dice_expression", return_value=4)
    def test_not_applied_to_attack_and_not_consumed(self, _mock_roll):
        participant = {"id": "p1", "kind": "player", "active_effects": [_guidance_effect()]}
        result = RollResult(event_id="e2", roll_type="attack", actor_kind="player", actor_ref_id="p1", actor_display_name="Lia", rolls=[10, 10], selected_roll=10, advantage_mode="normal", modifier_used=4, override_used=False, formula="1d20 + 4", total=14, target_ac=15, success=False, roll_source="system", timestamp="2026-01-01T00:00:00Z")
        consumed = CombatService._apply_roll_bonus_dice_to_roll_result(participant=participant, roll_result=result, roll_type="attack")
        self.assertEqual(consumed, [])
        self.assertEqual(result.total, 14)
        self.assertEqual(len(participant.get("active_effects", [])), 1)

    @patch("app.services.combat_service.condition_effects_predicates_parts.predicates_spell_metadata._roll_dice_expression", return_value=2)
    def test_invalid_then_valid_roll_consumes_only_on_valid(self, _mock_roll):
        participant = {"id": "p1", "kind": "player", "active_effects": [_guidance_effect()]}
        atk_sources = get_roll_bonus_dice_sources(participant, roll_type="attack")
        self.assertEqual(atk_sources, [])
        self.assertEqual(len(participant.get("active_effects", [])), 1)

        result = RollResult(event_id="e3", roll_type="skill", actor_kind="player", actor_ref_id="p1", actor_display_name="Lia", rolls=[9, 9], selected_roll=9, advantage_mode="normal", modifier_used=1, override_used=False, formula="1d20 + 1", total=10, skill="perception", dc=11, success=False, roll_source="system", timestamp="2026-01-01T00:00:00Z")
        consumed = CombatService._apply_roll_bonus_dice_to_roll_result(participant=participant, roll_result=result, roll_type="skill")
        self.assertEqual(result.total, 12)
        self.assertTrue(result.success)
        self.assertEqual(consumed, ["eff-guid"])
        self.assertEqual(len(participant.get("active_effects", [])), 0)


if __name__ == "__main__":
    unittest.main()
