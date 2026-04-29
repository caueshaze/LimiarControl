from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.services.combat import CombatService
from app.services.combat_service.persistent_area_effects import active_area_effects_for_map
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
        persistent_area = None
        if canonical_key == "fog_cloud":
            persistent_area = {
                "kind": "obscurement",
                "params": {"obscurement": "heavily_obscured"},
            }
        elif canonical_key == "spike_growth":
            persistent_area = {
                "kind": "hazard",
                "params": {
                    "terrainEffect": "difficult_terrain",
                    "movementDamageDice": "2d4",
                    "damageType": "Piercing",
                    "damagePerMeters": 1.5,
                },
            }
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
            "persistent_area": persistent_area,
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

    async def test_no_semantic_effect_maps_to_plain_spell_area_overlay(self):
        await self._cast_persistent_area(
            "guardian_field",
            spell_name="Guardian Field",
            persistent_area={"kind": "no_semantic_effect", "params": {}},
        )

        effect = self.state.active_area_effects[0]
        self.assertEqual(effect["effect_kind"], "spell_area")
        self.assertIsNone(effect.get("obscurement"))
        self.assertIsNone(effect.get("terrain_effect"))

    async def test_persistent_area_round_trips_into_map_payload_shape(self):
        await self._cast_persistent_area("fog_cloud")

        map_effects = active_area_effects_for_map(self.state)
        self.assertEqual(len(map_effects), 1)
        self.assertEqual(map_effects[0]["effectKind"], "obscurement")
        self.assertEqual(map_effects[0]["obscurement"], "heavily_obscured")


class ConcentrationAreaEffectCleanupTests(TestCombatServiceBase):
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
        persistent_area = None
        if canonical_key == "fog_cloud":
            persistent_area = {
                "kind": "obscurement",
                "params": {"obscurement": "heavily_obscured"},
            }
        elif canonical_key == "spike_growth":
            persistent_area = {
                "kind": "hazard",
                "params": {
                    "terrainEffect": "difficult_terrain",
                    "movementDamageDice": "2d4",
                    "damageType": "Piercing",
                    "damagePerMeters": 1.5,
                },
            }
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
            "persistent_area": persistent_area,
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

    def _setup_concentrating_caster_with_area_effect(
        self,
        spell_key: str = "fog_cloud",
        spell_name: str = "Fog Cloud",
        concentration_group: str = "conc-test-1",
    ):
        self.attacker["active_effects"] = [
            {
                "id": "conc-effect-1",
                "kind": "spell_effect",
                "source_participant_id": "p1",
                "duration_type": "manual",
                "created_at": "2026-04-25T00:00:00Z",
                "display_label": spell_name,
                "metadata": {
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": spell_key,
                    "concentration_area_effect_id": "area-effect-1",
                },
            }
        ]
        self.state.active_area_effects = [
            {
                "id": "area-effect-1",
                "source_spell_canonical_key": spell_key,
                "source_spell_name": spell_name,
                "caster_participant_id": "p1",
                "caster_ref_id": "player-123",
                "caster_character_id": "user-1",
                "origin_point": {"x": 10, "y": 10},
                "anchor_cell": {"x": 10, "y": 10},
                "area_shape": "sphere",
                "size_meters": 6.0,
                "radius_meters": 6.0,
                "length_meters": None,
                "side_meters": None,
                "affected_cells": [{"x": 10, "y": 10}, {"x": 10, "y": 9}],
                "duration": "Up to 1 hour",
                "concentration_owner_participant_id": "p1",
                "concentration_owner_ref_id": "player-123",
                "concentration_group": concentration_group,
                "created_round": 1,
                "created_turn_index": 0,
                "effect_kind": "obscurement",
                "obscurement": "heavily_obscured",
            }
        ]

    async def test_fog_cloud_creates_concentration_effect_on_caster(self):
        await self._cast_persistent_area("fog_cloud")

        caster_effects = self.attacker.get("active_effects", [])
        self.assertEqual(len(caster_effects), 1)
        effect = caster_effects[0]
        self.assertEqual(effect["kind"], "spell_effect")
        self.assertEqual(effect["source_participant_id"], "p1")
        metadata = effect.get("metadata", {})
        self.assertTrue(metadata.get("concentration"))
        self.assertIsInstance(metadata.get("concentration_group"), str)
        self.assertEqual(metadata.get("source_spell_key"), "fog_cloud")
        self.assertEqual(
            metadata.get("concentration_area_effect_id"),
            self.state.active_area_effects[0]["id"],
        )

    async def test_spike_growth_creates_concentration_effect_on_caster(self):
        await self._cast_persistent_area(
            "spike_growth",
            spell_name="Spike Growth",
            duration="Up to 10 minutes",
            slot_level=2,
            range_meters=45,
        )

        caster_effects = self.attacker.get("active_effects", [])
        self.assertEqual(len(caster_effects), 1)
        effect = caster_effects[0]
        metadata = effect.get("metadata", {})
        self.assertTrue(metadata.get("concentration"))
        self.assertEqual(metadata.get("source_spell_key"), "spike_growth")

    async def test_concentration_area_effect_has_concentration_group(self):
        await self._cast_persistent_area("fog_cloud")

        area_effect = self.state.active_area_effects[0]
        self.assertIsInstance(area_effect.get("concentration_group"), str)

        caster_effect = self.attacker["active_effects"][0]
        self.assertEqual(
            area_effect["concentration_group"],
            caster_effect["metadata"]["concentration_group"],
        )

    @patch("app.services.combat_service.spell_automation.resolve_saving_throw")
    @patch("app.services.combat.CombatService._build_roll_actor_stats_for_save")
    def test_damage_breaks_concentration_removes_fog_cloud(
        self,
        mock_build_roll_stats,
        mock_resolve_saving_throw,
    ):
        self._setup_concentrating_caster_with_area_effect("fog_cloud", "Fog Cloud")
        mock_resolve_saving_throw.return_value = MagicMock(total=5, success=False)
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={"currentHP": 20, "maxHP": 20, "deathSaves": {"successes": 0, "failures": 0}},
        )

        with patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(session_state, 10, 10, 10, 2, 0),
        ), patch(
            "app.services.combat_service.limiar_map_projection.maybe_sync_active_area_effects_to_limiar_map",
        ) as mock_sync:
            CombatService._apply_damage_to_target(
                self.db, "player-123", "player", 8, False, self.state,
            )

        self.assertEqual(self.state.active_area_effects, [])
        self.assertEqual(self.attacker.get("active_effects", []), [])
        mock_sync.assert_called_once_with("session-123", self.state)

    @patch("app.services.combat_service.spell_automation.resolve_saving_throw")
    @patch("app.services.combat.CombatService._build_roll_actor_stats_for_save")
    def test_damage_breaks_concentration_removes_spike_growth(
        self,
        mock_build_roll_stats,
        mock_resolve_saving_throw,
    ):
        self._setup_concentrating_caster_with_area_effect(
            "spike_growth", "Spike Growth",
        )
        mock_resolve_saving_throw.return_value = MagicMock(total=5, success=False)
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={"currentHP": 20, "maxHP": 20, "deathSaves": {"successes": 0, "failures": 0}},
        )

        with patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(session_state, 10, 10, 10, 2, 0),
        ), patch(
            "app.services.combat_service.limiar_map_projection.maybe_sync_active_area_effects_to_limiar_map",
        ) as mock_sync:
            CombatService._apply_damage_to_target(
                self.db, "player-123", "player", 8, False, self.state,
            )

        self.assertEqual(self.state.active_area_effects, [])
        self.assertEqual(self.attacker.get("active_effects", []), [])
        mock_sync.assert_called_once()

    async def test_new_concentration_replaces_prior_area_effect(self):
        await self._cast_persistent_area("fog_cloud")
        self.assertEqual(len(self.state.active_area_effects), 1)
        fog_id = self.state.active_area_effects[0]["id"]
        fog_group = self.state.active_area_effects[0]["concentration_group"]

        self.attacker["turn_resources"] = dict(CombatService._DEFAULT_TURN_RESOURCES)

        await self._cast_persistent_area(
            "spike_growth",
            spell_name="Spike Growth",
            duration="Up to 10 minutes",
            slot_level=2,
            range_meters=45,
        )

        self.assertEqual(len(self.state.active_area_effects), 1)
        spike = self.state.active_area_effects[0]
        self.assertEqual(spike["source_spell_canonical_key"], "spike_growth")
        self.assertNotEqual(spike["id"], fog_id)
        self.assertNotEqual(spike["concentration_group"], fog_group)

        caster_effects = self.attacker.get("active_effects", [])
        self.assertEqual(len(caster_effects), 1)
        self.assertEqual(caster_effects[0]["metadata"]["source_spell_key"], "spike_growth")

    async def test_non_concentration_area_effect_survives_cleanup(self):
        self._setup_concentrating_caster_with_area_effect()
        non_conc_effect = {
            "id": "non-conc-effect",
            "source_spell_canonical_key": "some_spell",
            "source_spell_name": "Non-Conc Spell",
            "caster_participant_id": "p1",
            "caster_ref_id": "player-123",
            "origin_point": {"x": 5, "y": 5},
            "anchor_cell": {"x": 5, "y": 5},
            "area_shape": "sphere",
            "size_meters": 6.0,
            "radius_meters": 6.0,
            "affected_cells": [{"x": 5, "y": 5}],
            "concentration_owner_participant_id": None,
            "concentration_owner_ref_id": None,
            "concentration_group": None,
            "effect_kind": "spell_area",
        }
        self.state.active_area_effects = [*self.state.active_area_effects, non_conc_effect]
        self.assertEqual(len(self.state.active_area_effects), 2)

        result = CombatService._clear_concentration_for_source(
            self.state, source_participant_id="p1",
        )

        self.assertEqual(len(self.state.active_area_effects), 1)
        self.assertEqual(self.state.active_area_effects[0]["id"], "non-conc-effect")
        self.assertEqual(result["removed_area_effects"][0]["id"], "area-effect-1")

    def test_concentration_break_on_status_change_removes_area_effects(self):
        self._setup_concentrating_caster_with_area_effect()
        self.state.active_area_effects[0]["concentration_group"] = "conc-test-1"

        with patch(
            "app.services.combat_service.limiar_map_projection.maybe_sync_active_area_effects_to_limiar_map",
        ) as mock_sync:
            CombatService._clear_concentration_for_participant_status(
                self.state,
                source_participant_id="p1",
            )

        self.assertEqual(self.state.active_area_effects, [])
        self.assertEqual(self.attacker.get("active_effects", []), [])
        mock_sync.assert_called_once_with("session-123", self.state)

    @patch("app.services.combat_service.spell_automation.resolve_saving_throw")
    @patch("app.services.combat.CombatService._build_roll_actor_stats_for_save")
    def test_concentration_check_includes_area_effect_names(
        self,
        mock_build_roll_stats,
        mock_resolve_saving_throw,
    ):
        self._setup_concentrating_caster_with_area_effect("fog_cloud", "Fog Cloud")
        mock_resolve_saving_throw.return_value = MagicMock(total=5, success=False)
        session_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="player-123",
            state_json={"currentHP": 20, "maxHP": 20, "deathSaves": {"successes": 0, "failures": 0}},
        )

        with patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(session_state, 10, 10, 10, 2, 0),
        ), patch(
            "app.services.combat_service.limiar_map_projection.maybe_sync_active_area_effects_to_limiar_map",
        ):
            _, _, _, concentration_check = CombatService._apply_damage_to_target(
                self.db, "player-123", "player", 8, False, self.state,
            )

        self.assertIsNotNone(concentration_check)
        self.assertIn("fog_cloud", concentration_check["source_spell_keys"])
        self.assertTrue(
            any("Fog Cloud" in label for label in concentration_check["broken_effect_labels"]),
        )

    async def test_manual_effect_removal_cleans_up_area_effects(self):
        self._setup_concentrating_caster_with_area_effect()

        from app.schemas.combat import CombatRemoveEffectRequest

        with patch(
            "app.services.combat.CombatService.get_state",
            return_value=self.state,
        ), patch(
            "app.services.combat_service.limiar_map_projection.maybe_sync_active_area_effects_to_limiar_map",
        ) as mock_sync, patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ):
            await CombatService.remove_effect(
                self.db,
                "session-123",
                CombatRemoveEffectRequest(
                    target_participant_id="p1",
                    effect_id="conc-effect-1",
                ),
            )

        self.assertEqual(self.state.active_area_effects, [])
        self.assertEqual(self.attacker.get("active_effects", []), [])
        mock_sync.assert_called_once_with("session-123", self.state)

    async def test_hunters_mark_cast_after_fog_cloud_removes_area_effect(self):
        await self._cast_persistent_area("fog_cloud")
        self.assertEqual(len(self.state.active_area_effects), 1)
        self.assertEqual(
            self.state.active_area_effects[0]["source_spell_canonical_key"], "fog_cloud",
        )

        self.attacker["turn_resources"] = dict(CombatService._DEFAULT_TURN_RESOURCES)

        target = self.state.participants[1]
        with patch(
            "app.services.combat_service.limiar_map_projection.maybe_sync_active_area_effects_to_limiar_map",
        ) as mock_sync:
            await CombatService._cast_hunters_mark_automation(
                self.db,
                "session-123",
                attacker=self.attacker,
                attacker_model=self.attacker_model,
                actor_user_id="user-1",
                is_gm=False,
                req=MagicMock(),
                state=self.state,
                spell_context={"spell_name": "Hunter's Mark", "spell_canonical_key": "hunters_mark"},
                target_participant=target,
            )

        self.assertEqual(self.state.active_area_effects, [])

        caster_effects = self.attacker.get("active_effects", [])
        hm_keys = [
            e["metadata"]["source_spell_key"]
            for e in caster_effects
            if isinstance(e.get("metadata"), dict)
        ]
        self.assertIn("hunters_mark", hm_keys)
        self.assertNotIn("fog_cloud", hm_keys)
        mock_sync.assert_called_once()

    async def test_spike_growth_cast_after_hunters_mark_removes_mark_effects(self):
        target = self.state.participants[1]
        with patch(
            "app.services.combat_service.limiar_map_projection.maybe_sync_active_area_effects_to_limiar_map",
        ):
            await CombatService._cast_hunters_mark_automation(
                self.db,
                "session-123",
                attacker=self.attacker,
                attacker_model=self.attacker_model,
                actor_user_id="user-1",
                is_gm=False,
                req=MagicMock(),
                state=self.state,
                spell_context={"spell_name": "Hunter's Mark", "spell_canonical_key": "hunters_mark"},
                target_participant=target,
            )

        self.assertEqual(len(self.attacker.get("active_effects", [])), 1)
        self.assertEqual(len(target.get("active_effects", [])), 1)
        self.assertEqual(self.state.active_area_effects, [])

        self.attacker["turn_resources"] = dict(CombatService._DEFAULT_TURN_RESOURCES)

        await self._cast_persistent_area(
            "spike_growth",
            spell_name="Spike Growth",
            duration="Up to 10 minutes",
            slot_level=2,
            range_meters=45,
        )

        self.assertEqual(len(self.state.active_area_effects), 1)
        self.assertEqual(
            self.state.active_area_effects[0]["source_spell_canonical_key"], "spike_growth",
        )

        all_effect_keys = []
        for p in self.state.participants:
            for e in p.get("active_effects", []):
                m = e.get("metadata", {})
                if isinstance(m, dict) and m.get("source_spell_key"):
                    all_effect_keys.append(m["source_spell_key"])
        self.assertNotIn("hunters_mark", all_effect_keys)

    def test_removed_spike_growth_not_in_map_sync_payload(self):
        self._setup_concentrating_caster_with_area_effect(
            "spike_growth", "Spike Growth",
        )
        from app.services.combat_service.persistent_area_effects import (
            active_area_effects_for_map,
        )

        self.assertEqual(len(active_area_effects_for_map(self.state)), 1)

        CombatService._clear_concentration_for_source(
            self.state, source_participant_id="p1",
        )

        self.assertEqual(active_area_effects_for_map(self.state), [])
