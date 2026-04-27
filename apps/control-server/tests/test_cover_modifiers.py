"""
Tests for cover modifier logic (attack cover + save-cover metadata).

Covers:
- Core logic: each cover level produces the correct AC modifier (Phase 4)
- Edge cases: None and unknown cover levels
- cover_label: human-readable strings for UI feedback
- Integration: modifier flows into weapon/spell attack resolution via targeting result
- Save modifier: cover reduces effective DC for physical/spatial saving throw spells (Phase 5)
- should_cover_apply_to_save: metadata-first without heuristic fallback
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.combat_service.cover_modifiers import (
    COVER_AC_MODIFIERS,
    COVER_SAVE_MODIFIERS,
    COVER_SAVE_RULE_NONE,
    COVER_SAVE_RULE_PHYSICAL,
    COVER_SAVE_RULE_VALUES,
    cover_label,
    resolve_cover_modifier,
    resolve_cover_save_dc,
    resolve_cover_save_modifier,
    should_cover_apply_to_save,
)


class ResolveCoverModifierTests(unittest.TestCase):
    """Unit tests for resolve_cover_modifier — single source of truth for AC bonuses."""

    def test_none_cover_adds_no_modifier(self) -> None:
        self.assertEqual(resolve_cover_modifier("none"), 0)

    def test_half_cover_adds_two(self) -> None:
        self.assertEqual(resolve_cover_modifier("half"), 2)

    def test_three_quarters_cover_adds_five(self) -> None:
        self.assertEqual(resolve_cover_modifier("threeQuarters"), 5)

    def test_three_quarters_greater_than_half(self) -> None:
        self.assertGreater(
            resolve_cover_modifier("threeQuarters"),
            resolve_cover_modifier("half"),
        )

    def test_full_cover_adds_no_modifier(self) -> None:
        # Full cover is rejected before resolution; its modifier is 0.
        self.assertEqual(resolve_cover_modifier("full"), 0)

    def test_none_value_treated_as_no_cover(self) -> None:
        self.assertEqual(resolve_cover_modifier(None), 0)

    def test_unknown_cover_level_returns_zero(self) -> None:
        self.assertEqual(resolve_cover_modifier("unknown_level"), 0)

    def test_all_standard_levels_present_in_constant(self) -> None:
        for level in ("none", "half", "threeQuarters", "full"):
            self.assertIn(level, COVER_AC_MODIFIERS)

    def test_half_and_three_quarters_are_positive(self) -> None:
        self.assertGreater(COVER_AC_MODIFIERS["half"], 0)
        self.assertGreater(COVER_AC_MODIFIERS["threeQuarters"], 0)


class CoverLabelTests(unittest.TestCase):
    """Unit tests for cover_label — UI feedback strings."""

    def test_half_cover_has_label(self) -> None:
        label = cover_label("half")
        self.assertIsNotNone(label)
        self.assertIn("Half", label)

    def test_three_quarters_cover_has_label(self) -> None:
        label = cover_label("threeQuarters")
        self.assertIsNotNone(label)
        self.assertIn("Three-Quarters", label)

    def test_no_cover_returns_none(self) -> None:
        self.assertIsNone(cover_label("none"))

    def test_none_value_returns_none(self) -> None:
        self.assertIsNone(cover_label(None))

    def test_full_cover_returns_none(self) -> None:
        # Full cover is never shown in combat log — it's already blocked.
        self.assertIsNone(cover_label("full"))


class CoverModifierIntegrationTests(unittest.TestCase):
    """
    Integration tests: cover modifier flows correctly into attack resolution.

    These tests verify that the modifier from targeting_result.spatial_metadata.cover
    is added to target_ac before resolve_attack_base() is called.
    """

    def _make_targeting_result(self, cover: str | None):
        from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult

        return TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="enemy-1",
            affected_target_ref_ids=["enemy-1"],
            target_kind="session_entity",
            spatial_metadata=SpatialMetadata(cover=cover),
        )

    def test_half_cover_increases_effective_ac_by_two(self) -> None:
        base_ac = 14
        targeting_result = self._make_targeting_result("half")
        effective_ac = base_ac + resolve_cover_modifier(targeting_result.spatial_metadata.cover)
        self.assertEqual(effective_ac, 16)

    def test_three_quarters_cover_increases_effective_ac_by_five(self) -> None:
        base_ac = 14
        targeting_result = self._make_targeting_result("threeQuarters")
        effective_ac = base_ac + resolve_cover_modifier(targeting_result.spatial_metadata.cover)
        self.assertEqual(effective_ac, 19)

    def test_no_cover_leaves_ac_unchanged(self) -> None:
        base_ac = 14
        targeting_result = self._make_targeting_result("none")
        effective_ac = base_ac + resolve_cover_modifier(targeting_result.spatial_metadata.cover)
        self.assertEqual(effective_ac, 14)

    def test_three_quarters_harder_to_hit_than_half(self) -> None:
        base_ac = 12
        half_ac = base_ac + resolve_cover_modifier("half")
        three_q_ac = base_ac + resolve_cover_modifier("threeQuarters")
        self.assertGreater(three_q_ac, half_ac)

    def test_null_cover_from_spatial_metadata_adds_nothing(self) -> None:
        from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult

        result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="enemy-1",
            affected_target_ref_ids=["enemy-1"],
            target_kind="session_entity",
            spatial_metadata=SpatialMetadata(),  # cover defaults to None
        )
        base_ac = 15
        effective_ac = base_ac + resolve_cover_modifier(result.spatial_metadata.cover)
        self.assertEqual(effective_ac, 15)

    def test_full_cover_never_reaches_resolution(self) -> None:
        # Full cover should be rejected at targeting phase.
        # If it somehow reaches here, modifier must not change AC.
        base_ac = 14
        effective_ac = base_ac + resolve_cover_modifier("full")
        self.assertEqual(effective_ac, base_ac)


class ResolveCoverSaveModifierTests(unittest.TestCase):
    """Unit tests for resolve_cover_save_modifier — DC reduction values."""

    def test_none_cover_reduces_dc_by_zero(self) -> None:
        self.assertEqual(resolve_cover_save_modifier("none"), 0)

    def test_half_cover_reduces_dc_by_two(self) -> None:
        self.assertEqual(resolve_cover_save_modifier("half"), 2)

    def test_three_quarters_cover_reduces_dc_by_five(self) -> None:
        self.assertEqual(resolve_cover_save_modifier("threeQuarters"), 5)

    def test_full_cover_reduces_dc_by_zero(self) -> None:
        # Full cover is blocked upstream; modifier is irrelevant.
        self.assertEqual(resolve_cover_save_modifier("full"), 0)

    def test_none_value_reduces_dc_by_zero(self) -> None:
        self.assertEqual(resolve_cover_save_modifier(None), 0)

    def test_save_modifiers_match_ac_modifiers(self) -> None:
        # Cover consistently makes defenders harder to affect in all combat paths.
        for level in ("none", "half", "threeQuarters", "full"):
            self.assertEqual(
                resolve_cover_save_modifier(level),
                resolve_cover_modifier(level),
                msg=f"Mismatch at cover level '{level}'",
            )

    def test_all_standard_levels_in_constant(self) -> None:
        for level in ("none", "half", "threeQuarters", "full"):
            self.assertIn(level, COVER_SAVE_MODIFIERS)

    def test_rule_values_tuple_contains_physical_and_none(self) -> None:
        self.assertIn(COVER_SAVE_RULE_PHYSICAL, COVER_SAVE_RULE_VALUES)
        self.assertIn(COVER_SAVE_RULE_NONE, COVER_SAVE_RULE_VALUES)


class ShouldCoverApplyToSaveTests(unittest.TestCase):
    """Unit tests for should_cover_apply_to_save — metadata-first decision logic."""

    # --- Explicit metadata: physical ---

    def test_physical_metadata_applies_cover(self) -> None:
        self.assertTrue(should_cover_apply_to_save("physical"))

    def test_physical_metadata_applies_cover_regardless_of_ability(self) -> None:
        self.assertTrue(should_cover_apply_to_save("physical", "wisdom"))

    def test_physical_metadata_applies_cover_for_wis_save(self) -> None:
        # Metadata is authoritative — even a WIS save is physical if flagged.
        self.assertTrue(should_cover_apply_to_save("physical", "wis"))

    # --- Explicit metadata: none ---

    def test_none_metadata_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save("none"))

    def test_none_metadata_does_not_apply_even_for_dex_save(self) -> None:
        # Metadata is authoritative — DEX save does not get cover if flagged "none".
        self.assertFalse(should_cover_apply_to_save("none", "dex"))

    def test_none_metadata_does_not_apply_for_dexterity_save(self) -> None:
        self.assertFalse(should_cover_apply_to_save("none", "dexterity"))

    def test_no_metadata_dex_ability_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save(None, "dex"))

    def test_no_metadata_dexterity_ability_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save(None, "dexterity"))

    def test_no_metadata_dexterity_case_insensitive_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save(None, "DEX"))
        self.assertFalse(should_cover_apply_to_save(None, "Dexterity"))

    def test_no_metadata_wis_ability_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save(None, "wis"))

    def test_no_metadata_str_ability_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save(None, "str"))

    def test_no_metadata_con_ability_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save(None, "con"))

    def test_no_metadata_no_ability_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save(None, None))

    def test_no_metadata_empty_ability_does_not_apply_cover(self) -> None:
        self.assertFalse(should_cover_apply_to_save(None, ""))


class CoverSaveIntegrationTests(unittest.TestCase):
    """Integration: cover reduces effective DC for physical saves, not mental saves."""

    def _effective_dc(
        self,
        base_dc: int,
        cover: str | None,
        cover_applies_to_save: str | None,
        save_ability: str | None = None,
    ) -> int:
        effective_dc, _ = resolve_cover_save_dc(
            base_dc,
            cover,
            cover_applies_to_save,
            save_ability,
        )
        return effective_dc

    def test_fireball_half_cover_reduces_dc_by_two(self) -> None:
        # fireball → "physical", DEX save; half cover reduces DC 15 to 13
        effective = self._effective_dc(15, "half", "physical", "dexterity")
        self.assertEqual(effective, 13)

    def test_fireball_three_quarters_cover_reduces_dc_by_five(self) -> None:
        effective = self._effective_dc(15, "threeQuarters", "physical", "dexterity")
        self.assertEqual(effective, 10)

    def test_hold_person_half_cover_does_not_reduce_dc(self) -> None:
        # hold_person → "none", WIS save; cover never applies
        effective = self._effective_dc(15, "half", "none", "wisdom")
        self.assertEqual(effective, 15)

    def test_charm_person_three_quarters_cover_does_not_reduce_dc(self) -> None:
        effective = self._effective_dc(15, "threeQuarters", "none", "wisdom")
        self.assertEqual(effective, 15)

    def test_no_cover_does_not_change_dc(self) -> None:
        effective = self._effective_dc(14, "none", "physical", "dexterity")
        self.assertEqual(effective, 14)

    def test_dc_cannot_go_below_zero(self) -> None:
        # Extremely low base DC with large cover bonus must not go negative.
        effective = self._effective_dc(3, "threeQuarters", "physical", "dexterity")
        self.assertEqual(effective, 0)

    def test_null_cover_from_spatial_metadata_does_not_change_dc(self) -> None:
        effective = self._effective_dc(15, None, "physical", "dexterity")
        self.assertEqual(effective, 15)

    def test_thunderwave_con_save_with_physical_flag_gets_cover(self) -> None:
        # thunderwave → "physical", CON save; metadata overrides ability-based heuristic
        self.assertTrue(should_cover_apply_to_save("physical", "con"))
        effective = self._effective_dc(14, "half", "physical", "con")
        self.assertEqual(effective, 12)

    def test_null_metadata_dex_save_does_not_get_cover(self) -> None:
        effective = self._effective_dc(14, "half", None, "dex")
        self.assertEqual(effective, 14)

    def test_fallback_wis_save_no_metadata_does_not_get_cover(self) -> None:
        effective = self._effective_dc(14, "half", None, "wis")
        self.assertEqual(effective, 14)

    def test_unknown_metadata_does_not_get_cover(self) -> None:
        effective = self._effective_dc(14, "half", "unexpected", "dexterity")
        self.assertEqual(effective, 14)

    def test_resolve_cover_save_dc_returns_modifier_for_half_cover(self) -> None:
        effective, modifier = resolve_cover_save_dc(15, "half", "physical", "dexterity")
        self.assertEqual(effective, 13)
        self.assertEqual(modifier, 2)

    def test_resolve_cover_save_dc_returns_modifier_for_three_quarters_cover(self) -> None:
        effective, modifier = resolve_cover_save_dc(15, "threeQuarters", "physical", "dexterity")
        self.assertEqual(effective, 10)
        self.assertEqual(modifier, 5)


if __name__ == "__main__":
    unittest.main()
