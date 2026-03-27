"""Tests for Wild Shape service and catalog."""
from __future__ import annotations

import unittest

from app.services.wild_shape_catalog import (
    get_all_forms,
    get_form,
    get_forms_for_level,
)
from app.services.wild_shape_service import (
    WildShapeError,
    apply_damage_to_form,
    apply_healing_to_form,
    compute_wild_shape_uses_max,
    ensure_wild_shape_block,
    force_revert,
    init_class_resources_for_druid,
    is_active,
    recharge_wild_shape,
    revert,
    transform,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _druid(level: int = 2, current_hp: int = 20, max_hp: int = 20) -> dict:
    return {
        "class": "druid",
        "level": level,
        "currentHP": current_hp,
        "maxHP": max_hp,
    }


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class WildShapeCatalogTests(unittest.TestCase):
    def test_get_form_returns_known_form(self):
        form = get_form("wolf")
        self.assertIsNotNone(form)
        self.assertEqual(form.canonical_key, "wolf")

    def test_get_form_returns_none_for_unknown(self):
        self.assertIsNone(get_form("dragon"))

    def test_all_forms_have_at_least_one_natural_attack(self):
        for form in get_all_forms():
            self.assertGreater(
                len(form.natural_attacks), 0,
                f"{form.canonical_key} has no natural attacks",
            )

    def test_forms_for_level_2_excludes_high_cr(self):
        forms = get_forms_for_level(2)
        keys = {f.canonical_key for f in forms}
        self.assertIn("cat", keys)
        self.assertIn("wolf", keys)
        self.assertNotIn("black_bear", keys)
        self.assertNotIn("brown_bear", keys)

    def test_forms_for_level_4_includes_half_cr(self):
        forms = get_forms_for_level(4)
        keys = {f.canonical_key for f in forms}
        self.assertIn("black_bear", keys)
        self.assertIn("crocodile", keys)
        self.assertNotIn("brown_bear", keys)

    def test_forms_for_level_8_includes_cr1(self):
        forms = get_forms_for_level(8)
        keys = {f.canonical_key for f in forms}
        self.assertIn("brown_bear", keys)
        self.assertIn("giant_spider", keys)


# ---------------------------------------------------------------------------
# Uses max
# ---------------------------------------------------------------------------


class UsesMaxTests(unittest.TestCase):
    def test_level_2_gets_two_uses(self):
        self.assertEqual(compute_wild_shape_uses_max(2), 2)

    def test_level_19_still_two_uses(self):
        self.assertEqual(compute_wild_shape_uses_max(19), 2)

    def test_level_20_gets_unlimited(self):
        self.assertGreater(compute_wild_shape_uses_max(20), 2)


# ---------------------------------------------------------------------------
# ensure_wild_shape_block
# ---------------------------------------------------------------------------


class EnsureBlockTests(unittest.TestCase):
    def test_creates_block_when_absent(self):
        data = ensure_wild_shape_block(_druid())
        ws = data["wildShape"]
        self.assertFalse(ws["active"])
        self.assertEqual(ws["usesMax"], 2)
        self.assertEqual(ws["usesRemaining"], 2)

    def test_patches_missing_keys_without_overwriting(self):
        data = {"class": "druid", "level": 2, "wildShape": {"active": True, "usesRemaining": 1}}
        result = ensure_wild_shape_block(data)
        ws = result["wildShape"]
        self.assertTrue(ws["active"])
        self.assertEqual(ws["usesRemaining"], 1)

    def test_does_not_mutate_input(self):
        original = _druid()
        ensure_wild_shape_block(original)
        self.assertNotIn("wildShape", original)


# ---------------------------------------------------------------------------
# transform
# ---------------------------------------------------------------------------


class TransformTests(unittest.TestCase):
    def test_transform_sets_active(self):
        data = _druid(level=2)
        result = transform(data, "wolf")
        self.assertTrue(is_active(result))

    def test_transform_sets_form_key(self):
        result = transform(_druid(level=2), "wolf")
        self.assertEqual(result["wildShape"]["formKey"], "wolf")

    def test_transform_sets_form_current_hp_to_form_max(self):
        wolf = get_form("wolf")
        result = transform(_druid(level=2), "wolf")
        self.assertEqual(result["wildShape"]["formCurrentHP"], wolf.max_hp)

    def test_transform_saves_humanoid_hp(self):
        data = _druid(level=2, current_hp=15)
        result = transform(data, "wolf")
        self.assertEqual(result["wildShape"]["savedHumanoidHP"], 15)

    def test_transform_decrements_uses(self):
        data = _druid(level=2)
        result = transform(data, "wolf")
        self.assertEqual(result["wildShape"]["usesRemaining"], 1)

    def test_transform_raises_for_non_druid(self):
        data = {"class": "fighter", "level": 5, "currentHP": 30, "maxHP": 30}
        with self.assertRaises(WildShapeError):
            transform(data, "wolf")

    def test_transform_raises_for_insufficient_level(self):
        data = _druid(level=2)
        with self.assertRaises(WildShapeError):
            transform(data, "black_bear")  # requires level 4

    def test_transform_raises_for_unknown_form(self):
        with self.assertRaises(WildShapeError):
            transform(_druid(level=2), "tarrasque")

    def test_transform_raises_when_already_active(self):
        data = transform(_druid(level=2), "wolf")
        with self.assertRaises(WildShapeError):
            transform(data, "cat")

    def test_transform_raises_when_no_uses_remaining(self):
        data = _druid(level=2)
        data = ensure_wild_shape_block(data)
        data["wildShape"]["usesRemaining"] = 0
        with self.assertRaises(WildShapeError):
            transform(data, "wolf")

    def test_transform_does_not_mutate_input(self):
        data = _druid(level=2)
        transform(data, "wolf")
        self.assertNotIn("wildShape", data)


# ---------------------------------------------------------------------------
# revert
# ---------------------------------------------------------------------------


class RevertTests(unittest.TestCase):
    def test_revert_sets_inactive(self):
        data = transform(_druid(level=2, current_hp=15), "wolf")
        result = revert(data)
        self.assertFalse(is_active(result))

    def test_revert_restores_humanoid_hp(self):
        data = transform(_druid(level=2, current_hp=15), "wolf")
        result = revert(data)
        self.assertEqual(result["currentHP"], 15)

    def test_revert_clears_form_key(self):
        data = transform(_druid(level=2), "wolf")
        result = revert(data)
        self.assertIsNone(result["wildShape"]["formKey"])

    def test_revert_clears_form_current_hp(self):
        data = transform(_druid(level=2), "wolf")
        result = revert(data)
        self.assertEqual(result["wildShape"]["formCurrentHP"], 0)

    def test_revert_raises_when_not_active(self):
        with self.assertRaises(WildShapeError):
            revert(_druid(level=2))

    def test_revert_hp_capped_at_max_hp(self):
        data = _druid(level=2, current_hp=20, max_hp=20)
        data = transform(data, "wolf")
        data["wildShape"]["savedHumanoidHP"] = 999  # artificially high
        result = revert(data)
        self.assertLessEqual(result["currentHP"], result["maxHP"])

    def test_force_revert_is_noop_when_not_active(self):
        data = _druid(level=2)
        result = force_revert(data)
        self.assertEqual(result, data)


# ---------------------------------------------------------------------------
# HP routing
# ---------------------------------------------------------------------------


class DamageRoutingTests(unittest.TestCase):
    def _transformed_wolf(self) -> dict:
        return transform(_druid(level=2, current_hp=20), "wolf")

    def test_damage_reduces_form_hp(self):
        data = self._transformed_wolf()
        wolf = get_form("wolf")
        result, reverted, overflow = apply_damage_to_form(data, 5)
        self.assertFalse(reverted)
        self.assertEqual(overflow, 0)
        self.assertEqual(result["wildShape"]["formCurrentHP"], wolf.max_hp - 5)

    def test_damage_does_not_change_humanoid_hp(self):
        data = self._transformed_wolf()
        result, _, _ = apply_damage_to_form(data, 5)
        # humanoid HP is saved, not touched while in form
        self.assertEqual(result["wildShape"]["savedHumanoidHP"], 20)

    def test_depleting_form_hp_reverts(self):
        data = self._transformed_wolf()
        wolf = get_form("wolf")
        result, reverted, overflow = apply_damage_to_form(data, wolf.max_hp + 4)
        self.assertTrue(reverted)
        self.assertFalse(is_active(result))

    def test_overflow_damage_returned_to_caller(self):
        """PHB 5e: excess damage carries over to the druid's humanoid form."""
        data = self._transformed_wolf()
        wolf = get_form("wolf")
        # wolf has 11 HP; deal 15 damage → 4 overflow
        result, reverted, overflow = apply_damage_to_form(data, wolf.max_hp + 4)
        self.assertTrue(reverted)
        self.assertEqual(overflow, 4)

    def test_overflow_is_zero_when_form_hp_exactly_depleted(self):
        data = self._transformed_wolf()
        wolf = get_form("wolf")
        result, reverted, overflow = apply_damage_to_form(data, wolf.max_hp)
        self.assertTrue(reverted)
        self.assertEqual(overflow, 0)

    def test_humanoid_hp_not_yet_reduced_by_service(self):
        """The service reverts (restores savedHumanoidHP) but does NOT apply overflow.
        That is the combat damage layer's responsibility."""
        data = self._transformed_wolf()
        wolf = get_form("wolf")
        result, reverted, overflow = apply_damage_to_form(data, wolf.max_hp + 4)
        self.assertTrue(reverted)
        # After revert, currentHP is the saved humanoid HP (20), NOT 20 - 4
        self.assertEqual(result["currentHP"], 20)

    def test_zero_damage_is_noop(self):
        data = self._transformed_wolf()
        result, reverted, overflow = apply_damage_to_form(data, 0)
        self.assertFalse(reverted)
        self.assertEqual(overflow, 0)
        self.assertIs(result, data)

    def test_damage_is_noop_when_not_in_form(self):
        data = _druid(level=2)
        result, reverted, overflow = apply_damage_to_form(data, 10)
        self.assertFalse(reverted)
        self.assertEqual(overflow, 0)

    def test_healing_increases_form_hp(self):
        wolf = get_form("wolf")
        data = self._transformed_wolf()
        # Damage some first
        data, _, _ = apply_damage_to_form(data, 5)
        result = apply_healing_to_form(data, 3, wolf)
        self.assertEqual(result["wildShape"]["formCurrentHP"], wolf.max_hp - 2)

    def test_healing_capped_at_form_max_hp(self):
        wolf = get_form("wolf")
        data = self._transformed_wolf()
        result = apply_healing_to_form(data, 9999, wolf)
        self.assertEqual(result["wildShape"]["formCurrentHP"], wolf.max_hp)


# ---------------------------------------------------------------------------
# Recharge
# ---------------------------------------------------------------------------


class RechargeTests(unittest.TestCase):
    def test_recharge_restores_all_uses(self):
        data = transform(_druid(level=2), "wolf")
        # One use consumed during transform
        self.assertEqual(data["wildShape"]["usesRemaining"], 1)
        data = revert(data)
        result = recharge_wild_shape(data)
        self.assertEqual(result["wildShape"]["usesRemaining"], 2)

    def test_recharge_respects_uses_max(self):
        data = _druid(level=2)
        data = ensure_wild_shape_block(data)
        data["wildShape"]["usesMax"] = 2
        data["wildShape"]["usesRemaining"] = 0
        result = recharge_wild_shape(data)
        self.assertEqual(result["wildShape"]["usesRemaining"], 2)


# ---------------------------------------------------------------------------
# classResources initialisation
# ---------------------------------------------------------------------------


class InitClassResourcesTests(unittest.TestCase):
    def test_adds_wild_shape_for_druid(self):
        data = {"class": "druid", "level": 2}
        result = init_class_resources_for_druid(data, 2)
        self.assertIn("classResources", result)
        self.assertIn("wildShape", result["classResources"])

    def test_uses_max_is_correct_at_level_2(self):
        data = init_class_resources_for_druid({"class": "druid"}, 2)
        self.assertEqual(data["classResources"]["wildShape"]["usesMax"], 2)

    def test_preserves_existing_remaining_when_below_max(self):
        data = {
            "class": "druid",
            "classResources": {"wildShape": {"usesMax": 2, "usesRemaining": 1}},
        }
        result = init_class_resources_for_druid(data, 2)
        self.assertEqual(result["classResources"]["wildShape"]["usesRemaining"], 1)

    def test_clamps_remaining_to_new_max(self):
        data = {
            "class": "druid",
            "classResources": {"wildShape": {"usesMax": 2, "usesRemaining": 99}},
        }
        result = init_class_resources_for_druid(data, 2)
        self.assertLessEqual(
            result["classResources"]["wildShape"]["usesRemaining"],
            result["classResources"]["wildShape"]["usesMax"],
        )


if __name__ == "__main__":
    unittest.main()
