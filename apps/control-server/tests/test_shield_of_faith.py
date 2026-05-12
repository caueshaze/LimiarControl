from __future__ import annotations

import json
import os
import unittest
from copy import deepcopy

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.session_state_finalize import calculate_player_armor_class_from_state


def _sof_effect(effect_id: str = "sof-1", group: str = "grp-sof", source_participant_id: str = "caster") -> dict:
    return {
        "id": effect_id,
        "kind": "temp_ac_bonus",
        "numeric_value": 2,
        "duration_type": "manual",
        "metadata": {
            "concentration": True,
            "concentration_group": group,
            "source_spell_key": "shield_of_faith",
            "declarative_effect": {
                "type": "modify_stat",
                "target": "selected_target",
                "params": {"stat": "temp_ac_bonus", "value": 2},
            },
        },
        "source_participant_id": source_participant_id,
    }


def _mage_armor_effect(effect_id: str = "ma-1") -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "duration_type": "timed",
        "metadata": {
            "source_spell_key": "mage_armor",
            "declarative_effect": {
                "type": "armor_class_formula",
                "target": "selected_target",
                "params": {"base_value": 13, "ability": "dexterity", "requires_unarmored": True},
            },
        },
    }


class ShieldOfFaithSeedTests(unittest.TestCase):
    def test_seed_has_canonical_temp_ac_bonus_contract(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        self.assertIn("shield_of_faith", spells)
        s = spells["shield_of_faith"]
        self.assertEqual(s["level"], 1)
        self.assertEqual(s["school"], "abjuration")
        self.assertEqual(s["castingTimeType"], "bonus_action")
        self.assertEqual(s["rangeMeters"], 18)
        self.assertTrue(s["concentration"])
        self.assertEqual(s["selectionType"], "creature")
        eff = s.get("effects", [])[0]
        self.assertEqual(eff.get("type"), "modify_stat")
        self.assertEqual((eff.get("params") or {}).get("stat"), "temp_ac_bonus")
        self.assertEqual((eff.get("params") or {}).get("value"), 2)
        self.assertNotEqual(eff.get("type"), "armor_class_bonus")


class ShieldOfFaithAcCompositionTests(unittest.TestCase):
    def test_mage_armor_base_plus_shield_of_faith_bonus(self):
        state = {
            "abilities": {"dexterity": 16},
            "active_spell_effects": [_mage_armor_effect(), _sof_effect()],
        }
        ac = calculate_player_armor_class_from_state(state)
        self.assertEqual(ac, 18)  # 13 + 3 + 2

    def test_armor_base_plus_shield_item_plus_shield_of_faith(self):
        state = {
            "abilities": {"dexterity": 16},
            "equippedArmor": {"armorType": "light", "baseAC": 11, "allowsDex": True},
            "equippedShield": {"bonus": 2},
            "active_spell_effects": [_sof_effect()],
        }
        ac = calculate_player_armor_class_from_state(state)
        self.assertEqual(ac, 18)  # (11+3) +2 shield item +2 SoF

    def test_shield_of_faith_is_additive_not_base_formula(self):
        base = {
            "abilities": {"dexterity": 14},
            "equippedArmor": {"armorType": "light", "baseAC": 11, "allowsDex": True},
            "active_spell_effects": [],
        }
        with_sof = deepcopy(base)
        with_sof["active_spell_effects"] = [_sof_effect()]
        self.assertEqual(calculate_player_armor_class_from_state(base), 13)
        self.assertEqual(calculate_player_armor_class_from_state(with_sof), 15)


class ShieldOfFaithConcentrationLifecycleTests(unittest.TestCase):
    def test_clearing_concentration_removes_effect_and_no_orphan_group(self):
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {"id": "caster", "ref_id": "u1", "kind": "player", "display_name": "Caster", "active_effects": []},
                {"id": "target", "ref_id": "u2", "kind": "player", "display_name": "Target", "active_effects": [_sof_effect()]},
            ],
            use_map=False,
        )
        result = CombatService._clear_concentration_for_source(state, source_participant_id="caster")
        removed = result.get("removed_effects", [])
        self.assertTrue(any((e.get("metadata") or {}).get("source_spell_key") == "shield_of_faith" for e in removed))
        self.assertEqual(state.participants[1]["active_effects"], [])
        # no group should remain on active effects after removal
        for p in state.participants:
            for e in p.get("active_effects", []):
                self.assertNotEqual((e.get("metadata") or {}).get("concentration_group"), "grp-sof")


if __name__ == "__main__":
    unittest.main()
