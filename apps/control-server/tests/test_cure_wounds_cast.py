"""Tests for Cure Wounds (Curar Ferimentos) out-of-combat automation (issue #303).

Covers:
- HealParams schema validation
- heal effect type correctly registered and rejected for wrong params
- build_persisted_effects returns [] for heal (no active_spell_effects created)
- collect_heal_effects extracts params
- compute_heal_dice_with_upcast scales correctly
- resolve_spellcasting_modifier reads from state_json
- roll_spell_heal_effects rolls and sums correctly
- HP application: heals, caps at max, handles wild shape pass-through
- Upcast: 1→2→3 slot levels produce correct dice counts
- Goodberry regression: still creates consumable, not immediate heal
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from app.schemas.base_spell_effects import HealParams, SpellDeclarativeEffect
from app.services.out_of_combat_cast import (
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
    collect_heal_effects,
    compute_heal_dice_with_upcast,
    resolve_spellcasting_modifier,
    roll_spell_heal_effects,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _heal_effect(
    *,
    dice: str = "1d8",
    ability_modifier: str | None = "spellcasting",
    target: str = "selected_target",
) -> dict:
    return {"type": "heal", "target": target, "params": {"dice": dice, "ability_modifier": ability_modifier}}


def _make_spell(
    *,
    canonical_key: str = "cure_wounds",
    level: int = 1,
    effects_json: list | None = None,
    upcast_json: dict | None = None,
    out_of_combat_castable: bool = True,
    out_of_combat_target: str = "self_or_ally",
):
    spell = MagicMock()
    spell.canonical_key = canonical_key
    spell.level = level
    spell.concentration = False
    spell.out_of_combat_castable = out_of_combat_castable
    spell.out_of_combat_target = out_of_combat_target
    spell.effects_json = effects_json if effects_json is not None else [_heal_effect()]
    spell.variants_json = []
    spell.upcast_json = upcast_json if upcast_json is not None else {
        "mode": "extra_heal_dice",
        "dice": "1d8",
        "perLevel": 1,
    }
    spell.name_pt = "Curar Ferimentos"
    spell.name_en = "Cure Wounds"
    return spell


def _slot_state(*, slot_level: int = 1, used: int = 0, max_slots: int = 4) -> dict:
    return {"spellcasting": {"slots": {str(slot_level): {"used": used, "max": max_slots}}}}


def _caster_state(
    *,
    current_hp: int = 8,
    max_hp: int = 14,
    spellcasting_ability: str = "wisdom",
    wisdom: int = 16,
) -> dict:
    return {
        "currentHP": current_hp,
        "maxHP": max_hp,
        "abilities": {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": wisdom, "charisma": 10,
        },
        "spellcasting": {
            "ability": spellcasting_ability,
            "slots": {"1": {"used": 0, "max": 4}},
        },
    }


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class HealParamsSchemaTests(unittest.TestCase):
    def test_heal_effect_validates_with_dice_and_modifier(self):
        effect = SpellDeclarativeEffect(**_heal_effect())
        self.assertEqual(effect.type, "heal")
        self.assertIsInstance(effect.params, HealParams)
        self.assertEqual(effect.params.dice, "1d8")
        self.assertEqual(effect.params.ability_modifier, "spellcasting")

    def test_heal_effect_validates_without_ability_modifier(self):
        # ability_modifier must be explicitly null (not omitted) to distinguish from GrantTempHpParams
        effect = SpellDeclarativeEffect(**{
            "type": "heal",
            "target": "selected_target",
            "params": {"dice": "1d8", "ability_modifier": None},
        })
        self.assertIsNone(effect.params.ability_modifier)

    def test_heal_params_rejects_extra_fields(self):
        with self.assertRaises(ValidationError):
            HealParams(dice="1d8", ability_modifier="spellcasting", unknown=True)

    def test_heal_effect_rejects_wrong_params(self):
        with self.assertRaises(ValidationError):
            SpellDeclarativeEffect(**{
                "type": "heal",
                "target": "selected_target",
                "params": {"condition": "blinded"},
            })


# ---------------------------------------------------------------------------
# Eligibility tests
# ---------------------------------------------------------------------------

class CureWoundsEligibilityTests(unittest.TestCase):
    def test_eligibility_passes_with_heal_effect(self):
        spell = _make_spell()
        state = _slot_state()
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state,
            slot_level=1,
            variant_key=None,
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_eligibility_fails_when_no_slot(self):
        spell = _make_spell()
        state = _slot_state(used=4, max_slots=4)
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json=state,
            slot_level=1,
            variant_key=None,
        )
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# build_persisted_effects / collect helpers
# ---------------------------------------------------------------------------

class CureWoundsBuildEffectsTests(unittest.TestCase):
    def test_build_persisted_effects_returns_empty_for_heal(self):
        spell = _make_spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="user-1",
            target_user_id="user-1",
            variant_key=None,
            game_time_seconds=0,
        )
        self.assertEqual(effects, [])

    def test_no_active_spell_effects_created_for_cure_wounds(self):
        spell = _make_spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="user-1",
            target_user_id="user-2",
            variant_key=None,
            game_time_seconds=0,
        )
        self.assertEqual(len(effects), 0, "heal must not produce active_spell_effects")

    def test_collect_heal_effects_extracts_correct_params(self):
        spell = _make_spell()
        collected = collect_heal_effects(spell, variant_key=None)
        self.assertEqual(len(collected), 1)
        params = collected[0]["params"]
        self.assertEqual(params["dice"], "1d8")
        self.assertEqual(params["ability_modifier"], "spellcasting")

    def test_collect_heal_effects_empty_for_non_heal_spell(self):
        spell = _make_spell(effects_json=[
            {"type": "modify_stat", "target": "caster", "params": {"stat": "attack_bonus", "value": 1}},
        ])
        collected = collect_heal_effects(spell, variant_key=None)
        self.assertEqual(collected, [])

    def test_goodberry_has_no_heal_effects_regression(self):
        """Goodberry must stay as create_consumable — no heal_effects."""
        goodberry = MagicMock()
        goodberry.effects_json = [
            {"type": "create_consumable", "target": "caster",
             "params": {"canonical_key": "goodberry", "quantity": 10, "expires_in_seconds": 86400}}
        ]
        goodberry.variants_json = []
        self.assertEqual(collect_heal_effects(goodberry, variant_key=None), [])


# ---------------------------------------------------------------------------
# Upcast tests
# ---------------------------------------------------------------------------

class CureWoundsUpcastTests(unittest.TestCase):
    def _spell_with_upcast(self, upcast_json=None):
        return _make_spell(upcast_json=upcast_json or {"mode": "extra_heal_dice", "dice": "1d8", "perLevel": 1})

    def test_base_cast_uses_1d8(self):
        spell = self._spell_with_upcast()
        result = compute_heal_dice_with_upcast("1d8", spell, slot_level=1)
        self.assertEqual(result, "1d8")

    def test_upcast_level_2_gives_2d8(self):
        spell = self._spell_with_upcast()
        result = compute_heal_dice_with_upcast("1d8", spell, slot_level=2)
        self.assertEqual(result, "2d8")

    def test_upcast_level_3_gives_3d8(self):
        spell = self._spell_with_upcast()
        result = compute_heal_dice_with_upcast("1d8", spell, slot_level=3)
        self.assertEqual(result, "3d8")

    def test_upcast_level_5_gives_5d8(self):
        spell = self._spell_with_upcast()
        result = compute_heal_dice_with_upcast("1d8", spell, slot_level=5)
        self.assertEqual(result, "5d8")

    def test_no_upcast_config_returns_base_dice(self):
        spell = _make_spell(upcast_json={})
        result = compute_heal_dice_with_upcast("1d8", spell, slot_level=3)
        self.assertEqual(result, "1d8")

    def test_slot_level_none_returns_base_dice(self):
        spell = self._spell_with_upcast()
        result = compute_heal_dice_with_upcast("1d8", spell, slot_level=None)
        self.assertEqual(result, "1d8")


# ---------------------------------------------------------------------------
# Spellcasting modifier tests
# ---------------------------------------------------------------------------

class SpellcastingModifierTests(unittest.TestCase):
    def test_reads_precomputed_modifier(self):
        state = {"spellcasting": {"ability": "wisdom", "modifier": 5}}
        self.assertEqual(resolve_spellcasting_modifier(state), 5)

    def test_computes_from_ability_score(self):
        # wisdom=16 → modifier = (16-10)//2 = 3
        state = _caster_state(wisdom=16)
        self.assertEqual(resolve_spellcasting_modifier(state), 3)

    def test_defaults_to_zero_when_no_spellcasting(self):
        self.assertEqual(resolve_spellcasting_modifier({}), 0)

    def test_negative_modifier(self):
        # wisdom=8 → (8-10)//2 = -1
        state = _caster_state(wisdom=8)
        self.assertEqual(resolve_spellcasting_modifier(state), -1)


# ---------------------------------------------------------------------------
# Roll heal effects tests
# ---------------------------------------------------------------------------

class RollSpellHealEffectsTests(unittest.TestCase):
    def test_total_is_at_least_modifier(self):
        spell = _make_spell()
        state = _caster_state(wisdom=16)  # mod=3
        heal_effects = collect_heal_effects(spell, variant_key=None)
        with patch("app.services.out_of_combat_cast.random.randint", return_value=4):
            results = roll_spell_heal_effects(heal_effects, spell, slot_level=1, caster_state_json=state)
        self.assertEqual(len(results), 1)
        # 4 (roll) + 3 (mod) = 7
        self.assertEqual(results[0]["amount"], 7)
        self.assertEqual(results[0]["rolls"], [4])
        self.assertEqual(results[0]["modifier"], 3)
        self.assertEqual(results[0]["effective_dice"], "1d8")

    def test_upcast_rolls_more_dice(self):
        spell = _make_spell()
        state = _caster_state(wisdom=16)  # mod=3
        heal_effects = collect_heal_effects(spell, variant_key=None)
        with patch("app.services.out_of_combat_cast.random.randint", return_value=5):
            results = roll_spell_heal_effects(heal_effects, spell, slot_level=2, caster_state_json=state)
        # 2d8: 5+5=10, mod=3 → total=13
        self.assertEqual(results[0]["amount"], 13)
        self.assertEqual(len(results[0]["rolls"]), 2)
        self.assertEqual(results[0]["effective_dice"], "2d8")

    def test_zero_healing_when_amount_would_be_negative(self):
        spell = _make_spell(effects_json=[{"type": "heal", "target": "selected_target", "params": {"dice": "1d8"}}])
        state = {}
        heal_effects = collect_heal_effects(spell, variant_key=None)
        with patch("app.services.out_of_combat_cast.random.randint", return_value=0):
            results = roll_spell_heal_effects(heal_effects, spell, slot_level=1, caster_state_json=state)
        self.assertGreaterEqual(results[0]["amount"], 0)


# ---------------------------------------------------------------------------
# HP application helper tests
# ---------------------------------------------------------------------------

class ApplyHealToStateDictTests(unittest.TestCase):
    def setUp(self):
        # Import the private helper from routes (testing internal logic)
        from app.api.routes.sessions.state import _apply_heal_to_state_dict
        self._apply = _apply_heal_to_state_dict

    def test_heals_hp_correctly(self):
        state = {"currentHP": 5, "maxHP": 14}
        result = self._apply(state, 4)
        self.assertEqual(result["currentHP"], 9)

    def test_caps_at_max_hp(self):
        state = {"currentHP": 12, "maxHP": 14}
        result = self._apply(state, 10)
        self.assertEqual(result["currentHP"], 14)

    def test_already_at_max_stays_at_max(self):
        state = {"currentHP": 14, "maxHP": 14}
        result = self._apply(state, 5)
        self.assertEqual(result["currentHP"], 14)

    def test_zero_healing_unchanged(self):
        state = {"currentHP": 7, "maxHP": 14}
        result = self._apply(state, 0)
        self.assertEqual(result["currentHP"], 7)

    def test_wild_shape_delegates_to_form_healing(self):
        state = {
            "currentHP": 20,
            "maxHP": 20,
            "wildShape": {"formKey": "brown_bear", "formCurrentHP": 5, "formMaxHP": 34},
        }
        mock_form = MagicMock()
        mock_form.max_hp = 34
        healed_state = {**state, "wildShape": {**state["wildShape"], "formCurrentHP": 9}}

        with patch("app.api.routes.sessions.state.is_wild_shape_active", return_value=True, create=True), \
             patch("app.api.routes.sessions.state.get_form", return_value=mock_form), \
             patch("app.api.routes.sessions.state.apply_healing_to_form", return_value=healed_state):
            result = self._apply(state, 4)

        self.assertEqual(result["wildShape"]["formCurrentHP"], 9)


if __name__ == "__main__":
    unittest.main()
