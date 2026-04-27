"""Tests for per-instance spatial validation in multi-instance spell casts.

Covers:
  - _validate_instance_spatial_targets validates range/LoS/LoE per unique target
  - Deduplication: each unique targetRefId validated once, even with multiple instances
  - First instance_index using a failing target is cited in the error
  - CombatServiceError raised before resource consumption
  - Correct error phrase for each failure reason
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.targeting_diagnostics import (
    NO_LINE_OF_EFFECT,
    NO_LINE_OF_SIGHT,
    NOT_VISIBLE,
    TARGET_OUT_OF_REACH,
    TargetingDiagnostics,
)
from app.services.combat_service.targeting_result import TargetingResult


def _build_state(use_map=True):
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        use_map=use_map,
        participants=[
            {"id": "p1", "ref_id": "player-1", "kind": "player", "display_name": "Hero", "status": "active", "team": "players", "visible": True, "actor_user_id": "user-1"},
            {"id": "e1", "ref_id": "entity:goblin-a", "kind": "session_entity", "display_name": "Goblin A", "status": "active", "team": "enemies", "visible": True, "actor_user_id": None},
            {"id": "e2", "ref_id": "entity:goblin-b", "kind": "session_entity", "display_name": "Goblin B", "status": "active", "team": "enemies", "visible": True, "actor_user_id": None},
            {"id": "e3", "ref_id": "entity:orc-c", "kind": "session_entity", "display_name": "Orc C", "status": "active", "team": "enemies", "visible": True, "actor_user_id": None},
        ],
    )


def _build_attacker():
    return {"ref_id": "player-1", "kind": "player", "display_name": "Hero"}


def _build_spell_context(range_meters=36, requires_sight=True, requires_effect=True):
    return {
        "effect_instance_count": 5,
        "effect_instance_dice": "1d4+1",
        "spell_mode": "direct_damage",
        "spell_canonical_key": "magic_missile",
        "spell_name": "Magic Missile",
        "range_meters": range_meters,
        "requires_target_sight": requires_sight,
        "requires_target_effect": requires_effect,
        "target_type": "ranged",
        "selection_type": "creature",
        "attack_type": None,
        "range_kind": None,
        "area_shape": None,
    }


def _make_validated_target(instance_index: int, target_ref_id: str, display_name: str):
    return {
        "instance_index": instance_index,
        "target_ref_id": target_ref_id,
        "participant": {"ref_id": target_ref_id, "display_name": display_name, "kind": "session_entity"},
    }


def _valid_result(target_ref_id: str = "entity:goblin-a") -> TargetingResult:
    return TargetingResult(
        is_valid=True,
        validated_primary_target_ref_id=target_ref_id,
        affected_target_ref_ids=[target_ref_id],
        target_kind="session_entity",
    )


def _invalid_result(reason_constant: str) -> TargetingResult:
    diag = TargetingDiagnostics()
    diag.fail(reason_constant)
    return TargetingResult.invalid(reason=reason_constant, diagnostics=diag)


class ValidateInstanceSpatialTargetsTests(unittest.TestCase):
    def _call(self, validated_targets, state=None, spell_context=None, mock_service=None):
        state = state or _build_state()
        spell_context = spell_context or _build_spell_context()
        with patch(
            "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
            return_value=mock_service or MagicMock(validate=MagicMock(return_value=_valid_result())),
        ):
            CombatService._validate_instance_spatial_targets(
                state=state,
                attacker=_build_attacker(),
                spell_context=spell_context,
                validated_targets=validated_targets,
                session_id="session-1",
            )

    def test_valid_targets_pass_without_error(self):
        targets = [
            _make_validated_target(1, "entity:goblin-a", "Goblin A"),
            _make_validated_target(2, "entity:goblin-b", "Goblin B"),
        ]
        # Should not raise
        self._call(targets)

    def test_out_of_range_raises_with_instance_index(self):
        mock_svc = MagicMock()
        mock_svc.validate.side_effect = [
            _valid_result("entity:goblin-a"),
            _invalid_result(TARGET_OUT_OF_REACH),
        ]
        targets = [
            _make_validated_target(1, "entity:goblin-a", "Goblin A"),
            _make_validated_target(2, "entity:goblin-b", "Goblin B"),
        ]
        with patch(
            "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
            return_value=mock_svc,
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                CombatService._validate_instance_spatial_targets(
                    state=_build_state(),
                    attacker=_build_attacker(),
                    spell_context=_build_spell_context(),
                    validated_targets=targets,
                    session_id="session-1",
                )
        self.assertIn("Instance 2", ctx.exception.detail)
        self.assertIn("out of range", ctx.exception.detail)
        self.assertIn("Goblin B", ctx.exception.detail)

    def test_blocked_los_raises_with_correct_phrase(self):
        mock_svc = MagicMock(validate=MagicMock(return_value=_invalid_result(NO_LINE_OF_SIGHT)))
        targets = [_make_validated_target(3, "entity:orc-c", "Orc C")]
        with patch(
            "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
            return_value=mock_svc,
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                CombatService._validate_instance_spatial_targets(
                    state=_build_state(),
                    attacker=_build_attacker(),
                    spell_context=_build_spell_context(),
                    validated_targets=targets,
                    session_id="session-1",
                )
        self.assertIn("Instance 3", ctx.exception.detail)
        self.assertIn("blocked line of sight", ctx.exception.detail)

    def test_blocked_loe_raises_with_correct_phrase(self):
        mock_svc = MagicMock(validate=MagicMock(return_value=_invalid_result(NO_LINE_OF_EFFECT)))
        targets = [_make_validated_target(4, "entity:goblin-a", "Goblin A")]
        with patch(
            "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
            return_value=mock_svc,
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                CombatService._validate_instance_spatial_targets(
                    state=_build_state(),
                    attacker=_build_attacker(),
                    spell_context=_build_spell_context(),
                    validated_targets=targets,
                    session_id="session-1",
                )
        self.assertIn("blocked line of effect", ctx.exception.detail)

    def test_deduplicates_validation_by_target_ref_id(self):
        # 5 instances, 2 unique targets (goblin-a x3, goblin-b x2)
        targets = [
            _make_validated_target(1, "entity:goblin-a", "Goblin A"),
            _make_validated_target(2, "entity:goblin-a", "Goblin A"),
            _make_validated_target(3, "entity:goblin-a", "Goblin A"),
            _make_validated_target(4, "entity:goblin-b", "Goblin B"),
            _make_validated_target(5, "entity:goblin-b", "Goblin B"),
        ]
        mock_svc = MagicMock(validate=MagicMock(return_value=_valid_result()))
        with patch(
            "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
            return_value=mock_svc,
        ):
            CombatService._validate_instance_spatial_targets(
                state=_build_state(),
                attacker=_build_attacker(),
                spell_context=_build_spell_context(),
                validated_targets=targets,
                session_id="session-1",
            )
        # Must call validate exactly twice (one per unique target), not 5 times
        self.assertEqual(mock_svc.validate.call_count, 2)

    def test_first_instance_index_reported_for_shared_failing_target(self):
        # goblin-b appears in instances 2 and 4; instance 2 is first
        mock_svc = MagicMock()
        mock_svc.validate.side_effect = [
            _valid_result("entity:goblin-a"),
            _invalid_result(TARGET_OUT_OF_REACH),
        ]
        targets = [
            _make_validated_target(1, "entity:goblin-a", "Goblin A"),
            _make_validated_target(2, "entity:goblin-b", "Goblin B"),
            _make_validated_target(3, "entity:goblin-a", "Goblin A"),
            _make_validated_target(4, "entity:goblin-b", "Goblin B"),
        ]
        with patch(
            "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
            return_value=mock_svc,
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                CombatService._validate_instance_spatial_targets(
                    state=_build_state(),
                    attacker=_build_attacker(),
                    spell_context=_build_spell_context(),
                    validated_targets=targets,
                    session_id="session-1",
                )
        # First instance to use goblin-b is instance 2
        self.assertIn("Instance 2", ctx.exception.detail)

    def test_targeting_service_selected_based_on_use_map_flag(self):
        targets = [_make_validated_target(1, "entity:goblin-a", "Goblin A")]
        with patch(
            "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
            return_value=MagicMock(validate=MagicMock(return_value=_valid_result())),
        ) as mock_factory:
            CombatService._validate_instance_spatial_targets(
                state=_build_state(use_map=False),
                attacker=_build_attacker(),
                spell_context=_build_spell_context(),
                validated_targets=targets,
                session_id="session-1",
            )
        mock_factory.assert_called_once_with(False)

    def test_resolve_multi_instance_not_called_on_spatial_failure(self):
        # Spatial failure must prevent _resolve_multi_instance_cast from running
        mock_svc = MagicMock(validate=MagicMock(return_value=_invalid_result(TARGET_OUT_OF_REACH)))
        targets = [_make_validated_target(1, "entity:goblin-a", "Goblin A")]
        with patch(
            "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
            return_value=mock_svc,
        ):
            with patch.object(
                CombatService, "_resolve_multi_instance_cast", new_callable=MagicMock
            ) as mock_resolve:
                with self.assertRaises(CombatServiceError):
                    CombatService._validate_instance_spatial_targets(
                        state=_build_state(),
                        attacker=_build_attacker(),
                        spell_context=_build_spell_context(),
                        validated_targets=targets,
                        session_id="session-1",
                    )
                mock_resolve.assert_not_called()
