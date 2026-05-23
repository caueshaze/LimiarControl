"""Tests for Enhance Ability (Aprimorar Habilidade).

Covers:
- Seed contract: level=2, concentration, outOfCombatCastable=True, 6 variants
- Each variant applies correct ability advantage
- Bears Endurance: grant_temp_hp(2d6)
- Bull's Strength: carrying_capacity_multiplier(2)
- Cat's Grace: fall_damage_immunity_threshold(6m)
- Owl's Wisdom: passive_skill_bonus(perception, +5)
- Eagles Splendor / Fox's Cunning: advantage on CHA / INT
- Advantage predicate resolves correctly from active_effects
"""

from __future__ import annotations

import json
import unittest

from app.services.combat_service.condition_effects_predicates import (
    get_carrying_capacity_multiplier,
    get_fall_damage_immunity_threshold,
    get_passive_skill_bonus,
    resolve_check_advantage_mode,
)


def _participant_with_advantage(ability: str) -> dict:
    return {
        "id": "p1",
        "ref_id": "target",
        "active_effects": [
            {
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "enhance_ability",
                    "declarative_effect": {
                        "type": "advantage_on_checks",
                        "params": {"ability": ability, "against": "any"},
                    },
                },
            }
        ],
    }


def _participant_with_carrying_multiplier(multiplier: float) -> dict:
    return {
        "id": "p1",
        "ref_id": "target",
        "active_effects": [
            {
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "enhance_ability",
                    "declarative_effect": {
                        "type": "carrying_capacity_multiplier",
                        "params": {"multiplier": multiplier},
                    },
                },
            }
        ],
    }


def _participant_with_fall_immunity(max_distance: float) -> dict:
    return {
        "id": "p1",
        "ref_id": "target",
        "active_effects": [
            {
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "enhance_ability",
                    "declarative_effect": {
                        "type": "fall_damage_immunity_threshold",
                        "params": {"max_distance_meters": max_distance},
                    },
                },
            }
        ],
    }


def _participant_with_passive_skill_bonus(skill: str, bonus: int) -> dict:
    return {
        "id": "p1",
        "ref_id": "target",
        "active_effects": [
            {
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "enhance_ability",
                    "declarative_effect": {
                        "type": "passive_skill_bonus",
                        "params": {"skill": skill, "bonus": bonus},
                    },
                },
            }
        ],
    }


# ---------------------------------------------------------------------------
# Seed tests
# ---------------------------------------------------------------------------

class EnhanceAbilitySeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.seed_paths import resolve_base_seed_path
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "enhance_ability"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "enhance_ability not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 2)
        self.assertEqual(e["school"], "transmutation")
        self.assertTrue(e["concentration"])
        self.assertEqual(e["attackType"], "none")

    def test_out_of_combat_castable(self):
        self.assertTrue(self.entry.get("outOfCombatCastable"))
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")

    def test_upcast_mode_additional_targets(self):
        up = self.entry.get("upcast")
        self.assertIsNotNone(up)
        self.assertEqual(up["mode"], "additional_targets")

    def test_has_six_variants(self):
        variants = self.entry.get("variants") or []
        keys = {v["key"] for v in variants}
        expected = {"bears_endurance", "bulls_strength", "cats_grace", "eagles_splendor", "foxs_cunning", "owls_wisdom"}
        self.assertEqual(keys, expected)

    def test_bears_endurance_has_grant_temp_hp(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        types = [e["type"] for e in variants["bears_endurance"]["effects"]]
        self.assertIn("grant_temp_hp", types)
        self.assertIn("advantage_on_checks", types)

    def test_bulls_strength_has_carrying_capacity_multiplier(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        types = [e["type"] for e in variants["bulls_strength"]["effects"]]
        self.assertIn("carrying_capacity_multiplier", types)

    def test_cats_grace_has_fall_damage_immunity(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        types = [e["type"] for e in variants["cats_grace"]["effects"]]
        self.assertIn("fall_damage_immunity_threshold", types)

    def test_owls_wisdom_has_passive_perception_bonus(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        types = [e["type"] for e in variants["owls_wisdom"]["effects"]]
        self.assertIn("passive_skill_bonus", types)
        bonus_effect = next(e for e in variants["owls_wisdom"]["effects"] if e["type"] == "passive_skill_bonus")
        self.assertEqual(bonus_effect["params"]["skill"], "perception")
        self.assertEqual(bonus_effect["params"]["bonus"], 5)

    def test_each_variant_has_advantage_on_checks(self):
        variants = {v["key"]: v for v in (self.entry.get("variants") or [])}
        for key, variant in variants.items():
            types = [e["type"] for e in variant["effects"]]
            self.assertIn("advantage_on_checks", types, f"Variant {key} missing advantage_on_checks")


# ---------------------------------------------------------------------------
# Advantage predicate per variant
# ---------------------------------------------------------------------------

class EnhanceAbilityAdvantageTests(unittest.TestCase):
    def _mode(self, ability: str) -> str:
        return resolve_check_advantage_mode(
            _participant_with_advantage(ability),
            ability,
        )

    def test_bears_endurance_grants_con_advantage(self):
        self.assertEqual(self._mode("constitution"), "advantage")

    def test_bulls_strength_grants_str_advantage(self):
        self.assertEqual(self._mode("strength"), "advantage")

    def test_cats_grace_grants_dex_advantage(self):
        self.assertEqual(self._mode("dexterity"), "advantage")

    def test_eagles_splendor_grants_cha_advantage(self):
        self.assertEqual(self._mode("charisma"), "advantage")

    def test_foxs_cunning_grants_int_advantage(self):
        self.assertEqual(self._mode("intelligence"), "advantage")

    def test_owls_wisdom_grants_wis_advantage(self):
        self.assertEqual(self._mode("wisdom"), "advantage")

    def test_no_advantage_on_unrelated_ability(self):
        p = _participant_with_advantage("constitution")
        mode = resolve_check_advantage_mode(p, "dexterity")
        self.assertEqual(mode, "normal")

    def test_no_effects_gives_normal_mode(self):
        p = {"id": "p1", "active_effects": []}
        mode = resolve_check_advantage_mode(p, "strength")
        self.assertEqual(mode, "normal")


# ---------------------------------------------------------------------------
# Secondary effect predicates
# ---------------------------------------------------------------------------

class EnhanceAbilitySecondaryEffectsTests(unittest.TestCase):
    def test_bulls_strength_doubles_carrying_capacity(self):
        p = _participant_with_carrying_multiplier(2.0)
        self.assertEqual(get_carrying_capacity_multiplier(p), 2.0)

    def test_no_bulls_strength_gives_default_multiplier(self):
        p = {"id": "p1", "active_effects": []}
        self.assertEqual(get_carrying_capacity_multiplier(p), 1.0)

    def test_cats_grace_grants_fall_immunity_6m(self):
        p = _participant_with_fall_immunity(6.0)
        threshold, _ = get_fall_damage_immunity_threshold(p)
        self.assertEqual(threshold, 6.0)

    def test_no_cats_grace_gives_no_fall_immunity(self):
        p = {"id": "p1", "active_effects": []}
        threshold, _ = get_fall_damage_immunity_threshold(p)
        self.assertIsNone(threshold)

    def test_owls_wisdom_grants_perception_bonus(self):
        p = _participant_with_passive_skill_bonus("perception", 5)
        self.assertEqual(get_passive_skill_bonus(p, "perception"), 5)

    def test_owls_wisdom_does_not_affect_other_skills(self):
        p = _participant_with_passive_skill_bonus("perception", 5)
        self.assertEqual(get_passive_skill_bonus(p, "stealth"), 0)
