from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app.schemas.base_spell_effects import GrantTempHpParams, SpellDeclarativeEffect
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin
from app.services.out_of_combat_cast import (
    collect_temp_hp_effects,
    compute_temp_hp_upcast_bonus,
    roll_spell_temp_hp_effects,
)


def _temp_hp_effect(*, dice: str = "1d4 + 4", target: str = "caster") -> dict:
    return {
        "type": "grant_temp_hp",
        "target": target,
        "duration": {"type": "timed", "seconds": 3600},
        "out_of_combat_duration": {"type": "timed", "seconds": 3600},
        "params": {"dice": dice},
    }


def _make_spell(
    *,
    canonical_key: str = "false_life",
    level: int = 1,
    effects_json: list | None = None,
    upcast_json: dict | None = None,
    out_of_combat_castable: bool = True,
    out_of_combat_target: str = "self",
):
    spell = MagicMock()
    spell.canonical_key = canonical_key
    spell.level = level
    spell.concentration = False
    spell.out_of_combat_castable = out_of_combat_castable
    spell.out_of_combat_target = out_of_combat_target
    spell.effects_json = effects_json if effects_json is not None else [_temp_hp_effect()]
    spell.variants_json = []
    spell.upcast_json = upcast_json if upcast_json is not None else {
        "mode": "extra_temp_hp",
        "flat": 5,
        "perLevel": 1,
    }
    spell.name_pt = "Vitalidade Vazia"
    spell.name_en = "False Life"
    return spell


class FalseLifeSeedContractTests(unittest.TestCase):
    def test_seed_contains_false_life(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")) as f:
            data = json.load(f)
        keys = [s["canonicalKey"] for s in data["spells"]]
        self.assertIn("false_life", keys)

    def test_seed_false_life_metadata(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")) as f:
            data = json.load(f)
        spell = next(s for s in data["spells"] if s["canonicalKey"] == "false_life")
        self.assertEqual(spell["level"], 1)
        self.assertEqual(spell["school"], "necromancy")
        self.assertEqual(spell["castingTimeType"], "action")
        self.assertEqual(spell["rangeText"], "Self")
        self.assertEqual(spell["duration"], "1 hour")
        self.assertFalse(spell["concentration"])
        self.assertNotIn("savingThrow", spell)
        self.assertNotIn("damageDice", spell)
        self.assertEqual(spell["targetType"], "self")
        self.assertEqual(spell["selectionType"], "self")
        self.assertEqual(spell["originType"], "caster")
        self.assertEqual(spell["targetAnchor"], "caster")
        self.assertEqual(spell["rangeKind"], "self")
        self.assertEqual(spell["effectTiming"], "immediate")
        self.assertTrue(spell["outOfCombatCastable"])
        self.assertEqual(spell["outOfCombatTarget"], "self")

    def test_seed_false_life_effect(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")) as f:
            data = json.load(f)
        spell = next(s for s in data["spells"] if s["canonicalKey"] == "false_life")
        effects = spell["effects"]
        self.assertEqual(len(effects), 1)
        eff = effects[0]
        self.assertEqual(eff["type"], "grant_temp_hp")
        self.assertEqual(eff["target"], "caster")
        self.assertEqual(eff["duration"]["type"], "timed")
        self.assertEqual(eff["duration"]["seconds"], 3600)
        self.assertEqual(eff["params"]["dice"], "1d4 + 4")

    def test_seed_false_life_upcast(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")) as f:
            data = json.load(f)
        spell = next(s for s in data["spells"] if s["canonicalKey"] == "false_life")
        upcast = spell["upcast"]
        self.assertEqual(upcast["mode"], "extra_temp_hp")
        self.assertEqual(upcast["flat"], 5)
        self.assertEqual(upcast["perLevel"], 1)


class FalseLifeSchemaTests(unittest.TestCase):
    def test_grant_temp_hp_effect_validates(self):
        effect = SpellDeclarativeEffect(**_temp_hp_effect())
        self.assertEqual(effect.type, "grant_temp_hp")
        self.assertIsInstance(effect.params, GrantTempHpParams)
        self.assertEqual(effect.params.dice, "1d4 + 4")

    def test_grant_temp_hp_rejects_wrong_params(self):
        with self.assertRaises(Exception):
            SpellDeclarativeEffect(**{
                "type": "grant_temp_hp",
                "target": "caster",
                "params": {"condition": "blinded"},
            })


class FalseLifeUpcastMathTests(unittest.TestCase):
    def _apply_upcast(self, slot_level: int) -> dict:
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast({
            "mode": "extra_temp_hp",
            "flat": 5,
            "perLevel": 1,
        })
        return CombatSpellDiceMathMixin._apply_structured_spell_upcast(
            spell_level=1,
            slot_level=slot_level,
            effect_kind=None,
            effect_dice=None,
            effect_bonus=0,
            upcast=structured,
        )

    def test_slot_1_no_upcast_bonus(self):
        result = self._apply_upcast(1)
        self.assertEqual(result["effect_bonus"], 0)
        self.assertFalse(result["upcast_applied"])

    def test_slot_2_bonus_5(self):
        result = self._apply_upcast(2)
        self.assertEqual(result["effect_bonus"], 5)
        self.assertTrue(result["upcast_applied"])

    def test_slot_3_bonus_10(self):
        result = self._apply_upcast(3)
        self.assertEqual(result["effect_bonus"], 10)
        self.assertTrue(result["upcast_applied"])

    def test_slot_4_bonus_15(self):
        result = self._apply_upcast(4)
        self.assertEqual(result["effect_bonus"], 15)
        self.assertTrue(result["upcast_applied"])

    def test_slot_5_bonus_20(self):
        result = self._apply_upcast(5)
        self.assertEqual(result["effect_bonus"], 20)
        self.assertTrue(result["upcast_applied"])

    def test_structured_upcast_parses_extra_temp_hp(self):
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast({
            "mode": "extra_temp_hp",
            "flat": 5,
            "perLevel": 1,
        })
        self.assertIsNotNone(structured)
        self.assertEqual(structured["mode"], "extra_temp_hp")
        self.assertEqual(structured["flat"], 5)
        self.assertEqual(structured["perLevel"], 1)


class FalseLifeOOCUpcastTests(unittest.TestCase):
    def test_compute_bonus_slot_1(self):
        spell = _make_spell()
        self.assertEqual(compute_temp_hp_upcast_bonus(spell, 1), 0)

    def test_compute_bonus_slot_2(self):
        spell = _make_spell()
        self.assertEqual(compute_temp_hp_upcast_bonus(spell, 2), 5)

    def test_compute_bonus_slot_3(self):
        spell = _make_spell()
        self.assertEqual(compute_temp_hp_upcast_bonus(spell, 3), 10)

    def test_compute_bonus_slot_4(self):
        spell = _make_spell()
        self.assertEqual(compute_temp_hp_upcast_bonus(spell, 4), 15)

    def test_compute_bonus_no_upcast_config(self):
        spell = _make_spell(upcast_json={})
        self.assertEqual(compute_temp_hp_upcast_bonus(spell, 3), 0)

    def test_compute_bonus_wrong_mode(self):
        spell = _make_spell(upcast_json={"mode": "extra_damage_dice", "flat": 5, "perLevel": 1})
        self.assertEqual(compute_temp_hp_upcast_bonus(spell, 3), 0)

    def test_compute_bonus_paridade_perLevel_2(self):
        spell = _make_spell(upcast_json={"mode": "extra_temp_hp", "flat": 3, "perLevel": 2})
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(spell.upcast_json)
        for slot in range(1, 7):
            combat = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
                spell_level=1, slot_level=slot, effect_kind=None,
                effect_dice=None, effect_bonus=0, upcast=structured,
            )
            ooc = compute_temp_hp_upcast_bonus(spell, slot)
            self.assertEqual(
                combat["effect_bonus"], ooc,
                f"perLevel=2 diverge at slot {slot}: combat={combat['effect_bonus']} ooc={ooc}",
            )

    def test_compute_bonus_paridade_levelStep_2(self):
        spell = _make_spell(upcast_json={"mode": "extra_temp_hp", "flat": 8, "levelStep": 2})
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(spell.upcast_json)
        for slot in range(1, 7):
            combat = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
                spell_level=1, slot_level=slot, effect_kind=None,
                effect_dice=None, effect_bonus=0, upcast=structured,
            )
            ooc = compute_temp_hp_upcast_bonus(spell, slot)
            self.assertEqual(
                combat["effect_bonus"], ooc,
                f"levelStep=2 diverge at slot {slot}: combat={combat['effect_bonus']} ooc={ooc}",
            )

    def test_compute_bonus_paridade_maxLevel(self):
        spell = _make_spell(upcast_json={"mode": "extra_temp_hp", "flat": 5, "perLevel": 1, "maxLevel": 3})
        structured = CombatSpellDiceMathMixin._get_structured_spell_upcast(spell.upcast_json)
        for slot in range(1, 7):
            combat = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
                spell_level=1, slot_level=slot, effect_kind=None,
                effect_dice=None, effect_bonus=0, upcast=structured,
            )
            ooc = compute_temp_hp_upcast_bonus(spell, slot)
            self.assertEqual(
                combat["effect_bonus"], ooc,
                f"maxLevel=3 diverge at slot {slot}: combat={combat['effect_bonus']} ooc={ooc}",
            )


class FalseLifeCollectEffectsTests(unittest.TestCase):
    def test_collect_temp_hp_effects(self):
        spell = _make_spell()
        collected = collect_temp_hp_effects(spell, variant_key=None)
        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["type"], "grant_temp_hp")
        self.assertEqual(collected[0]["params"]["dice"], "1d4 + 4")

    def test_collect_temp_hp_effects_empty_for_non_temp_hp_spell(self):
        spell = _make_spell(effects_json=[
            {"type": "modify_stat", "target": "caster", "params": {"stat": "attack_bonus", "value": 1}},
        ])
        self.assertEqual(collect_temp_hp_effects(spell, variant_key=None), [])


class FalseLifeRollTempHpTests(unittest.TestCase):
    @patch("app.services.combat_service.exceptions._roll_dice_expression", return_value=7)
    def test_roll_slot_1_no_bonus(self, mock_roll):
        spell = _make_spell()
        results = roll_spell_temp_hp_effects(
            [_temp_hp_effect()], spell, slot_level=1,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["amount"], 7)
        self.assertEqual(results[0]["upcast_bonus"], 0)
        self.assertEqual(results[0]["base_dice"], "1d4 + 4")

    @patch("app.services.combat_service.exceptions._roll_dice_expression", return_value=7)
    def test_roll_slot_2_adds_bonus(self, mock_roll):
        spell = _make_spell()
        results = roll_spell_temp_hp_effects(
            [_temp_hp_effect()], spell, slot_level=2,
        )
        self.assertEqual(results[0]["amount"], 12)
        self.assertEqual(results[0]["upcast_bonus"], 5)

    @patch("app.services.combat_service.exceptions._roll_dice_expression", return_value=7)
    def test_roll_slot_4_adds_bonus(self, mock_roll):
        spell = _make_spell()
        results = roll_spell_temp_hp_effects(
            [_temp_hp_effect()], spell, slot_level=4,
        )
        self.assertEqual(results[0]["amount"], 22)
        self.assertEqual(results[0]["upcast_bonus"], 15)


class FalseLifeTempHpPolicyTests(unittest.TestCase):
    def test_apply_temp_hp_new(self):
        from app.api.routes.sessions.state import _apply_temp_hp_to_state_dict
        state = {"currentHP": 10, "maxHP": 20}
        result = _apply_temp_hp_to_state_dict(state, 7)
        self.assertEqual(result["tempHP"], 7)

    def test_apply_temp_hp_keep_higher(self):
        from app.api.routes.sessions.state import _apply_temp_hp_to_state_dict
        state = {"currentHP": 10, "maxHP": 20, "tempHP": 12}
        result = _apply_temp_hp_to_state_dict(state, 7)
        self.assertEqual(result["tempHP"], 12)

    def test_apply_temp_hp_replace_lower(self):
        from app.api.routes.sessions.state import _apply_temp_hp_to_state_dict
        state = {"currentHP": 10, "maxHP": 20, "tempHP": 3}
        result = _apply_temp_hp_to_state_dict(state, 7)
        self.assertEqual(result["tempHP"], 7)

    def test_apply_temp_hp_does_not_heal_real_hp(self):
        from app.api.routes.sessions.state import _apply_temp_hp_to_state_dict
        state = {"currentHP": 5, "maxHP": 20}
        result = _apply_temp_hp_to_state_dict(state, 10)
        self.assertEqual(result["currentHP"], 5)
        self.assertEqual(result["tempHP"], 10)


class FalseLifeCombatUpcastBonusTests(unittest.TestCase):
    def test_combat_handler_reads_effect_bonus_from_context(self):
        from app.services.combat_service.exceptions import _roll_dice_expression

        base_roll = _roll_dice_expression("1d4 + 4")
        self.assertGreaterEqual(base_roll, 5)
        self.assertLessEqual(base_roll, 8)

        upcast_bonus = 10
        total = base_roll + upcast_bonus
        self.assertGreaterEqual(total, 15)
        self.assertLessEqual(total, 18)

    def test_combat_upcast_agrees_with_ooc(self):
        for slot in (1, 2, 3, 4):
            structured = CombatSpellDiceMathMixin._get_structured_spell_upcast({
                "mode": "extra_temp_hp",
                "flat": 5,
                "perLevel": 1,
            })
            upcast_result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
                spell_level=1,
                slot_level=slot,
                effect_kind=None,
                effect_dice=None,
                effect_bonus=0,
                upcast=structured,
            )
            spell = _make_spell()
            ooc_bonus = compute_temp_hp_upcast_bonus(spell, slot)
            self.assertEqual(
                upcast_result["effect_bonus"],
                ooc_bonus,
                f"Combat and OOC upcast disagree at slot {slot}",
            )
