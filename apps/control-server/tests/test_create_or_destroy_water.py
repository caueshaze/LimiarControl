from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell, WaterPayload
from app.services.combat import CombatService, CombatServiceError
from app.services.create_or_destroy_water import (
    resolve_cube_side_meters,
    resolve_water_amount,
    select_obscurement_effects_in_cells,
)
from app.services.out_of_combat_cast import (
    _is_ooc_utility_spell,
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
)
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult
from app.services.seed_paths import resolve_base_seed_path


class WaterSeedContractTests(TestCombatServiceBase):
    @classmethod
    def setUpClass(cls):
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "create_or_destroy_water"),
            None,
        )

    def test_seed_entry_exists(self):
        self.assertIsNotNone(self.entry, "create_or_destroy_water not found in seed")

    def test_seed_basic_fields(self):
        entry = self.entry
        assert entry is not None
        self.assertEqual(entry.get("level"), 1)
        self.assertEqual(entry.get("school"), "transmutation")
        self.assertEqual(set(entry.get("classesJson") or []), {"Cleric", "Druid"})
        self.assertEqual(entry.get("rangeMeters"), 9)
        self.assertEqual(entry.get("durationSeconds"), 0)
        self.assertFalse(entry.get("concentration"))
        self.assertTrue(entry.get("outOfCombatCastable"))
        self.assertEqual(entry.get("outOfCombatTarget"), "environment")
        self.assertEqual(entry.get("areaShape"), "cube")
        self.assertEqual(entry.get("sideMeters"), 9)
        self.assertIsNone(entry.get("savingThrowAbility"))


class WaterRegistryTests(TestCombatServiceBase):
    def test_targeting_semantics_override_exists(self):
        semantics = explicit_spell_targeting_overrides().get("create_or_destroy_water")
        self.assertIsNotNone(semantics)
        assert semantics is not None
        self.assertEqual(semantics.selection_type, "point")
        self.assertEqual(semantics.effect_timing, "persistent")

    def test_spell_context_meta_exists(self):
        meta = CombatService.UTILITY_SPELL_CONTEXT_META.get("create_or_destroy_water")
        self.assertIsInstance(meta, dict)
        assert isinstance(meta, dict)
        self.assertEqual(meta.get("type"), "environment_utility")
        self.assertTrue(meta.get("instantaneous"))
        self.assertTrue(meta.get("requiresEffectPayload"))
        self.assertEqual(meta.get("variants"), ["create_water", "destroy_water"])
        self.assertEqual(meta.get("baseLiters"), 38)
        self.assertTrue(meta.get("outOfCombatCastable"))


class WaterScalingTests(TestCombatServiceBase):
    def test_water_amount_scaling(self):
        self.assertEqual(resolve_water_amount(1), (10, 38))
        self.assertEqual(resolve_water_amount(2), (20, 76))
        self.assertEqual(resolve_water_amount(3), (30, 114))
        self.assertEqual(resolve_water_amount(None), (10, 38))

    def test_cube_side_scaling(self):
        self.assertEqual(resolve_cube_side_meters(1), 9.0)
        self.assertEqual(resolve_cube_side_meters(2), 10.5)
        self.assertEqual(resolve_cube_side_meters(3), 12.0)


class WaterCastBase(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.attacker = self.state.participants[0]
        self.attacker["active_effects"] = []

    def _spell_context(self, slot_level=1):
        return {
            "spell_name": "Create or Destroy Water",
            "spell_canonical_key": "create_or_destroy_water",
            "spell_mode": "utility",
            "effect_kind": None,
            "effect_timing": "persistent",
            "origin_type": "selected_point",
            "target_anchor": "selected_point",
            "selection_type": "point",
            "attack_type": "none",
            "range_kind": "distance",
            "area_shape": "cube",
            "range_meters": 9,
            "side_meters": 9,
            "duration": "Instantaneous",
            "duration_seconds": 0,
            "concentration": False,
            "action_cost": "action",
            "source_kind": "prepared_spell",
            "slot_level": slot_level,
            "save_ability": None,
            "save_dc": None,
            "material_component_consumed": False,
            "consumable_material_options_json": None,
        }

    def _targeting_result(self, cells):
        return TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=[],
            target_kind="",
            spatial_metadata=SpatialMetadata(
                affected_cells=list(cells),
                affected_token_ids=[],
                area_shape="cube",
                map_version=1,
                targeting_authority="limiar_map",
            ),
        )

    async def _cast(self, *, water_payload, slot_level=1, cells=None):
        cells = cells if cells is not None else [{"x": 10, "y": 10}]
        with patch(
            "app.services.combat_service.spells.cast_area.get_game_time_seconds",
            return_value=1000,
        ), patch(
            "app.services.combat.CombatService._emit_state", new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_and_persist_log", new_callable=AsyncMock,
        ), patch(
            "app.services.combat_service.spells.cast_area.maybe_sync_active_area_effects_to_limiar_map",
        ):
            return await CombatService._cast_create_or_destroy_water(
                self.db,
                "session-123",
                req=CombatCastSpellRequest(
                    actor_participant_id=self.attacker["id"],
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="create_or_destroy_water",
                    water_payload=water_payload,
                ),
                attacker=self.attacker,
                actor_user_id="user-1",
                is_gm=False,
                state=self.state,
                spell_context=self._spell_context(slot_level=slot_level),
                area_spec={"shape": "cube", "size_meters": 9, "range_meters": 9},
                targeting_result=self._targeting_result(cells),
                was_overridden=False,
            )


class WaterPayloadValidationTests(WaterCastBase):
    async def test_missing_payload_rejected(self):
        with self.assertRaises(CombatServiceError):
            await self._cast(water_payload=None)

    async def test_bad_mode_rejected(self):
        with self.assertRaises(CombatServiceError):
            await self._cast(water_payload=WaterPayload(mode="boil", target_kind="container", description="barril"))

    async def test_bad_target_kind_rejected(self):
        with self.assertRaises(CombatServiceError):
            await self._cast(water_payload=WaterPayload(mode="create", target_kind="ocean", description="x"))

    async def test_container_without_description_rejected(self):
        # No anchor relevance for container; missing description -> reject.
        payload = WaterPayload(mode="create", target_kind="container")
        with self.assertRaises(CombatServiceError):
            await self._cast(water_payload=payload)


class WaterCastTests(WaterCastBase):
    async def test_create_container_returns_amount(self):
        result = await self._cast(
            water_payload=WaterPayload(mode="create", target_kind="container", description="odre"),
            slot_level=2,
        )
        self.assertEqual(result["mode"], "create")
        self.assertEqual(result["target_kind"], "container")
        self.assertEqual(result["amount"], {"gallons": 20, "liters": 76})
        self.assertIsNone(result["area"])
        # No participant effects, no area effects.
        self.assertEqual(self.attacker.get("active_effects") or [], [])
        self.assertEqual(self.state.active_area_effects or [], [])

    async def test_create_area_returns_rain_and_extinguish_flags(self):
        result = await self._cast(
            water_payload=WaterPayload(mode="create", target_kind="area"),
        )
        self.assertEqual(result["target_kind"], "area")
        self.assertTrue(result["environment_effects"]["rain"])
        self.assertTrue(result["environment_effects"]["extinguishes_exposed_flames"])
        self.assertEqual(result["area"], {"shape": "cube", "side_meters": 9.0})

    async def test_destroy_container_returns_amount(self):
        result = await self._cast(
            water_payload=WaterPayload(mode="destroy", target_kind="container", description="barril"),
        )
        self.assertEqual(result["mode"], "destroy")
        self.assertEqual(result["amount"], {"gallons": 10, "liters": 38})

    async def test_destroy_area_returns_destroy_fog(self):
        result = await self._cast(
            water_payload=WaterPayload(mode="destroy", target_kind="area"),
        )
        self.assertTrue(result["environment_effects"]["destroy_fog"])

    async def test_does_not_clear_existing_concentration(self):
        self.attacker["active_effects"] = [
            {
                "id": "conc-1",
                "source_participant_id": self.attacker["id"],
                "kind": "spell_effect",
                "metadata": {"concentration": True, "concentration_group": "grp-x", "source_spell_key": "bless"},
            }
        ]
        await self._cast(
            water_payload=WaterPayload(mode="create", target_kind="container", description="odre"),
        )
        self.assertEqual(len(self.attacker["active_effects"]), 1)


class WaterDestroyFogTests(WaterCastBase):
    def _fog(self, fid, cells, *, concentration_group=None, caster_id=None):
        effect = {
            "id": fid,
            "effect_kind": "obscurement",
            "obscurement": "heavily_obscured",
            "affected_cells": list(cells),
            "source_spell_canonical_key": "fog_cloud",
        }
        if concentration_group:
            effect["concentration_group"] = concentration_group
        if caster_id:
            effect["caster_participant_id"] = caster_id
        return effect

    async def test_destroy_fog_removes_overlapping_obscurement(self):
        self.state.active_area_effects = [
            self._fog("fog-in", [{"x": 10, "y": 10}]),
            self._fog("fog-out", [{"x": 99, "y": 99}]),
            {"id": "hazard-in", "effect_kind": "hazard", "affected_cells": [{"x": 10, "y": 10}]},
        ]
        result = await self._cast(
            water_payload=WaterPayload(mode="destroy", target_kind="area"),
            cells=[{"x": 10, "y": 10}, {"x": 11, "y": 10}],
        )
        self.assertEqual(result["removed_fog_effect_ids"], ["fog-in"])
        remaining_ids = {e["id"] for e in self.state.active_area_effects}
        self.assertEqual(remaining_ids, {"fog-out", "hazard-in"})

    async def test_destroy_fog_removes_concentration_group_and_anchor(self):
        caster = self.state.participants[1]
        caster["active_effects"] = [
            {
                "id": "anchor-fog",
                "source_participant_id": caster["id"],
                "kind": "spell_effect",
                "metadata": {"concentration": True, "concentration_group": "fog-grp", "source_spell_key": "fog_cloud"},
            }
        ]
        self.state.active_area_effects = [
            self._fog("fog-c", [{"x": 10, "y": 10}], concentration_group="fog-grp", caster_id=caster["id"]),
        ]
        result = await self._cast(
            water_payload=WaterPayload(mode="destroy", target_kind="area"),
            cells=[{"x": 10, "y": 10}],
        )
        self.assertEqual(result["removed_fog_effect_ids"], ["fog-c"])
        self.assertEqual(self.state.active_area_effects or [], [])
        # Caster's concentration anchor for that fog is also gone.
        self.assertEqual(caster["active_effects"], [])

    def test_select_helper_ignores_non_obscurement_and_outside(self):
        state = SimpleNamespace(active_area_effects=[
            {"id": "a", "effect_kind": "obscurement", "affected_cells": [{"x": 1, "y": 1}]},
            {"id": "b", "effect_kind": "obscurement", "affected_cells": [{"x": 5, "y": 5}]},
            {"id": "c", "effect_kind": "hazard", "affected_cells": [{"x": 1, "y": 1}]},
        ])
        matches = select_obscurement_effects_in_cells(state, [{"x": 1, "y": 1}])
        self.assertEqual([m["id"] for m in matches], ["a"])


def _ooc_spell(level=1):
    return SimpleNamespace(
        canonical_key="create_or_destroy_water",
        name_pt="Criar ou Destruir Água",
        name_en="Create or Destroy Water",
        level=level,
        concentration=False,
        out_of_combat_castable=True,
        effects_json=None,
        variants_json=None,
    )


def _slots_state(level=1):
    return {"spellcasting": {"slots": {str(level): {"used": 0, "max": 2}}}}


class WaterOocTests(TestCombatServiceBase):
    def test_is_ooc_utility_spell(self):
        self.assertTrue(_is_ooc_utility_spell("create_or_destroy_water"))

    def test_eligibility_accepts_with_slot(self):
        ok, reason = check_out_of_combat_cast_eligibility(
            spell=_ooc_spell(),
            state_json=_slots_state(1),
            slot_level=1,
            variant_key="create_water",
            out_of_combat_target="environment",
            caster_user_id="u1",
            target_user_id="u1",
        )
        self.assertTrue(ok, reason)

    def test_persisted_effect_is_nonmechanical_with_scaled_amount(self):
        effects = build_persisted_effects(
            spell=_ooc_spell(),
            caster_user_id="u1",
            target_user_id="u1",
            variant_key="create_water",
            game_time_seconds=100,
            slot_level=2,
        )
        self.assertEqual(len(effects), 1)
        meta = effects[0]["metadata"]
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["instantaneous"])
        self.assertEqual(meta["mode"], "create")
        self.assertEqual(meta["target_kind"], "container")
        self.assertEqual(meta["gallons"], 20)
        self.assertEqual(meta["liters"], 76)
        # Instantaneous: expires at creation time (no lasting effect).
        self.assertEqual(
            effects[0]["expires_at_game_time_seconds"],
            effects[0]["created_at_game_time_seconds"],
        )

    def test_destroy_variant_maps_to_mode(self):
        effects = build_persisted_effects(
            spell=_ooc_spell(),
            caster_user_id="u1",
            target_user_id="u1",
            variant_key="destroy_water",
            game_time_seconds=100,
            slot_level=1,
        )
        self.assertEqual(effects[0]["metadata"]["mode"], "destroy")
