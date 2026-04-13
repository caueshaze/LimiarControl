"""Phase F4.5 — Targeting diagnostics tests.

Tests cover:
  - TargetingDiagnostics dataclass: all methods, compact_log formatting
  - Canonical failure reason constants and ALL_CANONICAL_REASONS sentinel
  - LocalCombatTargetingService: diagnostics attached and checks correct
  - LimiarMapTargetingService: diagnostics attached on both success and failure
  - Multiple failure accumulation
  - Regression: existing targeting API unchanged (is_valid, failure_reason, etc.)
"""

import unittest

from app.models.combat import CombatState, CombatPhase
from app.services.combat_service.targeting_diagnostics import (
    ALL_CANONICAL_REASONS,
    AREA_TARGETING_UNAVAILABLE,
    BLOCKED_BY_CONDITION,
    CHECK_HAS_LINE_OF_EFFECT,
    CHECK_HAS_LINE_OF_SIGHT,
    CHECK_IN_RANGE,
    CHECK_IS_VISIBLE,
    CHECK_TARGET_FOUND,
    CHECK_TARGET_KIND_VALID,
    INVALID_TARGET_TYPE,
    MAP_UNAVAILABLE_FOR_AREA_SPELL,
    MAP_UNREACHABLE,
    NOT_VISIBLE,
    NO_LINE_OF_EFFECT,
    NO_LINE_OF_SIGHT,
    SELF_TARGET_NOT_ALLOWED,
    TARGET_NOT_FOUND,
    TARGET_OUT_OF_REACH,
    TargetingDiagnostics,
)
from app.services.combat_service.targeting_result import TargetingResult
from app.services.combat_service.combat_targeting import (
    LocalCombatTargetingService,
    LimiarMapTargetingService,
)
from app.services.combat_service.targeting_intent import (
    AreaTargetingIntent,
    SpellCastIntent,
    WeaponAttackIntent,
)
from app.integrations.limiar_map_client import (
    LimiarMapClientError,
    LimiarMapTargetingResponse,
)


# ─── helpers ──────────────────────────────────────────────────────────────────


def _make_participant(ref_id: str, kind: str = "player", **kwargs) -> dict:
    p = {"ref_id": ref_id, "kind": kind, "display_name": ref_id}
    p.update(kwargs)
    return p


def _make_state(*participants) -> CombatState:
    return CombatState(
        id="s",
        session_id="sess",
        status="active",
        phase=CombatPhase.active,
        participants=list(participants),
        initiative_order=[],
        current_turn_index=0,
        round_number=1,
        state_json={},
    )


def _weapon_intent(
    actor_ref_id: str = "player-1",
    target_ref_id: str = "enemy-1",
    requires_sight: bool = False,
    weapon_range_type: str = "melee",
) -> WeaponAttackIntent:
    return WeaponAttackIntent(
        session_id="sess",
        action_id="act",
        actor_ref_id=actor_ref_id,
        actor_kind="player",
        requested_target_ref_id=target_ref_id,
        weapon_range_type=weapon_range_type,
        has_reach=False,
        requires_sight=requires_sight,
        requires_effect=False,
    )


def _area_intent(actor_ref_id: str = "player-1") -> AreaTargetingIntent:
    return AreaTargetingIntent(
        session_id="sess",
        action_id="act",
        actor_ref_id=actor_ref_id,
        actor_kind="player",
        requested_target_ref_id=None,
        spell_canonical_key="fireball",
        spell_mode="area",
        shape="sphere",
        size_meters=9,
    )


# ─── TargetingDiagnostics unit tests ──────────────────────────────────────────


class TestTargetingDiagnosticsDataclass(unittest.TestCase):
    def test_default_is_valid(self):
        diag = TargetingDiagnostics()
        self.assertTrue(diag.is_valid)

    def test_default_empty_reasons(self):
        self.assertEqual(TargetingDiagnostics().failure_reasons, [])

    def test_default_empty_checks(self):
        self.assertEqual(TargetingDiagnostics().checks, {})

    def test_default_empty_metadata(self):
        self.assertEqual(TargetingDiagnostics().metadata, {})

    def test_fail_marks_invalid(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_NOT_FOUND)
        self.assertFalse(diag.is_valid)

    def test_fail_appends_reason(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_OUT_OF_REACH)
        self.assertIn(TARGET_OUT_OF_REACH, diag.failure_reasons)

    def test_fail_idempotent_for_same_reason(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_NOT_FOUND)
        diag.fail(TARGET_NOT_FOUND)
        self.assertEqual(diag.failure_reasons.count(TARGET_NOT_FOUND), 1)

    def test_multiple_failures_accumulate(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_OUT_OF_REACH)
        diag.fail(NO_LINE_OF_SIGHT)
        self.assertEqual(len(diag.failure_reasons), 2)
        self.assertIn(TARGET_OUT_OF_REACH, diag.failure_reasons)
        self.assertIn(NO_LINE_OF_SIGHT, diag.failure_reasons)

    def test_set_check_records_pass(self):
        diag = TargetingDiagnostics()
        diag.set_check("target_found", True)
        self.assertTrue(diag.checks["target_found"])

    def test_set_check_records_fail(self):
        diag = TargetingDiagnostics()
        diag.set_check("in_range", False)
        self.assertFalse(diag.checks["in_range"])

    def test_set_check_overwrites(self):
        diag = TargetingDiagnostics()
        diag.set_check("target_found", True)
        diag.set_check("target_found", False)
        self.assertFalse(diag.checks["target_found"])

    def test_set_meta_stores_value(self):
        diag = TargetingDiagnostics()
        diag.set_meta("distance_cells", 3)
        self.assertEqual(diag.metadata["distance_cells"], 3)

    def test_primary_failure_first_reason(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_OUT_OF_REACH)
        diag.fail(NO_LINE_OF_SIGHT)
        self.assertEqual(diag.primary_failure(), TARGET_OUT_OF_REACH)

    def test_primary_failure_none_when_valid(self):
        self.assertIsNone(TargetingDiagnostics().primary_failure())


class TestCompactLog(unittest.TestCase):
    def test_valid_no_meta_returns_ok(self):
        diag = TargetingDiagnostics()
        self.assertEqual(diag.compact_log(), "ok")

    def test_valid_with_distance_and_range(self):
        diag = TargetingDiagnostics()
        diag.set_meta("distance_cells", 2)
        diag.set_meta("range_cells", 3)
        log = diag.compact_log()
        self.assertIn("dist=2", log)
        self.assertIn("range=3", log)
        self.assertTrue(log.startswith("ok"))

    def test_valid_with_cover(self):
        diag = TargetingDiagnostics()
        diag.set_meta("cover", "half_cover")
        self.assertIn("cover=half_cover", diag.compact_log())

    def test_invalid_single_reason(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_OUT_OF_REACH)
        self.assertIn(TARGET_OUT_OF_REACH, diag.compact_log())

    def test_invalid_multiple_reasons_joined(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_OUT_OF_REACH)
        diag.fail(NO_LINE_OF_SIGHT)
        log = diag.compact_log()
        self.assertIn(TARGET_OUT_OF_REACH, log)
        self.assertIn(NO_LINE_OF_SIGHT, log)

    def test_invalid_with_metadata(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_OUT_OF_REACH)
        diag.set_meta("distance_cells", 3)
        diag.set_meta("range_cells", 1)
        log = diag.compact_log()
        self.assertIn("dist=3", log)
        self.assertIn("range=1", log)


class TestCanonicalReasons(unittest.TestCase):
    def test_all_canonical_reasons_is_frozenset(self):
        self.assertIsInstance(ALL_CANONICAL_REASONS, frozenset)

    def test_all_required_reasons_present(self):
        required = {
            TARGET_NOT_FOUND,
            INVALID_TARGET_TYPE,
            AREA_TARGETING_UNAVAILABLE,
            TARGET_OUT_OF_REACH,
            NO_LINE_OF_SIGHT,
            NO_LINE_OF_EFFECT,
            NOT_VISIBLE,
            BLOCKED_BY_CONDITION,
            SELF_TARGET_NOT_ALLOWED,
            MAP_UNREACHABLE,
        }
        self.assertTrue(required.issubset(ALL_CANONICAL_REASONS))

    def test_reasons_are_strings(self):
        for reason in ALL_CANONICAL_REASONS:
            with self.subTest(reason=reason):
                self.assertIsInstance(reason, str)

    def test_reasons_are_snake_case(self):
        for reason in ALL_CANONICAL_REASONS:
            with self.subTest(reason=reason):
                self.assertEqual(reason, reason.lower())
                self.assertNotIn(" ", reason)


# ─── TargetingResult.diagnostics integration ──────────────────────────────────


class TestTargetingResultDiagnosticsField(unittest.TestCase):
    def test_invalid_result_accepts_diagnostics(self):
        diag = TargetingDiagnostics()
        diag.fail(TARGET_NOT_FOUND)
        result = TargetingResult.invalid("Target not found.", diagnostics=diag)
        self.assertIs(result.diagnostics, diag)

    def test_invalid_result_without_diagnostics_is_none(self):
        result = TargetingResult.invalid("Target not found.")
        self.assertIsNone(result.diagnostics)

    def test_valid_result_carries_diagnostics(self):
        diag = TargetingDiagnostics()
        result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="x",
            affected_target_ref_ids=["x"],
            target_kind="player",
            diagnostics=diag,
        )
        self.assertIs(result.diagnostics, diag)

    def test_existing_api_unchanged_is_valid(self):
        result = TargetingResult.invalid("msg")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.failure_reason, "msg")

    def test_existing_api_unchanged_affected_empty(self):
        result = TargetingResult.invalid("msg")
        self.assertEqual(result.affected_target_ref_ids, [])


# ─── LocalCombatTargetingService diagnostics ──────────────────────────────────


class TestLocalServiceDiagnostics(unittest.TestCase):
    def setUp(self):
        self.svc = LocalCombatTargetingService()
        self.attacker = _make_participant("player-1")
        self.target = _make_participant("enemy-1", kind="entity")

    def test_success_has_diagnostics(self):
        state = _make_state(self.attacker, self.target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertIsNotNone(result.diagnostics)

    def test_success_diagnostics_is_valid(self):
        state = _make_state(self.attacker, self.target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertTrue(result.diagnostics.is_valid)

    def test_success_checks_target_found_true(self):
        state = _make_state(self.attacker, self.target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertTrue(result.diagnostics.checks[CHECK_TARGET_FOUND])

    def test_success_checks_target_kind_valid_true(self):
        state = _make_state(self.attacker, self.target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertTrue(result.diagnostics.checks[CHECK_TARGET_KIND_VALID])

    def test_success_failure_reasons_empty(self):
        state = _make_state(self.attacker, self.target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertEqual(result.diagnostics.failure_reasons, [])

    def test_target_not_found_has_canonical_reason(self):
        state = _make_state(self.attacker)  # target absent
        result = self.svc.validate(_weapon_intent(), state)
        self.assertFalse(result.is_valid)
        self.assertIn(TARGET_NOT_FOUND, result.diagnostics.failure_reasons)

    def test_target_not_found_check_is_false(self):
        state = _make_state(self.attacker)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertFalse(result.diagnostics.checks[CHECK_TARGET_FOUND])

    def test_invalid_kind_has_canonical_reason(self):
        bad_target = _make_participant("enemy-1", kind="unknown_kind")
        state = _make_state(self.attacker, bad_target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertFalse(result.is_valid)
        self.assertIn(INVALID_TARGET_TYPE, result.diagnostics.failure_reasons)

    def test_invalid_kind_check_is_false(self):
        bad_target = _make_participant("enemy-1", kind="unknown_kind")
        state = _make_state(self.attacker, bad_target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertFalse(result.diagnostics.checks[CHECK_TARGET_KIND_VALID])

    def test_area_intent_has_canonical_reason(self):
        state = _make_state(self.attacker, self.target)
        result = self.svc.validate(_area_intent(), state)
        self.assertFalse(result.is_valid)
        self.assertIn(
            MAP_UNAVAILABLE_FOR_AREA_SPELL, result.diagnostics.failure_reasons
        )

    def test_sight_not_required_los_check_passes(self):
        state = _make_state(self.attacker, self.target)
        intent = _weapon_intent(requires_sight=False)
        result = self.svc.validate(intent, state)
        self.assertTrue(result.diagnostics.checks[CHECK_HAS_LINE_OF_SIGHT])
        self.assertTrue(result.diagnostics.checks[CHECK_IS_VISIBLE])

    def test_compact_log_ok_on_success(self):
        state = _make_state(self.attacker, self.target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertTrue(result.diagnostics.compact_log().startswith("ok"))

    def test_compact_log_has_reason_on_failure(self):
        state = _make_state(self.attacker)
        result = self.svc.validate(_weapon_intent(), state)
        log = result.diagnostics.compact_log()
        self.assertIn(TARGET_NOT_FOUND, log)

    def test_primary_failure_matches_failure_reason(self):
        state = _make_state(self.attacker)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertEqual(
            result.diagnostics.primary_failure(),
            result.diagnostics.failure_reasons[0],
        )

    def test_diagnostics_is_valid_matches_result_is_valid_on_success(self):
        state = _make_state(self.attacker, self.target)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertEqual(result.diagnostics.is_valid, result.is_valid)

    def test_diagnostics_is_valid_matches_result_is_valid_on_failure(self):
        state = _make_state(self.attacker)
        result = self.svc.validate(_weapon_intent(), state)
        self.assertEqual(result.diagnostics.is_valid, result.is_valid)


# ─── LimiarMapTargetingService diagnostics ────────────────────────────────────


class StubMapClient:
    """Minimal LimiarMap client stub."""

    def __init__(
        self,
        *,
        is_valid: bool = True,
        reason: str | None = None,
        cover: str | None = None,
        error: Exception | None = None,
        source_token_id: str = "tok-src",
        target_token_id: str = "tok-tgt",
    ) -> None:
        self._response = LimiarMapTargetingResponse(
            is_valid=is_valid,
            reason=reason,
            session_id="sess",
            action_id="act",
            source_token_id=source_token_id,
            target_token_id=target_token_id,
            version=1,
            cover=cover,
        )
        self._error = error

    def validate_single_target(
        self,
        *,
        session_id,
        action_id,
        combatant_id,
        target_combatant_id,
        range_cells,
        requires_sight=False,
        requires_effect=False,
    ):
        if self._error:
            raise self._error
        return self._response


class TestLimiarMapServiceDiagnostics(unittest.TestCase):
    def _svc(self, **kwargs) -> LimiarMapTargetingService:
        return LimiarMapTargetingService(StubMapClient(**kwargs))

    def _state(self):
        attacker = _make_participant("player-1")
        target = _make_participant("enemy-1", kind="entity")
        return _make_state(attacker, target)

    def test_success_diagnostics_attached(self):
        result = self._svc().validate(_weapon_intent(), self._state())
        self.assertIsNotNone(result.diagnostics)

    def test_success_diagnostics_is_valid(self):
        result = self._svc().validate(_weapon_intent(), self._state())
        self.assertTrue(result.diagnostics.is_valid)

    def test_success_checks_in_range_true(self):
        result = self._svc().validate(_weapon_intent(), self._state())
        self.assertTrue(result.diagnostics.checks.get(CHECK_IN_RANGE))

    def test_success_checks_los_true(self):
        result = self._svc().validate(_weapon_intent(), self._state())
        self.assertTrue(result.diagnostics.checks.get(CHECK_HAS_LINE_OF_SIGHT))

    def test_success_checks_loe_true(self):
        result = self._svc().validate(_weapon_intent(), self._state())
        self.assertTrue(result.diagnostics.checks.get(CHECK_HAS_LINE_OF_EFFECT))

    def test_success_with_cover_stored_in_metadata(self):
        result = self._svc(cover="half_cover").validate(_weapon_intent(), self._state())
        self.assertEqual(result.diagnostics.metadata.get("cover"), "half_cover")

    def test_map_out_of_range_has_canonical_reason(self):
        result = self._svc(is_valid=False, reason="out_of_range").validate(
            _weapon_intent(), self._state()
        )
        self.assertIn(TARGET_OUT_OF_REACH, result.diagnostics.failure_reasons)

    def test_map_out_of_range_check_in_range_false(self):
        result = self._svc(is_valid=False, reason="out_of_range").validate(
            _weapon_intent(), self._state()
        )
        self.assertFalse(result.diagnostics.checks.get(CHECK_IN_RANGE))

    def test_map_no_los_has_canonical_reason(self):
        result = self._svc(is_valid=False, reason="no_line_of_sight").validate(
            _weapon_intent(), self._state()
        )
        self.assertIn(NO_LINE_OF_SIGHT, result.diagnostics.failure_reasons)

    def test_map_no_los_check_los_false(self):
        result = self._svc(is_valid=False, reason="no_line_of_sight").validate(
            _weapon_intent(), self._state()
        )
        self.assertFalse(result.diagnostics.checks.get(CHECK_HAS_LINE_OF_SIGHT))

    def test_map_no_loe_has_canonical_reason(self):
        result = self._svc(is_valid=False, reason="no_line_of_effect").validate(
            _weapon_intent(), self._state()
        )
        self.assertIn(NO_LINE_OF_EFFECT, result.diagnostics.failure_reasons)

    def test_map_full_cover_has_no_line_of_effect_reason(self):
        result = self._svc(is_valid=False, reason="full_cover").validate(
            _weapon_intent(), self._state()
        )
        self.assertIn(NO_LINE_OF_EFFECT, result.diagnostics.failure_reasons)

    def test_map_error_falls_back_diagnostics_attached(self):
        result = self._svc(
            error=LimiarMapClientError("network error", kind="network")
        ).validate(_weapon_intent(), self._state())
        # Falls back to local — result is still valid (target found)
        self.assertTrue(result.is_valid)
        self.assertIsNotNone(result.diagnostics)

    def test_map_error_sets_map_fallback_meta(self):
        result = self._svc(
            error=LimiarMapClientError("timeout", kind="network")
        ).validate(_weapon_intent(), self._state())
        self.assertTrue(result.diagnostics.metadata.get("map_fallback"))

    def test_range_cells_stored_in_metadata(self):
        intent = WeaponAttackIntent(
            session_id="sess",
            action_id="act",
            actor_ref_id="player-1",
            actor_kind="player",
            requested_target_ref_id="enemy-1",
            weapon_range_type="melee",
            has_reach=False,
            requires_sight=False,
            requires_effect=False,
        )
        result = self._svc().validate(intent, self._state())
        # Melee default reach = 1
        self.assertEqual(result.diagnostics.metadata.get("range_cells"), 1)

    def test_local_failure_propagated_to_caller(self):
        # Target not in state → local rejects → LimiarMap service returns it as-is
        state = _make_state(_make_participant("player-1"))  # no target
        result = self._svc().validate(_weapon_intent(), state)
        self.assertFalse(result.is_valid)
        self.assertIn(TARGET_NOT_FOUND, result.diagnostics.failure_reasons)

    def test_map_failure_diagnostics_compact_log_has_reason(self):
        result = self._svc(is_valid=False, reason="out_of_range").validate(
            _weapon_intent(), self._state()
        )
        self.assertIn(TARGET_OUT_OF_REACH, result.diagnostics.compact_log())


# ─── Regression: existing API contract unchanged ──────────────────────────────


class TestDiagnosticsRegressionContract(unittest.TestCase):
    """Verify that adding diagnostics does NOT break any existing API."""

    def setUp(self):
        self.svc = LocalCombatTargetingService()
        self.attacker = _make_participant("player-1")
        self.target = _make_participant("enemy-1", kind="entity")

    def test_is_valid_true_on_success(self):
        state = _make_state(self.attacker, self.target)
        r = self.svc.validate(_weapon_intent(), state)
        self.assertTrue(r.is_valid)

    def test_failure_reason_is_none_on_success(self):
        state = _make_state(self.attacker, self.target)
        r = self.svc.validate(_weapon_intent(), state)
        self.assertIsNone(r.failure_reason)

    def test_validated_primary_target_ref_id_correct(self):
        state = _make_state(self.attacker, self.target)
        r = self.svc.validate(_weapon_intent(), state)
        self.assertEqual(r.validated_primary_target_ref_id, "enemy-1")

    def test_affected_target_ref_ids_single_entry(self):
        state = _make_state(self.attacker, self.target)
        r = self.svc.validate(_weapon_intent(), state)
        self.assertEqual(r.affected_target_ref_ids, ["enemy-1"])

    def test_target_kind_correct(self):
        state = _make_state(self.attacker, self.target)
        r = self.svc.validate(_weapon_intent(), state)
        self.assertEqual(r.target_kind, "entity")

    def test_failure_reason_present_on_failure(self):
        state = _make_state(self.attacker)
        r = self.svc.validate(_weapon_intent(), state)
        self.assertFalse(r.is_valid)
        self.assertIsNotNone(r.failure_reason)

    def test_spatial_metadata_is_always_present(self):
        state = _make_state(self.attacker, self.target)
        r = self.svc.validate(_weapon_intent(), state)
        self.assertIsNotNone(r.spatial_metadata)

    def test_targeting_authority_local(self):
        state = _make_state(self.attacker, self.target)
        r = self.svc.validate(_weapon_intent(), state)
        self.assertEqual(r.spatial_metadata.targeting_authority, "local")


if __name__ == "__main__":
    unittest.main()
