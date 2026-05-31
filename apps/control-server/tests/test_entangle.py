from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.movement_hazards import _is_movement_hazard
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult
from app.services.seed_paths import resolve_base_seed_path
from app.services.spell_material_components import MaterialConsumptionResult
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides


class EntangleSeedContractTests(TestCombatServiceBase):
    @classmethod
    def setUpClass(cls):
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "entangle"),
            None,
        )

    def test_seed_entry_exists(self):
        self.assertIsNotNone(self.entry, "entangle not found in seed")

    def test_seed_uses_existing_targeting_field_names(self):
        entry = self.entry
        assert entry is not None
        self.assertEqual(entry.get("selectionType"), "point")
        self.assertEqual(entry.get("originType"), "selected_point")
        self.assertEqual(entry.get("targetAnchor"), "selected_point")
        self.assertEqual(entry.get("savingThrowAbility"), "strength")

    def test_seed_hazard_is_difficult_terrain_without_damage(self):
        entry = self.entry
        assert entry is not None
        persistent = entry.get("persistentArea")
        self.assertIsInstance(persistent, dict)
        self.assertEqual(persistent.get("kind"), "hazard")
        params = persistent.get("params") or {}
        self.assertEqual(params.get("terrainEffect"), "difficult_terrain")
        self.assertIsNone(params.get("movementDamageDice"))
        self.assertIsNone(params.get("damagePerMeters"))
        self.assertIsNone(params.get("damageType"))

    def test_entangle_hazard_is_not_movement_damage_hazard(self):
        effect = {
            "effect_kind": "hazard",
            "terrain_effect": "difficult_terrain",
        }
        self.assertFalse(_is_movement_hazard(effect))


class EntangleRegistryTests(TestCombatServiceBase):
    def test_targeting_semantics_override_exists(self):
        entangle = explicit_spell_targeting_overrides().get("entangle")
        self.assertIsNotNone(entangle)
        assert entangle is not None
        self.assertEqual(entangle.selection_type, "point")
        self.assertEqual(entangle.origin_type, "selected_point")
        self.assertEqual(entangle.target_anchor, "selected_point")
        self.assertEqual(entangle.effect_timing, "persistent")

    def test_spell_context_meta_exists(self):
        meta = CombatService.UTILITY_SPELL_CONTEXT_META.get("entangle")
        self.assertIsInstance(meta, dict)
        assert isinstance(meta, dict)
        self.assertEqual(meta.get("type"), "area_control")
        self.assertEqual(meta.get("conditionApplied"), "restrained")
        self.assertTrue(meta.get("createsDifficultTerrain"))
        self.assertTrue(meta.get("escapeAction"))

    def test_automation_registry_entry_exists(self):
        spec = CombatService._get_spell_automation_spec("entangle")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.handler_name, "_cast_entangle_automation")


class EntangleCastTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.attacker = self.state.participants[0]
        self.enemy = self.state.participants[1]

    def _spell_context(self):
        return {
            "spell_name": "Entangle",
            "spell_canonical_key": "entangle",
            "spell_mode": "utility",
            "effect_kind": None,
            "effect_timing": "persistent",
            "origin_type": "selected_point",
            "target_anchor": "selected_point",
            "selection_type": "point",
            "attack_type": "none",
            "range_kind": "distance",
            "area_shape": "square",
            "range_meters": 27,
            "side_meters": 6,
            "duration": "Concentration, up to 1 minute",
            "duration_seconds": 60,
            "concentration": True,
            "action_cost": "action",
            "source_kind": "prepared_spell",
            "slot_level": None,
            "damage_type": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": "strength",
            "save_dc": 14,
            "save_success_outcome": "none",
            "persistent_area": {
                "kind": "hazard",
                "params": {"terrainEffect": "difficult_terrain"},
            },
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "material_component_consumed": False,
            "consumable_material_options_json": None,
        }

    async def test_cast_applies_restrained_on_failed_initial_save(self):
        targeting_result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=[self.enemy["ref_id"]],
            target_kind="",
            spatial_metadata=SpatialMetadata(
                affected_cells=[{"x": 10, "y": 10}],
                affected_token_ids=[],
                area_shape="square",
                map_version=1,
                targeting_authority="limiar_map",
            ),
        )
        material_ok = MaterialConsumptionResult(
            required=False,
            consumed=False,
            material_key=None,
            material_label=None,
            quantity=0,
            inventory_item_id=None,
        )
        roll_result = SimpleNamespace(success=False, total=7, check_modifier_sources=[], is_gm_roll=False)

        with patch(
            "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
            return_value=SimpleNamespace(validate=MagicMock(return_value=targeting_result)),
        ), patch(
            "app.services.combat_service.spells.cast_area.validate_spell_material",
            return_value=material_ok,
        ), patch(
            "app.services.combat_service.spells.cast_area.consume_spell_material",
            return_value=material_ok,
        ), patch(
            "app.services.combat_service.spells.cast_area_entangle.resolve_saving_throw",
            return_value=roll_result,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_and_persist_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat_service.spells.cast_area_entangle.maybe_sync_active_area_effects_to_limiar_map",
        ):
            result = await CombatService._cast_area_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id=self.attacker["id"],
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="entangle",
                ),
                attacker=self.attacker,
                attacker_model=SimpleNamespace(),
                actor_user_id="user-1",
                is_gm=False,
                state=self.state,
                spell_context=self._spell_context(),
                area_spec={"shape": "square", "size_meters": 6, "range_meters": 27},
            )

        self.assertEqual(result["spell_canonical_key"], "entangle")
        self.assertEqual(result["area_shape"], "square")
        self.assertTrue(any(e.get("source_spell_canonical_key") == "entangle" for e in (self.state.active_area_effects or [])))
        enemy_effects = self.enemy.get("active_effects") or []
        entangle_restrained = [
            e for e in enemy_effects
            if e.get("kind") == "condition"
            and e.get("condition_type") == "restrained"
            and (e.get("metadata") or {}).get("source_spell_key") == "entangle"
        ]
        self.assertEqual(len(entangle_restrained), 1)


class EntangleEscapeActionTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.actor = self.state.participants[0]
        self.actor["turn_resources"] = {
            "action_used": False,
            "bonus_action_used": False,
            "reaction_used": False,
        }
        self.actor["active_effects"] = [
            {
                "id": "cond-1",
                "kind": "condition",
                "condition_type": "restrained",
                "metadata": {
                    "source_spell_key": "entangle",
                    "source_spell_name": "Entangle",
                    "source_effect_id": "area-1",
                    "escape_action": True,
                    "escape_check_ability": "strength",
                    "escape_check_dc": 14,
                },
            }
        ]

    async def test_invalid_source_does_not_consume_action(self):
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError):
                await CombatService.resolve_condition_escape_action(
                    self.db,
                    "session-123",
                    actor_participant_id=self.actor["id"],
                    actor_user_id="user-1",
                    is_gm=False,
                    condition_type="restrained",
                    source_effect_id="missing-area",
                )
        self.assertFalse(self.actor["turn_resources"]["action_used"])

    async def test_valid_escape_consumes_action_and_removes_condition_on_success(self):
        roll_result = SimpleNamespace(success=True, total=16, is_gm_roll=False, check_modifier_sources=[])
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat_service.effects_actions.resolve_ability_check",
            return_value=roll_result,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._apply_roll_dice_modifiers_for_actor",
            return_value=[],
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log",
            new_callable=AsyncMock,
        ):
            result = await CombatService.resolve_condition_escape_action(
                self.db,
                "session-123",
                actor_participant_id=self.actor["id"],
                actor_user_id="user-1",
                is_gm=False,
                condition_type="restrained",
                source_effect_id="area-1",
            )

        self.assertTrue(self.actor["turn_resources"]["action_used"])
        self.assertTrue(result["conditionRemoved"])
        self.assertEqual(self.actor.get("active_effects"), [])
