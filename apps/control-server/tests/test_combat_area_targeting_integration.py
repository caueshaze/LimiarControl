from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell, CombatResolveSpellEffectRequest
from app.schemas.roll import RollActorStats
from app.services.combat import CombatService
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult


class CombatAreaTargetingIntegrationTests(TestCombatServiceBase):
    @patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat_service.spells.cast_area.resolve_saving_throw")
    async def test_fireball_area_targeting_flows_through_map_and_applies_damage_per_target(
        self,
        mock_resolve_saving_throw,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "abilities": {"charisma": 18},
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Fireball",
                            "canonicalKey": "fireball",
                            "level": 3,
                            "prepared": True,
                        }
                    ],
                    "slots": {"3": {"used": 0, "max": 2}},
                },
            },
        )
        map_targeting_result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="enemy-123",
            affected_target_ref_ids=["player-123", "enemy-123"],
            target_kind="session_entity",
            spatial_metadata=SpatialMetadata(
                source_token_id="tok_player",
                affected_token_ids=["tok_player", "tok_enemy"],
                affected_cells=[{"x": 10, "y": 10}, {"x": 10, "y": 9}],
                area_shape="sphere",
                map_version=12,
                targeting_authority="limiar_map",
            ),
        )

        def get_stats_side_effect(_db, ref_id, kind, _session_id=""):
            if ref_id == "player-123" and kind == "player":
                return (attacker_state, 12, 10, 10, 3, 4)
            if ref_id == "enemy-123" and kind == "session_entity":
                return (MagicMock(), 13, 10, 10, 2, 0)
            raise AssertionError(f"Unexpected get_stats call for {ref_id}/{kind}")

        mock_resolve_saving_throw.side_effect = [
            MagicMock(total=14, success=True),
            MagicMock(total=7, success=False),
        ]

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="fireball",
                name_en="Fireball",
                name_pt="Bola de Fogo",
                level=3,
                resolution_type="saving_throw",
                saving_throw="dexterity",
                save_success_outcome="half_damage",
                damage_type="fire",
                damage_dice="8d6",
                heal_dice=None,
                upcast_json=None,
                casting_time_type="action",
                target_type="ranged", area_shape="sphere",
                range_meters=45,
                radius_meters=6,
            ),
        ), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=get_stats_side_effect,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=RollActorStats(
                display_name="Target",
                abilities={"dexterity": 10},
                actor_kind="session_entity",
                actor_ref_id="enemy-123",
            ),
        ), patch(
            "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
            return_value=SimpleNamespace(validate=MagicMock(return_value=map_targeting_result)),
        ):
            first_result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="fireball",
                ),
                "user-1",
                False,
            )

            self.assertTrue(first_result["effect_roll_required"])
            self.assertEqual(first_result["area_shape"], "sphere")
            self.assertEqual(first_result["affected_target_ref_ids"], ["player-123", "enemy-123"])
            self.assertEqual(first_result["target_count"], 2)
            self.assertEqual(
                [outcome["target_ref_id"] for outcome in first_result["area_target_outcomes"]],
                ["player-123", "enemy-123"],
            )
            self.assertEqual(self.state.participants[0]["pending_attack"]["area_shape"], "sphere")

            with patch(
                "app.services.combat.CombatService._apply_damage_to_target",
                side_effect=[
                    (14, "", 20, None),
                    (5, "", 16, None),
                ],
            ) as mock_apply_damage:
                second_result = await CombatService.cast_spell_effect(
                    self.db,
                    "session-123",
                    CombatResolveSpellEffectRequest(
                        actor_participant_id="p1",
                        pending_spell_id=first_result["pending_spell_id"],
                        roll_source="manual",
                        manual_rolls=[6, 6, 6, 6, 6, 6, 6, 6],
                    ),
                    "user-1",
                    False,
                )

        self.assertEqual(second_result["area_shape"], "sphere")
        self.assertEqual(second_result["damage"], 72)
        self.assertEqual(second_result["effect_rolls"], [6, 6, 6, 6, 6, 6, 6, 6])
        self.assertEqual(second_result["base_effect"], 48)
        self.assertEqual(second_result["affected_target_ref_ids"], ["player-123", "enemy-123"])
        self.assertEqual(second_result["target_count"], 2)
        self.assertEqual(
            [outcome["damage_applied"] for outcome in second_result["area_target_outcomes"]],
            [24, 48],
        )
        self.assertNotIn("pending_attack", self.state.participants[0])
        self.assertEqual(mock_apply_damage.call_count, 2)
        self.assertEqual(mock_apply_damage.call_args_list[0].args[3], 24)
        self.assertEqual(mock_apply_damage.call_args_list[1].args[3], 48)
        mock_emit_state.assert_awaited()
        mock_emit_log.assert_awaited()

    @patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat_service.spells.cast_area.resolve_saving_throw")
    async def test_cylinder_area_spell_cast_creates_pending_multi_target_effect(
        self,
        mock_resolve_saving_throw,
        mock_emit_log,
        mock_emit_state,
        mock_emit_entity_hp_update,
        mock_emit_player_state_update,
    ):
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        attacker_state = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "abilities": {"wisdom": 18},
                "spellcasting": {
                    "spells": [
                        {
                            "name": "Flame Strike",
                            "canonicalKey": "flame_strike",
                            "level": 5,
                            "prepared": True,
                        }
                    ],
                    "slots": {"5": {"used": 0, "max": 1}},
                },
            },
        )
        map_targeting_result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="enemy-123",
            affected_target_ref_ids=["enemy-123"],
            target_kind="session_entity",
            spatial_metadata=SpatialMetadata(
                source_token_id="tok_player",
                affected_token_ids=["tok_enemy"],
                affected_cells=[{"x": 10, "y": 10}, {"x": 11, "y": 10}],
                area_shape="cylinder",
                map_version=12,
                targeting_authority="limiar_map",
            ),
        )

        mock_resolve_saving_throw.return_value = MagicMock(total=7, success=False)

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=MagicMock(
                canonical_key="flame_strike",
                name_en="Flame Strike",
                name_pt=None,
                level=5,
                resolution_type="saving_throw",
                saving_throw="dexterity",
                save_success_outcome="half_damage",
                damage_type="fire",
                damage_dice="4d6",
                heal_dice=None,
                upcast_json=None,
                casting_time_type="action",
                target_type="ranged", area_shape="cylinder",
                range_meters=18,
                radius_meters=3,
            ),
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(attacker_state, 12, 10, 10, 3, 4),
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=RollActorStats(
                display_name="Target",
                abilities={"dexterity": 10},
                actor_kind="session_entity",
                actor_ref_id="enemy-123",
            ),
        ), patch(
            "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
            return_value=SimpleNamespace(validate=MagicMock(return_value=map_targeting_result)),
        ):
            result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="flame_strike",
                ),
                "user-1",
                False,
            )

        self.assertTrue(result["effect_roll_required"])
        self.assertEqual(result["area_shape"], "cylinder")
        self.assertEqual(result["affected_target_ref_ids"], ["enemy-123"])
        self.assertEqual(result["target_count"], 1)
        self.assertIsNotNone(result["pending_spell_id"])
        self.assertEqual(self.state.participants[0]["pending_attack"]["area_shape"], "cylinder")
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["5"]["used"], 1)
        mock_emit_state.assert_awaited()
        mock_emit_log.assert_awaited()
