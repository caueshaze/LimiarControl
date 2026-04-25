from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.services.combat import CombatService
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult


class PersistentAreaEffectCastTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.attacker = self.state.participants[0]
        self.attacker_model = SessionState(
            id="state-player",
            session_id="session-123",
            player_user_id="player-123",
            state_json={
                "spellcasting": {
                    "slots": {"1": {"used": 0, "max": 2}, "2": {"used": 0, "max": 2}},
                },
            },
        )

    def _targeting_result(self, *, shape: str = "sphere") -> TargetingResult:
        return TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=[],
            target_kind="",
            spatial_metadata=SpatialMetadata(
                affected_cells=[{"x": 10, "y": 10}, {"x": 10, "y": 9}],
                affected_token_ids=[],
                area_shape=shape,
                map_version=12,
                targeting_authority="limiar_map",
            ),
        )

    def _spell_context(self, canonical_key: str, **overrides):
        base = {
            "spell_name": "Fog Cloud" if canonical_key == "fog_cloud" else "Spike Growth",
            "spell_canonical_key": canonical_key,
            "spell_mode": "utility",
            "effect_kind": None,
            "effect_timing": "persistent",
            "origin_type": "selected_point",
            "target_anchor": "selected_point",
            "selection_type": "point",
            "attack_type": "none",
            "range_kind": "distance",
            "area_shape": "sphere",
            "range_meters": 36,
            "radius_meters": 6,
            "length_meters": None,
            "side_meters": None,
            "duration": "Up to 1 hour",
            "concentration": True,
            "action_cost": "action",
            "source_kind": "prepared_spell",
            "slot_level": 1,
            "damage_type": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
        }
        base.update(overrides)
        return base

    async def _cast_persistent_area(self, canonical_key: str, **context_overrides):
        targeting_result = self._targeting_result()
        with patch(
            "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
            return_value=SimpleNamespace(validate=MagicMock(return_value=targeting_result)),
        ), patch(
            "app.services.combat_service.spells.cast_area.maybe_sync_active_area_effects_to_limiar_map",
        ) as mock_sync, patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_player_state_update",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(self.attacker_model, 10, 10, 10, 2, 3),
        ):
            result = await CombatService._cast_area_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key=canonical_key,
                    slot_level=1,
                ),
                attacker=self.attacker,
                attacker_model=self.attacker_model,
                actor_user_id="user-1",
                is_gm=False,
                state=self.state,
                spell_context=self._spell_context(canonical_key, **context_overrides),
                area_spec={"shape": "sphere", "size_meters": 6, "range_meters": 36},
            )
        return result, mock_sync

    async def test_fog_cloud_creates_obscurement_area_effect(self):
        result, mock_sync = await self._cast_persistent_area("fog_cloud")

        self.assertEqual(len(self.state.active_area_effects), 1)
        effect = self.state.active_area_effects[0]
        self.assertEqual(effect["source_spell_canonical_key"], "fog_cloud")
        self.assertEqual(effect["effect_kind"], "obscurement")
        self.assertEqual(effect["obscurement"], "heavily_obscured")
        self.assertEqual(effect["area_shape"], "sphere")
        self.assertEqual(effect["radius_meters"], 6.0)
        self.assertEqual(effect["origin_point"], {"x": 10, "y": 10})
        self.assertEqual(effect["anchor_cell"], {"x": 10, "y": 10})
        self.assertEqual(effect["concentration_owner_participant_id"], "p1")
        self.assertEqual(result["active_area_effect"]["id"], effect["id"])
        mock_sync.assert_called_once_with("session-123", self.state)

    async def test_spike_growth_creates_hazard_area_effect(self):
        await self._cast_persistent_area(
            "spike_growth",
            spell_name="Spike Growth",
            duration="Up to 10 minutes",
            slot_level=2,
            range_meters=45,
        )

        effect = self.state.active_area_effects[0]
        self.assertEqual(effect["source_spell_canonical_key"], "spike_growth")
        self.assertEqual(effect["effect_kind"], "hazard")
        self.assertEqual(effect["terrain_effect"], "difficult_terrain")
        self.assertEqual(effect["movement_damage_dice"], "2d4")
        self.assertEqual(effect["damage_type"], "Piercing")
        self.assertEqual(effect["damage_per_meters"], 1.5)

    async def test_triggered_area_spell_does_not_create_persistent_overlay(self):
        result, mock_sync = await self._cast_persistent_area(
            "hail_of_thorns",
            spell_name="Hail of Thorns",
            effect_timing="triggered",
            origin_type="caster",
            target_anchor="trigger_target",
            selection_type="none",
            range_kind="self",
        )

        self.assertEqual(self.state.active_area_effects, [])
        self.assertIsNone(result["active_area_effect"])
        mock_sync.assert_not_called()
