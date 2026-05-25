from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import (
    resolve_armor_class_floor,
)
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.out_of_combat_cast import _SPECIAL_OOC_UTILITY_SPELLS, build_persisted_effects
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


def _first(value):
    mock = MagicMock()
    mock.first.return_value = value
    return mock


def _barkskin_effect() -> dict:
    return {
        "id": "fx-barkskin",
        "kind": "spell_effect",
        "metadata": {
            "source_spell_key": "barkskin",
            "armor_class_floor": 16,
            "ac_floor": 16,
            "sets_minimum_ac": True,
            "is_flat_bonus": False,
        },
    }


class BarkskinSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next((s for s in data.get("spells", []) if s.get("canonicalKey") == "barkskin"), None)

    def test_seed_contract(self):
        self.assertIsNotNone(self.entry)
        self.assertEqual(self.entry["level"], 2)
        self.assertEqual(self.entry["school"], "transmutation")
        self.assertIn("Druid", self.entry["classesJson"])
        self.assertIn("Ranger", self.entry["classesJson"])
        self.assertEqual(self.entry["rangeMeters"], 1.5)
        self.assertEqual(self.entry["durationSeconds"], 3600)
        self.assertTrue(self.entry["concentration"])
        self.assertEqual(self.entry["selectionType"], "creature")
        self.assertEqual(self.entry["attackType"], "none")
        self.assertTrue(self.entry.get("outOfCombatCastable"))
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")


class BarkskinSemanticsRegistryTests(unittest.TestCase):
    def test_targeting_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "barkskin"})
        self.assertEqual(sem.selection_type, "creature")
        self.assertEqual(sem.target_anchor, "selected_target")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.range_kind, "touch")
        self.assertEqual(sem.effect_timing, "persistent")

    def test_registry_entry(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("barkskin")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.default_mode, "utility")
        self.assertFalse(spec.requires_effect_payload)
        self.assertEqual(spec.handler_name, "_cast_barkskin_automation")

    def test_ooc_allowlist(self):
        self.assertIn("barkskin", _SPECIAL_OOC_UTILITY_SPELLS)


class BarkskinFloorHelperTests(unittest.TestCase):
    def test_floor_resolution(self):
        self.assertIsNone(resolve_armor_class_floor({"active_effects": []}))
        self.assertEqual(resolve_armor_class_floor({"active_effects": [_barkskin_effect()]}), 16)
        self.assertEqual(
            resolve_armor_class_floor(
                {
                    "active_effects": [
                        _barkskin_effect(),
                        {
                            "id": "fx-other",
                            "kind": "spell_effect",
                            "metadata": {
                                "sets_minimum_ac": True,
                                "armor_class_floor": 14,
                            },
                        },
                    ]
                }
            ),
            16,
        )


class BarkskinAcIntegrationTests(unittest.TestCase):
    def test_player_ac_13_with_barkskin_becomes_effective_16_without_mutating_state(self):
        state_json = {
            "abilities": {"dexterity": 16},  # base AC 13
            "spellcasting": {},
            "armorClass": 13,
        }
        state_model = SimpleNamespace(state_json=state_json)
        db = MagicMock()
        db.exec.return_value = _first(state_model)
        combat_state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "u1",
                    "kind": "player",
                    "active_effects": [_barkskin_effect()],
                }
            ],
        )

        _, ac, *_ = CombatService._get_stats(
            db, "u1", "player", "s1", combat_state=combat_state
        )
        self.assertEqual(ac, 16)
        self.assertEqual(state_model.state_json["armorClass"], 13)

    def test_entity_ac_13_with_barkskin_becomes_effective_16(self):
        session_entity = SimpleNamespace(campaign_entity_id="npc-1", overrides={"armorClass": 13})
        campaign_entity = SimpleNamespace(abilities={}, spellcasting={}, armor_class=13)
        db = MagicMock()
        db.exec.side_effect = [_first(session_entity), _first(campaign_entity)]
        combat_state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "e1",
                    "ref_id": "entity-1",
                    "kind": "session_entity",
                    "active_effects": [_barkskin_effect()],
                }
            ],
        )

        _, ac, *_ = CombatService._get_stats(
            db, "entity-1", "session_entity", "s1", combat_state=combat_state
        )
        self.assertEqual(ac, 16)

    def test_ac_18_with_barkskin_stays_18(self):
        state_json = {
            "abilities": {"dexterity": 18},
            "equippedArmor": {"armorType": "light", "baseAC": 14},
            "spellcasting": {},
        }  # 14 + 4 = 18
        state_model = SimpleNamespace(state_json=state_json)
        db = MagicMock()
        db.exec.return_value = _first(state_model)
        combat_state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "u1",
                    "kind": "player",
                    "active_effects": [_barkskin_effect()],
                }
            ],
        )

        _, ac, *_ = CombatService._get_stats(
            db, "u1", "player", "s1", combat_state=combat_state
        )
        self.assertEqual(ac, 18)

    def test_ac_15_plus_bonus_2_with_barkskin_is_17_not_16_or_19(self):
        state_json = {
            "abilities": {"dexterity": 14},  # +2
            "equippedArmor": {"armorType": "light", "baseAC": 13},  # 15
            "miscACBonus": 2,  # 17
            "spellcasting": {},
        }
        state_model = SimpleNamespace(state_json=state_json)
        db = MagicMock()
        db.exec.return_value = _first(state_model)
        combat_state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "u1",
                    "kind": "player",
                    "active_effects": [_barkskin_effect()],
                }
            ],
        )

        _, ac, *_ = CombatService._get_stats(
            db, "u1", "player", "s1", combat_state=combat_state
        )
        self.assertEqual(ac, 17)


class BarkskinOocPersistedShapeTests(unittest.TestCase):
    def test_build_persisted_effects_shape(self):
        spell = SimpleNamespace(
            canonical_key="barkskin",
            name_pt="Pele de Árvore",
            name_en="Barkskin",
            concentration=True,
            effects_json=None,
        )
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u2",
            variant_key=None,
            game_time_seconds=10,
        )
        self.assertEqual(len(effects), 1)
        md = effects[0]["metadata"]
        self.assertEqual(md["source_spell_key"], "barkskin")
        self.assertTrue(md["concentration"])
        self.assertEqual(md["armor_class_floor"], 16)
        self.assertTrue(md["sets_minimum_ac"])
        self.assertFalse(md["is_flat_bonus"])


if __name__ == "__main__":
    unittest.main()
