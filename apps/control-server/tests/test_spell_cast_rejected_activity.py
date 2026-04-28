from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.schemas.combat import CombatCastSpellRequest
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.targeting_diagnostics import NO_LINE_OF_EFFECT, NO_LINE_OF_SIGHT, TARGET_OUT_OF_REACH, TargetingDiagnostics
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult


def _invalid_result(reason: str) -> TargetingResult:
    diag = TargetingDiagnostics(is_valid=False, failure_reasons=[reason])
    return TargetingResult(
        is_valid=False,
        validated_primary_target_ref_id="",
        affected_target_ref_ids=[],
        target_kind="",
        failure_reason="blocked",
        spatial_metadata=SpatialMetadata(),
        diagnostics=diag,
    )


class SpellCastRejectedActivityTests(unittest.TestCase):
    def test_single_target_rejection_records_activity_before_error(self) -> None:
        state = SimpleNamespace(
            use_map=True,
            participants=[
                {"ref_id": "enemy-1", "display_name": "Goblin A", "kind": "session_entity"},
            ],
        )
        attacker = {"ref_id": "player-1", "display_name": "Caue", "actor_user_id": "user-1", "kind": "player"}
        spell_context = {"spell_name": "Eldritch Blast", "spell_canonical_key": "eldritch_blast", "spell_mode": "spell_attack"}
        req = CombatCastSpellRequest(target_ref_id="enemy-1", spell_id="eldritch_blast")

        with (
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service") as get_service,
            patch.object(CombatService, "_record_spell_cast_rejected_activity") as record_activity,
        ):
            get_service.return_value.validate.return_value = _invalid_result(NO_LINE_OF_SIGHT)

            with self.assertRaises(CombatServiceError):
                import asyncio
                asyncio.run(
                    CombatService._resolve_cast_resolution(
                        MagicMock(),
                        "session-1",
                        req,
                        state,
                        attacker,
                        MagicMock(),
                        spell_context,
                        "user-1",
                        False,
                    )
                )

        record_activity.assert_called_once()
        self.assertEqual(record_activity.call_args.kwargs["reason"], "blocked_line_of_sight")
        self.assertEqual(record_activity.call_args.kwargs["target_display_name"], "Goblin A")

    def test_multi_instance_rejection_records_failed_instance_index(self) -> None:
        state = SimpleNamespace(use_map=True)
        attacker = {"ref_id": "player-1", "display_name": "Caue", "actor_user_id": "user-1", "kind": "player"}
        spell_context = {
            "spell_name": "Eldritch Blast",
            "spell_canonical_key": "eldritch_blast",
            "spell_mode": "spell_attack",
            "target_type": "creature",
            "selection_type": "target",
            "attack_type": "ranged",
            "range_kind": "ranged",
            "range_meters": 36,
            "requires_target_sight": True,
            "requires_target_effect": True,
        }
        validated_targets = [
            {
                "instance_index": 2,
                "target_ref_id": "enemy-2",
                "participant": {"ref_id": "enemy-2", "display_name": "Orc B"},
            }
        ]

        with (
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service") as get_service,
            patch.object(CombatService, "_record_spell_cast_rejected_activity") as record_activity,
        ):
            get_service.return_value.validate.return_value = _invalid_result(TARGET_OUT_OF_REACH)

            with self.assertRaises(CombatServiceError):
                CombatService._validate_instance_spatial_targets(
                    db=MagicMock(),
                    state=state,
                    attacker=attacker,
                    spell_context=spell_context,
                    validated_targets=validated_targets,
                    session_id="session-1",
                )

        record_activity.assert_called_once()
        self.assertEqual(record_activity.call_args.kwargs["reason"], "out_of_range")
        self.assertEqual(record_activity.call_args.kwargs["instance_index"], 2)

    def test_area_rejection_records_area_origin(self) -> None:
        state = SimpleNamespace(use_map=True, participants=[])
        attacker = {"ref_id": "player-1", "display_name": "Caue", "kind": "player"}
        spell_context = {
            "spell_name": "Fireball",
            "spell_canonical_key": "fireball",
            "spell_mode": "saving_throw",
            "effect_kind": "damage",
            "requires_point_sight": False,
            "requires_point_effect": True,
        }
        area_spec = {"shape": "sphere", "size_meters": 6, "range_meters": 45}
        req = CombatCastSpellRequest(
            spell_id="fireball",
            anchor_cell={"x": 12, "y": 8},
        )

        with (
            patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service") as get_service,
            patch.object(CombatService, "_record_spell_cast_rejected_activity") as record_activity,
        ):
            get_service.return_value.validate.return_value = _invalid_result(NO_LINE_OF_EFFECT)

            with self.assertRaises(CombatServiceError):
                import asyncio
                asyncio.run(
                    CombatService._cast_area_spell(
                        MagicMock(),
                        "session-1",
                        req,
                        attacker=attacker,
                        attacker_model=MagicMock(),
                        actor_user_id="user-1",
                        is_gm=False,
                        state=state,
                        spell_context=spell_context,
                        area_spec=area_spec,
                    )
                )

        record_activity.assert_called_once()
        self.assertEqual(record_activity.call_args.kwargs["reason"], "blocked_line_of_effect")
        self.assertEqual(record_activity.call_args.kwargs["area_origin"], {"x": 12, "y": 8})


if __name__ == "__main__":
    unittest.main()
