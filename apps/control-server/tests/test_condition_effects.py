"""Phase 12 / Phase F1 / Phase F2 — condition_effects unit tests."""

import unittest

from app.services.combat_service.condition_effects import (
    AttackAdvantageContext,
    SaveModifierContext,
    can_see,
    get_attack_advantage_penalty,
    get_attack_auto_crit,
    get_effective_reach,
    has_condition,
    is_action_blocked,
    is_invisible,
    is_movement_blocked,
    is_movement_halved,
    modify_saving_throw,
    resolve_attack_advantage,
    resolve_spell_attack_kind,
)


# ─── helpers ─────────────────────────────────────────────────────────────────


def _participant(
    conditions: list[str] | None = None, extra_effects: list[dict] | None = None
) -> dict:
    """Build a minimal participant dict with the given conditions."""
    effects: list[dict] = []
    for ctype in conditions or []:
        effects.append({"kind": "condition", "condition_type": ctype})
    effects.extend(extra_effects or [])
    return {"id": "p1", "active_effects": effects, "status": "active"}


# ─── has_condition ────────────────────────────────────────────────────────────


class TestHasCondition(unittest.TestCase):
    def test_present(self):
        p = _participant(["blinded"])
        self.assertTrue(has_condition(p, "blinded"))

    def test_absent(self):
        p = _participant(["prone"])
        self.assertFalse(has_condition(p, "blinded"))

    def test_no_effects(self):
        p = _participant()
        self.assertFalse(has_condition(p, "poisoned"))

    def test_non_condition_effect_not_matched(self):
        p = _participant(
            extra_effects=[
                {
                    "kind": "temp_ac_bonus",
                    "condition_type": "blinded",
                    "numeric_value": 2,
                }
            ]
        )
        # kind is not 'condition', must not match
        self.assertFalse(has_condition(p, "blinded"))

    def test_multiple_conditions_individual_check(self):
        p = _participant(["prone", "poisoned", "restrained"])
        self.assertTrue(has_condition(p, "prone"))
        self.assertTrue(has_condition(p, "poisoned"))
        self.assertTrue(has_condition(p, "restrained"))
        self.assertFalse(has_condition(p, "blinded"))

    def test_none_active_effects(self):
        p = {"id": "p1", "active_effects": None, "status": "active"}
        self.assertFalse(has_condition(p, "blinded"))

    def test_missing_active_effects_key(self):
        p = {"id": "p1", "status": "active"}
        self.assertFalse(has_condition(p, "blinded"))


# ─── is_action_blocked ────────────────────────────────────────────────────────


class TestIsActionBlocked(unittest.TestCase):
    def test_no_conditions(self):
        self.assertFalse(is_action_blocked(_participant()))

    def test_incapacitated(self):
        self.assertTrue(is_action_blocked(_participant(["incapacitated"])))

    def test_paralyzed(self):
        self.assertTrue(is_action_blocked(_participant(["paralyzed"])))

    def test_stunned(self):
        self.assertTrue(is_action_blocked(_participant(["stunned"])))

    def test_unconscious(self):
        self.assertTrue(is_action_blocked(_participant(["unconscious"])))

    def test_petrified(self):
        self.assertTrue(is_action_blocked(_participant(["petrified"])))

    def test_prone_not_blocked(self):
        self.assertFalse(is_action_blocked(_participant(["prone"])))

    def test_blinded_not_blocked(self):
        self.assertFalse(is_action_blocked(_participant(["blinded"])))

    def test_poisoned_not_blocked(self):
        self.assertFalse(is_action_blocked(_participant(["poisoned"])))

    def test_restrained_not_blocked(self):
        self.assertFalse(is_action_blocked(_participant(["restrained"])))

    def test_frightened_not_blocked(self):
        self.assertFalse(is_action_blocked(_participant(["frightened"])))


# ─── is_movement_blocked ─────────────────────────────────────────────────────


class TestIsMovementBlocked(unittest.TestCase):
    def test_no_conditions(self):
        self.assertFalse(is_movement_blocked(_participant()))

    def test_incapacitated(self):
        self.assertTrue(is_movement_blocked(_participant(["incapacitated"])))

    def test_paralyzed(self):
        self.assertTrue(is_movement_blocked(_participant(["paralyzed"])))

    def test_stunned(self):
        self.assertTrue(is_movement_blocked(_participant(["stunned"])))

    def test_unconscious(self):
        self.assertTrue(is_movement_blocked(_participant(["unconscious"])))

    def test_petrified(self):
        self.assertTrue(is_movement_blocked(_participant(["petrified"])))

    def test_restrained(self):
        self.assertTrue(is_movement_blocked(_participant(["restrained"])))

    def test_grappled(self):
        self.assertTrue(is_movement_blocked(_participant(["grappled"])))

    def test_prone_not_blocked(self):
        self.assertFalse(is_movement_blocked(_participant(["prone"])))

    def test_blinded_not_blocked(self):
        self.assertFalse(is_movement_blocked(_participant(["blinded"])))


# ─── is_movement_halved ──────────────────────────────────────────────────────


class TestIsMovementHalved(unittest.TestCase):
    def test_no_conditions(self):
        self.assertFalse(is_movement_halved(_participant()))

    def test_prone(self):
        self.assertTrue(is_movement_halved(_participant(["prone"])))

    def test_prone_but_also_restrained(self):
        # restrained already sets speed to 0; halving doesn't apply on top
        self.assertFalse(is_movement_halved(_participant(["prone", "restrained"])))

    def test_incapacitated_not_halved(self):
        # incapacitated blocks entirely; is_movement_halved returns False
        self.assertFalse(is_movement_halved(_participant(["incapacitated"])))

    def test_poisoned_not_halved(self):
        self.assertFalse(is_movement_halved(_participant(["poisoned"])))


# ─── can_see ─────────────────────────────────────────────────────────────────


class TestCanSee(unittest.TestCase):
    def test_no_conditions(self):
        self.assertTrue(can_see(_participant()))

    def test_blinded(self):
        self.assertFalse(can_see(_participant(["blinded"])))

    def test_unconscious(self):
        self.assertFalse(can_see(_participant(["unconscious"])))

    def test_petrified(self):
        self.assertFalse(can_see(_participant(["petrified"])))

    def test_prone_can_see(self):
        self.assertTrue(can_see(_participant(["prone"])))

    def test_restrained_can_see(self):
        self.assertTrue(can_see(_participant(["restrained"])))


# ─── is_invisible ─────────────────────────────────────────────────────────────


class TestIsInvisible(unittest.TestCase):
    def test_not_invisible(self):
        self.assertFalse(is_invisible(_participant()))

    def test_invisible(self):
        self.assertTrue(is_invisible(_participant(["invisible"])))

    def test_blinded_not_invisible(self):
        self.assertFalse(is_invisible(_participant(["blinded"])))


# ─── get_attack_advantage_penalty ────────────────────────────────────────────


class TestGetAttackAdvantagePenalty(unittest.TestCase):
    def _adv(self, attacker_conditions=None, target_conditions=None):
        attacker = _participant(attacker_conditions)
        target = _participant(target_conditions)
        return get_attack_advantage_penalty(attacker, target)

    def test_no_conditions(self):
        self.assertEqual(self._adv(), 0)

    def test_attacker_blinded(self):
        self.assertEqual(self._adv(["blinded"]), -1)

    def test_attacker_prone(self):
        self.assertEqual(self._adv(["prone"]), -1)

    def test_attacker_restrained(self):
        self.assertEqual(self._adv(["restrained"]), -1)

    def test_attacker_poisoned(self):
        self.assertEqual(self._adv(["poisoned"]), -1)

    def test_attacker_frightened(self):
        self.assertEqual(self._adv(["frightened"]), -1)

    def test_attacker_invisible(self):
        self.assertEqual(self._adv(["invisible"]), 1)

    def test_target_invisible(self):
        # Attacker attacking an invisible target → disadvantage
        self.assertEqual(self._adv(target_conditions=["invisible"]), -1)

    def test_advantage_and_disadvantage_cancel(self):
        # Attacker invisible but also blinded → cancels
        self.assertEqual(self._adv(["invisible", "blinded"]), 0)

    def test_invisible_vs_invisible(self):
        # Both invisible: attacker has advantage (invisible), but target is also invisible (disadvantage)
        self.assertEqual(self._adv(["invisible"], ["invisible"]), 0)


# ─── resolve_attack_advantage — core resolution ──────────────────────────────


class TestResolveAttackAdvantageCore(unittest.TestCase):
    """Tests for the 5e cancellation resolution rules."""

    def _ctx(self, attacker_conds=None, target_conds=None, attack_kind="melee"):
        return resolve_attack_advantage(
            _participant(attacker_conds),
            _participant(target_conds),
            attack_kind=attack_kind,
        )

    def test_no_sources_result_normal(self):
        ctx = self._ctx()
        self.assertEqual(ctx.result, "normal")
        self.assertEqual(ctx.advantage_sources, [])
        self.assertEqual(ctx.disadvantage_sources, [])

    def test_one_advantage_source(self):
        ctx = self._ctx(attacker_conds=["invisible"])
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("attacker_invisible", ctx.advantage_sources)
        self.assertEqual(ctx.disadvantage_sources, [])

    def test_one_disadvantage_source(self):
        ctx = self._ctx(attacker_conds=["poisoned"])
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("attacker_poisoned", ctx.disadvantage_sources)
        self.assertEqual(ctx.advantage_sources, [])

    def test_adv_and_dis_cancel_to_normal(self):
        # invisible (adv) + prone (dis) → normal
        ctx = self._ctx(attacker_conds=["invisible", "prone"])
        self.assertEqual(ctx.result, "normal")
        self.assertIn("attacker_invisible", ctx.advantage_sources)
        self.assertIn("attacker_prone", ctx.disadvantage_sources)

    def test_multiple_adv_sources_still_advantage(self):
        # restrained target + unconscious target → still just advantage, not stronger
        ctx = self._ctx(target_conds=["restrained", "unconscious"])
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("target_restrained", ctx.advantage_sources)
        self.assertIn("target_unconscious", ctx.advantage_sources)
        self.assertEqual(ctx.disadvantage_sources, [])

    def test_multiple_dis_sources_still_disadvantage(self):
        ctx = self._ctx(attacker_conds=["prone", "poisoned", "frightened"])
        self.assertEqual(ctx.result, "disadvantage")
        self.assertEqual(ctx.advantage_sources, [])
        self.assertEqual(len(ctx.disadvantage_sources), 3)

    def test_multiple_on_each_side_cancel(self):
        # Two adv sources and two dis sources → normal
        ctx = self._ctx(
            attacker_conds=["invisible", "poisoned"], target_conds=["restrained"]
        )
        # invisible → adv, target_restrained → adv, poisoned → dis
        # two adv, one dis → still cancels to normal
        self.assertEqual(ctx.result, "normal")


# ─── resolve_attack_advantage — condition mappings ───────────────────────────


class TestResolveAttackAdvantageConditions(unittest.TestCase):
    """One test per condition mapping specified in Phase F1."""

    def _adv(self, attacker_conds=None, target_conds=None, attack_kind="melee"):
        return resolve_attack_advantage(
            _participant(attacker_conds),
            _participant(target_conds),
            attack_kind=attack_kind,
        )

    # Attacker-side disadvantage
    def test_attacker_poisoned_gives_disadvantage(self):
        ctx = self._adv(attacker_conds=["poisoned"])
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("attacker_poisoned", ctx.disadvantage_sources)

    def test_attacker_frightened_gives_disadvantage(self):
        ctx = self._adv(attacker_conds=["frightened"])
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("attacker_frightened", ctx.disadvantage_sources)

    def test_attacker_restrained_gives_disadvantage(self):
        ctx = self._adv(attacker_conds=["restrained"])
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("attacker_restrained", ctx.disadvantage_sources)

    def test_attacker_prone_gives_disadvantage(self):
        ctx = self._adv(attacker_conds=["prone"])
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("attacker_prone", ctx.disadvantage_sources)

    # NOTE (Phase F3): attacker_blinded and target_invisible are now resolved
    # through the centralized visibility module, not through
    # resolve_attack_advantage. See test_visibility.py.

    # Attacker-side advantage
    def test_attacker_invisible_gives_advantage(self):
        ctx = self._adv(attacker_conds=["invisible"])
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("attacker_invisible", ctx.advantage_sources)

    # Target-side conditions
    def test_target_restrained_gives_advantage(self):
        ctx = self._adv(target_conds=["restrained"])
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("target_restrained", ctx.advantage_sources)

    def test_target_paralyzed_gives_advantage(self):
        ctx = self._adv(target_conds=["paralyzed"])
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("target_paralyzed", ctx.advantage_sources)

    def test_target_stunned_gives_advantage(self):
        ctx = self._adv(target_conds=["stunned"])
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("target_stunned", ctx.advantage_sources)

    def test_target_unconscious_gives_advantage(self):
        ctx = self._adv(target_conds=["unconscious"])
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("target_unconscious", ctx.advantage_sources)

    # Prone target: melee vs ranged
    def test_target_prone_melee_gives_advantage(self):
        ctx = self._adv(target_conds=["prone"], attack_kind="melee")
        self.assertEqual(ctx.result, "advantage")
        self.assertIn("target_prone_melee", ctx.advantage_sources)
        self.assertNotIn("target_prone_ranged", ctx.disadvantage_sources)

    def test_target_prone_ranged_gives_disadvantage(self):
        ctx = self._adv(target_conds=["prone"], attack_kind="ranged")
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("target_prone_ranged", ctx.disadvantage_sources)
        self.assertNotIn("target_prone_melee", ctx.advantage_sources)

    # Cancellation: invisible attacker vs various
    def test_invisible_attacker_vs_prone_ranged_cancels(self):
        ctx = self._adv(
            attacker_conds=["invisible"], target_conds=["prone"], attack_kind="ranged"
        )
        self.assertEqual(ctx.result, "normal")
        self.assertIn("attacker_invisible", ctx.advantage_sources)
        self.assertIn("target_prone_ranged", ctx.disadvantage_sources)

    # NOTE (Phase F3): invisible_vs_invisible cancellation is now handled
    # through the visibility module. attacker_invisible (adv) cancels with
    # attacker_cannot_directly_see_target (dis) from visibility resolution.


# ─── resolve_attack_advantage — describe() ───────────────────────────────────


class TestAttackAdvantageContextDescribe(unittest.TestCase):
    def test_no_sources_returns_normal(self):
        ctx = AttackAdvantageContext()
        self.assertEqual(ctx.describe(), "normal")

    def test_advantage_description(self):
        ctx = AttackAdvantageContext(
            advantage_sources=["attacker_invisible", "target_restrained"],
            disadvantage_sources=[],
            result="advantage",
        )
        desc = ctx.describe()
        self.assertIn("advantage", desc)
        self.assertIn("attacker_invisible", desc)
        self.assertIn("target_restrained", desc)

    def test_disadvantage_description(self):
        ctx = AttackAdvantageContext(
            advantage_sources=[],
            disadvantage_sources=["attacker_blinded"],
            result="disadvantage",
        )
        desc = ctx.describe()
        self.assertIn("disadvantage", desc)
        self.assertIn("attacker_blinded", desc)

    def test_cancellation_description(self):
        ctx = AttackAdvantageContext(
            advantage_sources=["attacker_invisible"],
            disadvantage_sources=["target_prone_ranged"],
            result="normal",
        )
        desc = ctx.describe()
        self.assertIn("normal", desc)
        self.assertIn("attacker_invisible", desc)
        self.assertIn("canceled by", desc)
        self.assertIn("target_prone_ranged", desc)


# ─── get_attack_advantage_penalty (deprecated wrapper) ───────────────────────


class TestGetAttackAdvantagePenalty(unittest.TestCase):
    """Backward-compatibility tests for the deprecated wrapper.

    The wrapper delegates to resolve_attack_advantage (melee mode) and maps
    the structured result back to +1 / 0 / -1.

    NOTE (Phase F3): attacker_blinded and target_invisible are now handled by
    the visibility module, not by resolve_attack_advantage. The tests below
    that relied on those sources have been updated or moved to test_visibility.
    """

    def _adv(self, attacker_conditions=None, target_conditions=None):
        attacker = _participant(attacker_conditions)
        target = _participant(target_conditions)
        return get_attack_advantage_penalty(attacker, target)

    def test_no_conditions(self):
        self.assertEqual(self._adv(), 0)

    def test_attacker_prone(self):
        self.assertEqual(self._adv(["prone"]), -1)

    def test_attacker_restrained(self):
        self.assertEqual(self._adv(["restrained"]), -1)

    def test_attacker_poisoned(self):
        self.assertEqual(self._adv(["poisoned"]), -1)

    def test_attacker_frightened(self):
        self.assertEqual(self._adv(["frightened"]), -1)

    def test_attacker_invisible(self):
        self.assertEqual(self._adv(["invisible"]), 1)


# ─── get_effective_reach ─────────────────────────────────────────────────────


class TestGetEffectiveReach(unittest.TestCase):
    def test_standard_reach(self):
        self.assertEqual(get_effective_reach(1), 1)

    def test_extended_reach(self):
        self.assertEqual(get_effective_reach(2), 2)

    def test_zero_clamped_to_one(self):
        self.assertEqual(get_effective_reach(0), 1)

    def test_negative_clamped_to_one(self):
        self.assertEqual(get_effective_reach(-5), 1)


# ─── get_attack_auto_crit ────────────────────────────────────────────────────


class TestGetAttackAutoCrit(unittest.TestCase):
    """Phase F2 — melee auto-crit for paralyzed/unconscious targets."""

    def _crit(self, attacker_conds=None, target_conds=None, attack_kind="melee"):
        return get_attack_auto_crit(
            _participant(attacker_conds),
            _participant(target_conds),
            attack_kind=attack_kind,
        )

    # ── no auto-crit ─────────────────────────────────────────────────────────
    def test_no_conditions_returns_empty(self):
        self.assertEqual(self._crit(), "")

    def test_target_stunned_melee_no_autocrit(self):
        # Stunned gives advantage but NOT auto-crit in 5e SRD
        self.assertEqual(self._crit(target_conds=["stunned"]), "")

    def test_target_restrained_no_autocrit(self):
        self.assertEqual(self._crit(target_conds=["restrained"]), "")

    def test_target_prone_no_autocrit(self):
        self.assertEqual(self._crit(target_conds=["prone"]), "")

    def test_attacker_paralyzed_no_autocrit(self):
        # Condition is on attacker, not target — irrelevant for auto-crit
        self.assertEqual(self._crit(attacker_conds=["paralyzed"]), "")

    def test_target_paralyzed_ranged_no_autocrit(self):
        # Auto-crit only applies to melee
        self.assertEqual(
            self._crit(target_conds=["paralyzed"], attack_kind="ranged"), ""
        )

    def test_target_unconscious_ranged_no_autocrit(self):
        self.assertEqual(
            self._crit(target_conds=["unconscious"], attack_kind="ranged"), ""
        )

    # ── auto-crit triggers ───────────────────────────────────────────────────
    def test_target_paralyzed_melee_returns_source(self):
        result = self._crit(target_conds=["paralyzed"])
        self.assertEqual(result, "target_paralyzed")

    def test_target_unconscious_melee_returns_source(self):
        result = self._crit(target_conds=["unconscious"])
        self.assertEqual(result, "target_unconscious")

    def test_result_is_truthy(self):
        # Callers rely on the return value being truthy when auto-crit applies
        self.assertTrue(self._crit(target_conds=["paralyzed"]))
        self.assertFalse(self._crit())

    def test_paralyzed_takes_priority_over_unconscious(self):
        # Both present — paralyzed is checked first
        result = self._crit(target_conds=["paralyzed", "unconscious"])
        self.assertEqual(result, "target_paralyzed")


# ─── modify_saving_throw ─────────────────────────────────────────────────────


class TestModifySavingThrow(unittest.TestCase):
    """Phase F2 — condition-based saving throw modifiers."""

    def _mod(self, conditions=None, ability="strength"):
        return modify_saving_throw(_participant(conditions), ability)

    # ── baseline ─────────────────────────────────────────────────────────────
    def test_no_conditions_no_modifier(self):
        ctx = self._mod()
        self.assertFalse(ctx.auto_fail)
        self.assertEqual(ctx.result, "normal")
        self.assertEqual(ctx.auto_fail_source, "")
        self.assertEqual(ctx.disadvantage_sources, [])

    # ── paralyzed auto-fail ──────────────────────────────────────────────────
    def test_paralyzed_str_auto_fail(self):
        ctx = self._mod(["paralyzed"], "strength")
        self.assertTrue(ctx.auto_fail)
        self.assertEqual(ctx.auto_fail_source, "actor_paralyzed")

    def test_paralyzed_dex_auto_fail(self):
        ctx = self._mod(["paralyzed"], "dexterity")
        self.assertTrue(ctx.auto_fail)

    def test_paralyzed_con_no_auto_fail(self):
        # Paralyzed only auto-fails STR and DEX in 5e SRD
        ctx = self._mod(["paralyzed"], "constitution")
        self.assertFalse(ctx.auto_fail)

    def test_paralyzed_wis_no_auto_fail(self):
        ctx = self._mod(["paralyzed"], "wisdom")
        self.assertFalse(ctx.auto_fail)

    # ── stunned auto-fail ────────────────────────────────────────────────────
    def test_stunned_str_auto_fail(self):
        ctx = self._mod(["stunned"], "strength")
        self.assertTrue(ctx.auto_fail)
        self.assertEqual(ctx.auto_fail_source, "actor_stunned")

    def test_stunned_dex_auto_fail(self):
        ctx = self._mod(["stunned"], "dexterity")
        self.assertTrue(ctx.auto_fail)

    def test_stunned_con_no_auto_fail(self):
        ctx = self._mod(["stunned"], "constitution")
        self.assertFalse(ctx.auto_fail)

    # ── unconscious auto-fail ────────────────────────────────────────────────
    def test_unconscious_dex_auto_fail(self):
        ctx = self._mod(["unconscious"], "dexterity")
        self.assertTrue(ctx.auto_fail)
        self.assertEqual(ctx.auto_fail_source, "actor_unconscious")

    def test_unconscious_str_auto_fail(self):
        ctx = self._mod(["unconscious"], "strength")
        self.assertTrue(ctx.auto_fail)

    def test_unconscious_wis_no_auto_fail(self):
        ctx = self._mod(["unconscious"], "wisdom")
        self.assertFalse(ctx.auto_fail)

    # ── restrained disadvantage on DEX ──────────────────────────────────────
    def test_restrained_dex_disadvantage(self):
        ctx = self._mod(["restrained"], "dexterity")
        self.assertFalse(ctx.auto_fail)
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("actor_restrained", ctx.disadvantage_sources)

    def test_restrained_str_no_disadvantage(self):
        ctx = self._mod(["restrained"], "strength")
        self.assertFalse(ctx.auto_fail)
        self.assertEqual(ctx.result, "normal")

    def test_restrained_con_no_disadvantage(self):
        ctx = self._mod(["restrained"], "constitution")
        self.assertEqual(ctx.result, "normal")

    # ── auto-fail takes priority over disadvantage ───────────────────────────
    def test_paralyzed_and_restrained_dex_auto_fail_wins(self):
        # Paralyzed auto-fail is checked before restrained disadvantage
        ctx = self._mod(["paralyzed", "restrained"], "dexterity")
        self.assertTrue(ctx.auto_fail)
        self.assertEqual(ctx.result, "normal")

    # ── case insensitivity ────────────────────────────────────────────────────
    def test_ability_case_insensitive(self):
        ctx_lower = self._mod(["paralyzed"], "strength")
        ctx_upper = modify_saving_throw(_participant(["paralyzed"]), "STRENGTH")
        self.assertEqual(ctx_lower.auto_fail, ctx_upper.auto_fail)


# ─── resolve_spell_attack_kind ───────────────────────────────────────────────


class TestResolveSpellAttackKind(unittest.TestCase):
    """resolve_spell_attack_kind — centralized spell attack kind resolver."""

    def test_no_arg_returns_ranged(self):
        self.assertEqual(resolve_spell_attack_kind(), "ranged")

    def test_empty_dict_returns_ranged(self):
        self.assertEqual(resolve_spell_attack_kind({}), "ranged")

    def test_arbitrary_dict_returns_ranged(self):
        # Metadata is reserved for future use — currently always "ranged"
        self.assertEqual(resolve_spell_attack_kind({"attackKind": "melee"}), "ranged")

    def test_return_value_is_string(self):
        result = resolve_spell_attack_kind()
        self.assertIsInstance(result, str)

    def test_return_value_is_valid_attack_kind(self):
        result = resolve_spell_attack_kind()
        self.assertIn(result, ("melee", "ranged"))


if __name__ == "__main__":
    unittest.main()
