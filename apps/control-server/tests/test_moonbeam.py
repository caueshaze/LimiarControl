from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.services.combat import CombatService
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult


class MoonbeamTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.caster = self.state.participants[0]
        self.target = self.state.participants[1]
        self.caster_model = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "slots": {"2": {"used": 0, "max": 2}, "3": {"used": 0, "max": 1}},
                    "spells": [{"canonicalKey": "moonbeam", "level": 2, "prepared": True}],
                },
            },
        )

    def _targeting_result(self) -> TargetingResult:
        return TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=[self.target["ref_id"]],
            target_kind="",
            spatial_metadata=SpatialMetadata(
                affected_cells=[{"x": 10, "y": 10}, {"x": 10, "y": 9}],
                affected_token_ids=[],
                area_shape="cylinder",
                map_version=12,
                targeting_authority="limiar_map",
            ),
        )

    def _moonbeam_context(self) -> dict:
        return {
            "spell_name": "Moonbeam",
            "spell_canonical_key": "moonbeam",
            "spell_mode": "saving_throw",
            "effect_kind": "damage",
            "effect_timing": "persistent",
            "origin_type": "selected_point",
            "target_anchor": "selected_point",
            "selection_type": "point",
            "attack_type": "save",
            "range_kind": "distance",
            "area_shape": "cylinder",
            "range_meters": 36,
            "radius_meters": 1.5,
            "length_meters": None,
            "side_meters": None,
            "duration": "Concentration, up to 1 minute",
            "duration_seconds": 60,
            "concentration": True,
            "action_cost": "action",
            "source_kind": "prepared_spell",
            "slot_level": 2,
            "damage_type": "Radiant",
            "effect_dice": "2d10",
            "effect_bonus": 0,
            "save_ability": "constitution",
            "save_dc": 13,
            "save_success_outcome": "half_damage",
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "persistent_area": {
                "kind": "hazard",
                "params": {
                    "effectKind": "moonbeam",
                    "damageTriggers": ["enter_first_time_on_turn", "start_turn"],
                    "moveDistanceMeters": 18,
                },
            },
        }

    async def _cast_moonbeam(self):
        with patch(
            "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
            return_value=SimpleNamespace(validate=MagicMock(return_value=self._targeting_result())),
        ), patch(
            "app.services.combat_service.spells.cast_area.maybe_sync_active_area_effects_to_limiar_map",
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_player_state_update",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_and_persist_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(self.caster_model, 10, 10, 4, 2, 13),
        ):
            return await CombatService._cast_area_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id=self.caster["id"],
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="moonbeam",
                    slot_level=2,
                ),
                attacker=self.caster,
                attacker_model=self.caster_model,
                actor_user_id="user-1",
                is_gm=False,
                state=self.state,
                spell_context=self._moonbeam_context(),
                area_spec={"shape": "cylinder", "size_meters": 1, "range_meters": 36},
            )

    def test_seed_contract(self):
        seed_path = Path(__file__).resolve().parents[3] / "Base" / "base_spells.seed.json"
        with seed_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        spells = payload.get("spells") if isinstance(payload, dict) else payload
        moonbeam = next((s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "moonbeam"), None)
        self.assertIsNotNone(moonbeam)
        assert moonbeam is not None
        self.assertEqual(moonbeam.get("level"), 2)
        self.assertEqual(str(moonbeam.get("school", "")).lower(), "evocation")
        self.assertEqual(moonbeam.get("outOfCombatCastable"), False)

    def test_targeting_semantics_override(self):
        semantics = explicit_spell_targeting_overrides().get("moonbeam")
        self.assertIsNotNone(semantics)
        assert semantics is not None
        self.assertEqual(semantics.selection_type, "point")
        self.assertEqual(semantics.effect_timing, "persistent")

    async def test_cast_creates_persistent_moonbeam_without_immediate_damage(self):
        result = await self._cast_moonbeam()
        self.assertEqual(result["damage"], 0)
        self.assertEqual(len(self.state.active_area_effects), 1)
        effect = self.state.active_area_effects[0]
        self.assertEqual(effect.get("kind"), "hazard")
        self.assertEqual(effect.get("effect_kind"), "moonbeam")

    async def test_trigger_enter_applies_damage_once_per_turn_trigger(self):
        await self._cast_moonbeam()
        effect = self.state.active_area_effects[0]
        self.target["position"] = {"x": 10, "y": 10}

        with patch(
            "app.services.combat_service.spell_automation.modify_saving_throw",
            return_value=SimpleNamespace(
                result="normal",
                auto_fail=False,
                advantage_source_details=[],
                disadvantage_source_details=[],
            ),
        ), patch(
            "app.services.combat_service.spell_automation.resolve_saving_throw",
            return_value=SimpleNamespace(success=False, total=7, check_modifier_sources=[]),
        ), patch(
            "app.services.combat_service.spell_automation._roll_dice_expression",
            return_value=([5, 5], 10),
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(self.caster_model, 10, 10, 4, 2, 13),
        ), patch(
            "app.services.combat.CombatService.get_state",
            return_value=self.state,
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(12, "", 22, None),
        ):
            first = await CombatService.resolve_moonbeam_enter_trigger(
                self.db,
                "session-123",
                actor_user_id="user-1",
                is_gm=False,
                area_effect_id=effect["id"],
                target_ref_id=self.target["ref_id"],
                actor_participant_id=self.caster["id"],
            )
            second = await CombatService.resolve_moonbeam_enter_trigger(
                self.db,
                "session-123",
                actor_user_id="user-1",
                is_gm=False,
                area_effect_id=effect["id"],
                target_ref_id=self.target["ref_id"],
                actor_participant_id=self.caster["id"],
            )
        self.assertEqual(first["applied_damage"], 10)
        self.assertTrue(second.get("skipped"))

    async def test_move_moonbeam_consumes_action_and_updates_origin(self):
        await self._cast_moonbeam()
        effect = self.state.active_area_effects[0]
        self.caster["turn_resources"]["action_used"] = False
        with patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), patch(
            "app.services.combat.CombatService._emit_log", new_callable=AsyncMock
        ), patch(
            "app.services.combat.CombatService.get_state",
            return_value=self.state,
        ):
            result = await CombatService.resolve_moonbeam_move(
                self.db,
                "session-123",
                actor_user_id="user-1",
                is_gm=False,
                area_effect_id=effect["id"],
                new_point={"x": 12, "y": 12},
                actor_participant_id=self.caster["id"],
            )
        self.assertEqual(result["new_origin_point"], {"x": 12, "y": 12})
        self.assertTrue(result["action_consumed"])

    async def test_start_turn_trigger_uses_start_turn_dedup_bucket(self):
        await self._cast_moonbeam()
        self.target["position"] = {"x": 10, "y": 10}
        with patch(
            "app.services.combat_service.spell_automation.modify_saving_throw",
            return_value=SimpleNamespace(
                result="normal",
                auto_fail=False,
                advantage_source_details=[],
                disadvantage_source_details=[],
            ),
        ), patch(
            "app.services.combat_service.spell_automation.resolve_saving_throw",
            return_value=SimpleNamespace(success=True, total=14, check_modifier_sources=[]),
        ), patch(
            "app.services.combat_service.spell_automation._roll_dice_expression",
            return_value=([6, 4], 10),
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(self.caster_model, 10, 10, 4, 2, 13),
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(12, "", 22, None),
        ):
            outcomes = await CombatService.resolve_moonbeam_start_turn(
                self.db,
                "session-123",
                state=self.state,
                participant=self.target,
            )
            second = await CombatService.resolve_moonbeam_start_turn(
                self.db,
                "session-123",
                state=self.state,
                participant=self.target,
            )
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["applied_damage"], 5)
        self.assertEqual(second, [])

    async def test_shapechanger_save_has_disadvantage_and_applies_lock(self):
        await self._cast_moonbeam()
        effect = self.state.active_area_effects[0]
        self.target["position"] = {"x": 10, "y": 10}
        self.target["creature_type"] = "shapechanger"
        mock_save = MagicMock(return_value=SimpleNamespace(success=False, total=6, check_modifier_sources=[]))
        with patch(
            "app.services.combat_service.spell_automation.modify_saving_throw",
            return_value=SimpleNamespace(
                result="normal",
                auto_fail=False,
                advantage_source_details=[],
                disadvantage_source_details=[],
            ),
        ), patch(
            "app.services.combat_service.spell_automation.resolve_saving_throw",
            mock_save,
        ), patch(
            "app.services.combat_service.spell_automation._roll_dice_expression",
            return_value=([5, 5], 10),
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(self.caster_model, 10, 10, 4, 2, 13),
        ), patch(
            "app.services.combat.CombatService.get_state",
            return_value=self.state,
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(12, "", 22, None),
        ):
            outcome = await CombatService.resolve_moonbeam_enter_trigger(
                self.db,
                "session-123",
                actor_user_id="user-1",
                is_gm=False,
                area_effect_id=effect["id"],
                target_ref_id=self.target["ref_id"],
                actor_participant_id=self.caster["id"],
            )
        self.assertEqual(mock_save.call_args.kwargs.get("advantage_mode"), "disadvantage")
        self.assertTrue(outcome["shapechanger_effect"]["applied"])
