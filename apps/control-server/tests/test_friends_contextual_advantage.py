"""Test: Friends spell contextual advantage with selected_target.

This test validates the complete cycle:
1. Cast Friends on target A
2. Check advantage vs A (should have)
3. Check advantage vs B (should NOT have)
4. Recast Friends on target B (replaces previous effect)
5. Check advantage vs B (should have)
6. Check advantage vs A (should NOT have, effect was replaced)

Regression guard: prevents silent breakage of contextual advantages.
"""

import unittest

from app.services.combat_service.condition_effects_predicates import (
    explain_check_modifier_sources,
    resolve_check_advantage_mode,
)


def _spell_effect_advantage(ability: str, against: str | None = None) -> dict:
    """Build a spell effect dict for advantage_on_checks."""
    return {
        "kind": "spell_effect",
        "metadata": {
            "declarative_effect": {
                "type": "advantage_on_checks",
                "params": {
                    "ability": ability,
                    **({"against": against} if against else {}),
                },
            },
            "selected_target_participant_id": None,  # Will be set per scenario
            "selected_target_display_name": "Guard Captain",
            "caster_participant_id": "caster_id",
            "source_spell_key": "friends",
            "source_spell_name": "Friends",
            "concentration": False,
        },
    }


def _participant_with_effect(
    participant_id: str, effects: list[dict] | None = None
) -> dict:
    """Build a participant with active effects."""
    return {
        "id": participant_id,
        "active_effects": effects or [],
        "status": "active",
    }


class TestFriendsContextualAdvantage(unittest.TestCase):
    """Friends spell with against: selected_target validation."""

    def test_cast_on_target_a_only(self):
        """Step 1: Cast Friends on target A."""
        effect = _spell_effect_advantage("charisma", against="selected_target")
        effect["metadata"]["selected_target_participant_id"] = "target_a_id"

        caster = _participant_with_effect("caster_id", [effect])
        mode = resolve_check_advantage_mode(caster, "charisma", target_participant_id="target_a_id")
        self.assertEqual(mode, "advantage", "Should have advantage vs target A after casting Friends")

    def test_check_vs_different_target_after_cast_on_a(self):
        """Step 2: Check advantage vs B when Friends is on A (should NOT have)."""
        effect = _spell_effect_advantage("charisma", against="selected_target")
        effect["metadata"]["selected_target_participant_id"] = "target_a_id"

        caster = _participant_with_effect("caster_id", [effect])
        mode = resolve_check_advantage_mode(caster, "charisma", target_participant_id="target_b_id")
        self.assertEqual(mode, "normal", "Should NOT have advantage vs target B when Friends is on A")

    def test_recast_on_target_b_replaces(self):
        """Step 3 & 4: Recast Friends on B (should replace effect from A)."""
        # Initial effect on A
        effect_on_a = _spell_effect_advantage("charisma", against="selected_target")
        effect_on_a["metadata"]["selected_target_participant_id"] = "target_a_id"

        caster = _participant_with_effect("caster_id", [effect_on_a])

        # Simulate the replace logic: same type & params means old is removed
        # In real code, _replace_matching_effects handles this
        # Here we just simulate the new effect
        effect_on_b = _spell_effect_advantage("charisma", against="selected_target")
        effect_on_b["metadata"]["selected_target_participant_id"] = "target_b_id"

        caster_after_recast = _participant_with_effect("caster_id", [effect_on_b])

        # Now check: should have advantage vs B
        mode_vs_b = resolve_check_advantage_mode(
            caster_after_recast, "charisma", target_participant_id="target_b_id"
        )
        self.assertEqual(mode_vs_b, "advantage", "Should have advantage vs target B after recasting")

        # And NOT vs A
        mode_vs_a = resolve_check_advantage_mode(
            caster_after_recast, "charisma", target_participant_id="target_a_id"
        )
        self.assertEqual(
            mode_vs_a, "normal", "Should NOT have advantage vs target A after recasting on B"
        )

    def test_complete_cycle(self):
        """Full cycle: A → B → A validation."""
        # T0: Cast on A
        effect_on_a = _spell_effect_advantage("charisma", against="selected_target")
        effect_on_a["metadata"]["selected_target_participant_id"] = "target_a_id"
        caster = _participant_with_effect("caster_id", [effect_on_a])

        # T1: Check vs A (should have)
        self.assertEqual(
            resolve_check_advantage_mode(caster, "charisma", target_participant_id="target_a_id"),
            "advantage",
            "T1: Should have advantage vs A",
        )

        # T2: Check vs B (should NOT have)
        self.assertEqual(
            resolve_check_advantage_mode(caster, "charisma", target_participant_id="target_b_id"),
            "normal",
            "T2: Should NOT have advantage vs B",
        )

        # T3: Recast on B (effect replaced in real code)
        effect_on_b = _spell_effect_advantage("charisma", against="selected_target")
        effect_on_b["metadata"]["selected_target_participant_id"] = "target_b_id"
        caster_after_recast = _participant_with_effect("caster_id", [effect_on_b])

        # T4: Check vs B (should have)
        self.assertEqual(
            resolve_check_advantage_mode(
                caster_after_recast, "charisma", target_participant_id="target_b_id"
            ),
            "advantage",
            "T4: Should have advantage vs B after recast",
        )

        # T5: Check vs A (should NOT have, effect was replaced)
        self.assertEqual(
            resolve_check_advantage_mode(
                caster_after_recast, "charisma", target_participant_id="target_a_id"
            ),
            "normal",
            "T5: Should NOT have advantage vs A (effect replaced with B)",
        )

    def test_no_target_participant_id_defaults_to_normal(self):
        """Edge case: Check without target_participant_id (e.g., initiative)."""
        effect = _spell_effect_advantage("charisma", against="selected_target")
        effect["metadata"]["selected_target_participant_id"] = "target_a_id"

        caster = _participant_with_effect("caster_id", [effect])
        mode = resolve_check_advantage_mode(caster, "charisma", target_participant_id=None)
        self.assertEqual(
            mode, "normal", "Should NOT have advantage if target_participant_id is None"
        )

    def test_against_any_ignores_target(self):
        """Baseline: against='any' should always apply (for comparison)."""
        effect = _spell_effect_advantage("charisma", against="any")
        effect["metadata"]["selected_target_participant_id"] = "target_a_id"

        caster = _participant_with_effect("caster_id", [effect])

        # vs A
        mode_vs_a = resolve_check_advantage_mode(caster, "charisma", target_participant_id="target_a_id")
        self.assertEqual(mode_vs_a, "advantage", "against='any' should apply vs A")

        # vs B
        mode_vs_b = resolve_check_advantage_mode(caster, "charisma", target_participant_id="target_b_id")
        self.assertEqual(mode_vs_b, "advantage", "against='any' should apply vs B")

        # vs None
        mode_vs_none = resolve_check_advantage_mode(caster, "charisma", target_participant_id=None)
        self.assertEqual(mode_vs_none, "advantage", "against='any' should apply even with no target")

    def test_different_ability_not_affected(self):
        """Charisma advantage should NOT apply to Strength checks."""
        effect = _spell_effect_advantage("charisma", against="selected_target")
        effect["metadata"]["selected_target_participant_id"] = "target_a_id"

        caster = _participant_with_effect("caster_id", [effect])
        mode = resolve_check_advantage_mode(caster, "strength", target_participant_id="target_a_id")
        self.assertEqual(
            mode, "normal", "Charisma advantage should NOT apply to Strength checks"
        )

    def test_explain_sources_marks_applied_entry(self):
        effect = _spell_effect_advantage("charisma", against="selected_target")
        effect["metadata"]["selected_target_participant_id"] = "target_a_id"
        caster = _participant_with_effect("caster_id", [effect])

        explanation = explain_check_modifier_sources(
            caster,
            ability="charisma",
            roll_type="ability",
            target_participant_id="target_a_id",
        )

        self.assertEqual(len(explanation), 1)
        self.assertTrue(explanation[0]["applied"])
        self.assertIsNone(explanation[0]["skip_reason"])
        self.assertEqual(explanation[0]["selected_target_display_name"], "Guard Captain")

    def test_explain_sources_marks_target_mismatch(self):
        effect = _spell_effect_advantage("charisma", against="selected_target")
        effect["metadata"]["selected_target_participant_id"] = "target_a_id"
        caster = _participant_with_effect("caster_id", [effect])

        explanation = explain_check_modifier_sources(
            caster,
            ability="charisma",
            roll_type="ability",
            target_participant_id="target_b_id",
        )

        self.assertEqual(len(explanation), 1)
        self.assertFalse(explanation[0]["applied"])
        self.assertEqual(explanation[0]["skip_reason"], "target_mismatch")


if __name__ == "__main__":
    unittest.main()
