"""Tests for local (non-map) targeting range validation.

Covers:
  - derive_max_range_meters: range derivation for all weapon/spell types
  - LocalCombatTargetingService: range validation with local_distances
  - Edge cases: self spells, touch, melee reach, ranged, missing config
  - Regression: map-backed targeting unchanged
"""

import unittest

from app.models.combat import CombatState, CombatPhase
from app.services.combat_service.reach import (
    derive_max_range_meters,
    WEAPON_RANGE_NOT_CONFIGURED,
    SPELL_RANGE_NOT_CONFIGURED,
    TOUCH_RANGE_METERS,
)
from app.services.combat_service.targeting_diagnostics import (
    CHECK_IN_RANGE,
    SPELL_RANGE_NOT_CONFIGURED as DIAG_SPELL_RANGE_NOT_CONFIGURED,
    TARGET_OUT_OF_REACH,
    WEAPON_RANGE_NOT_CONFIGURED as DIAG_WEAPON_RANGE_NOT_CONFIGURED,
)
from app.services.combat_service.combat_targeting import (
    LocalCombatTargetingService,
)
from app.services.combat_service.targeting_intent import (
    SpellCastIntent,
    WeaponAttackIntent,
)


def _make_participant(ref_id: str, kind: str = "player", **kwargs) -> dict:
    p = {"ref_id": ref_id, "kind": kind, "display_name": ref_id}
    p.update(kwargs)
    return p


def _make_state(
    *participants,
    local_distances: dict | None = None,
) -> CombatState:
    return CombatState(
        id="s",
        session_id="sess",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=list(participants),
        local_distances=local_distances or {},
    )


def _weapon_intent(
    actor_ref_id: str = "player-1",
    target_ref_id: str = "enemy-1",
    *,
    range_meters: int | None = None,
    weapon_range_type: str | None = "melee",
    has_reach: bool = False,
    requires_sight: bool = False,
) -> WeaponAttackIntent:
    return WeaponAttackIntent(
        session_id="sess",
        action_id="act",
        actor_ref_id=actor_ref_id,
        actor_kind="player",
        requested_target_ref_id=target_ref_id,
        range_meters=range_meters,
        weapon_range_type=weapon_range_type,
        has_reach=has_reach,
        requires_sight=requires_sight,
        requires_effect=False,
    )


def _spell_intent(
    actor_ref_id: str = "player-1",
    target_ref_id: str = "enemy-1",
    *,
    range_meters: int | None = None,
    target_mode: str | None = None,
    spell_mode: str = "spell_attack",
    requires_sight: bool = False,
) -> SpellCastIntent:
    return SpellCastIntent(
        session_id="sess",
        action_id="act",
        actor_ref_id=actor_ref_id,
        actor_kind="player",
        requested_target_ref_id=target_ref_id,
        spell_canonical_key="test_spell",
        spell_mode=spell_mode,
        target_mode=target_mode,
        range_meters=range_meters,
        requires_sight=requires_sight,
        requires_effect=False,
    )


svc = LocalCombatTargetingService()


# ── derive_max_range_meters unit tests ──────────────────────────────────────


class TestDeriveMaxRangeMeters(unittest.TestCase):
    def test_self_target_mode_returns_none(self):
        r, fail = derive_max_range_meters(target_mode="self")
        self.assertIsNone(r)
        self.assertIsNone(fail)

    def test_touch_target_mode_returns_1_5(self):
        r, fail = derive_max_range_meters(target_mode="touch")
        self.assertAlmostEqual(r, TOUCH_RANGE_METERS)
        self.assertIsNone(fail)

    def test_ranged_with_range_meters(self):
        r, fail = derive_max_range_meters(range_meters=18, weapon_range_type="ranged")
        self.assertEqual(r, 18.0)
        self.assertIsNone(fail)

    def test_ranged_without_range_meters_fails(self):
        r, fail = derive_max_range_meters(weapon_range_type="ranged")
        self.assertIsNone(r)
        self.assertEqual(fail, WEAPON_RANGE_NOT_CONFIGURED)

    def test_melee_default_1_5m(self):
        r, fail = derive_max_range_meters(weapon_range_type="melee")
        self.assertAlmostEqual(r, TOUCH_RANGE_METERS)
        self.assertIsNone(fail)

    def test_melee_reach_3m(self):
        r, fail = derive_max_range_meters(weapon_range_type="melee", has_reach=True)
        self.assertAlmostEqual(r, TOUCH_RANGE_METERS * 2)
        self.assertIsNone(fail)

    def test_range_meters_zero_treated_as_touch(self):
        r, fail = derive_max_range_meters(range_meters=0)
        self.assertAlmostEqual(r, TOUCH_RANGE_METERS)
        self.assertIsNone(fail)

    def test_spell_ranged_with_range(self):
        r, fail = derive_max_range_meters(range_meters=36, target_mode="ranged")
        self.assertEqual(r, 36.0)
        self.assertIsNone(fail)

    def test_ranged_spell_without_range_meters_fails_safely(self):
        r, fail = derive_max_range_meters(target_mode="ranged")
        self.assertIsNone(r)
        self.assertEqual(fail, SPELL_RANGE_NOT_CONFIGURED)

    def test_no_info_returns_none(self):
        r, fail = derive_max_range_meters()
        self.assertIsNone(r)
        self.assertIsNone(fail)

    def test_range_meters_takes_priority_over_melee_type(self):
        r, fail = derive_max_range_meters(range_meters=9, weapon_range_type="melee")
        self.assertEqual(r, 9.0)
        self.assertIsNone(fail)


# ── LocalCombatTargetingService range validation tests ─────────────────────


class TestLocalMeleeRangeValidation(unittest.TestCase):
    def setUp(self):
        self.state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 1.5, "enemy-2": 3.0}},
        )

    def test_melee_default_in_range(self):
        intent = _weapon_intent(weapon_range_type="melee", has_reach=False)
        result = svc.validate(intent, self.state)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.diagnostics.checks.get(CHECK_IN_RANGE))

    def test_melee_default_out_of_range(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 3.0}},
        )
        intent = _weapon_intent(weapon_range_type="melee", has_reach=False)
        result = svc.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIn(TARGET_OUT_OF_REACH, result.diagnostics.failure_reasons)

    def test_melee_reach_in_range(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 3.0}},
        )
        intent = _weapon_intent(weapon_range_type="melee", has_reach=True)
        result = svc.validate(intent, state)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.diagnostics.checks.get(CHECK_IN_RANGE))


class TestLocalRangedRangeValidation(unittest.TestCase):
    def test_ranged_weapon_in_range(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 9.0}},
        )
        intent = _weapon_intent(range_meters=18, weapon_range_type="ranged")
        result = svc.validate(intent, state)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.diagnostics.checks.get(CHECK_IN_RANGE))

    def test_ranged_weapon_out_of_range(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 20.0}},
        )
        intent = _weapon_intent(range_meters=18, weapon_range_type="ranged")
        result = svc.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIn(TARGET_OUT_OF_REACH, result.diagnostics.failure_reasons)
        self.assertIn("out of range", result.failure_reason.lower())
        self.assertIn("20.0m", result.failure_reason)
        self.assertIn("18.0m", result.failure_reason)
        self.assertEqual(result.diagnostics.metadata.get("distance_meters"), 20.0)
        self.assertEqual(result.diagnostics.metadata.get("max_range_meters"), 18.0)

    def test_ranged_weapon_without_range_meters_fails(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 5.0}},
        )
        intent = _weapon_intent(range_meters=None, weapon_range_type="ranged")
        result = svc.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIn(
            DIAG_WEAPON_RANGE_NOT_CONFIGURED, result.diagnostics.failure_reasons
        )
        self.assertIn("Ranged weapon has no range configured", result.failure_reason)


class TestLocalNoDistanceConfigured(unittest.TestCase):
    def test_ranged_without_distance_configured_fails(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={},
        )
        intent = _weapon_intent(range_meters=18, weapon_range_type="ranged")
        result = svc.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIn(TARGET_OUT_OF_REACH, result.diagnostics.failure_reasons)
        self.assertIn("GM must set", result.failure_reason)


class TestLocalSpellRangeValidation(unittest.TestCase):
    def test_self_spell_no_range_check(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={},
        )
        intent = _spell_intent(target_mode="self", target_ref_id="player-1")
        result = svc.validate(intent, state)
        self.assertTrue(result.is_valid)

    def test_touch_spell_in_range(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 1.5}},
        )
        intent = _spell_intent(target_mode="touch", range_meters=None)
        result = svc.validate(intent, state)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.diagnostics.checks.get(CHECK_IN_RANGE))

    def test_touch_spell_out_of_range(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 4.5}},
        )
        intent = _spell_intent(target_mode="touch", range_meters=None)
        result = svc.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIn(TARGET_OUT_OF_REACH, result.diagnostics.failure_reasons)

    def test_ranged_spell_in_range(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 30.0}},
        )
        intent = _spell_intent(range_meters=36, target_mode="ranged")
        result = svc.validate(intent, state)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.diagnostics.checks.get(CHECK_IN_RANGE))

    def test_ranged_spell_out_of_range(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 40.0}},
        )
        intent = _spell_intent(range_meters=36, target_mode="ranged")
        result = svc.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIn(TARGET_OUT_OF_REACH, result.diagnostics.failure_reasons)
        self.assertIn("40.0m", result.failure_reason)
        self.assertIn("36.0m", result.failure_reason)

    def test_ranged_spell_missing_distance_fails_clearly(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={},
        )
        intent = _spell_intent(range_meters=36, target_mode="ranged")
        result = svc.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIn(TARGET_OUT_OF_REACH, result.diagnostics.failure_reasons)
        self.assertIn("GM must set combat distances", result.failure_reason)

    def test_ranged_spell_without_range_meters_fails_safely(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 12.0}},
        )
        intent = _spell_intent(range_meters=None, target_mode="ranged")
        result = svc.validate(intent, state)
        self.assertFalse(result.is_valid)
        self.assertIn(
            DIAG_SPELL_RANGE_NOT_CONFIGURED, result.diagnostics.failure_reasons
        )
        self.assertIn("Spell range is not configured", result.failure_reason)


class TestLocalNoConstraintSkipsRange(unittest.TestCase):
    def test_action_without_range_info_skips_check(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={},
        )
        intent = WeaponAttackIntent(
            session_id="sess",
            action_id="act",
            actor_ref_id="player-1",
            actor_kind="player",
            requested_target_ref_id="enemy-1",
        )
        result = svc.validate(intent, state)
        self.assertTrue(result.is_valid)

    def test_range_meters_zero_treated_as_touch(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"player-1": {"enemy-1": 1.5}},
        )
        intent = _spell_intent(range_meters=0)
        result = svc.validate(intent, state)
        self.assertTrue(result.is_valid)


class TestLocalSymmetricDistanceLookup(unittest.TestCase):
    def test_distance_found_in_reverse_direction(self):
        state = _make_state(
            _make_participant("player-1", "player"),
            _make_participant("enemy-1", "session_entity"),
            local_distances={"enemy-1": {"player-1": 1.5}},
        )
        intent = _weapon_intent(weapon_range_type="melee")
        result = svc.validate(intent, state)
        self.assertTrue(result.is_valid)
