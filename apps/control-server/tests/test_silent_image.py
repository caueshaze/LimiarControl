from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.services.combat import CombatService, CombatServiceError
from app.services.silent_image import (
    find_silent_image_effect,
    mark_illusion_discerned,
    update_illusion,
)
from app.services.spell_material_components import MaterialConsumptionResult
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult
from app.services.seed_paths import resolve_base_seed_path


class SilentImageSeedContractTests(TestCombatServiceBase):
    @classmethod
    def setUpClass(cls):
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "silent_image"),
            None,
        )

    def test_seed_entry_exists(self):
        self.assertIsNotNone(self.entry, "silent_image not found in seed")

    def test_seed_basic_fields(self):
        entry = self.entry
        assert entry is not None
        self.assertEqual(entry.get("level"), 1)
        self.assertEqual(entry.get("school"), "illusion")
        self.assertEqual(set(entry.get("classesJson") or []), {"Bard", "Sorcerer", "Wizard"})
        self.assertEqual(entry.get("rangeMeters"), 18)
        self.assertEqual(entry.get("durationSeconds"), 600)
        self.assertTrue(entry.get("concentration"))
        self.assertEqual(entry.get("areaShape"), "cube")
        self.assertEqual(entry.get("sideMeters"), 4.5)
        self.assertFalse(entry.get("outOfCombatCastable"))
        self.assertIsNone(entry.get("savingThrowAbility"))

    def test_seed_persistent_area_is_illusion(self):
        entry = self.entry
        assert entry is not None
        persistent = entry.get("persistentArea")
        self.assertIsInstance(persistent, dict)
        self.assertEqual(persistent.get("kind"), "illusion")
        self.assertEqual((persistent.get("params") or {}).get("illusionKind"), "visual_image")


class SilentImageRegistryTests(TestCombatServiceBase):
    def test_targeting_semantics_override_exists(self):
        semantics = explicit_spell_targeting_overrides().get("silent_image")
        self.assertIsNotNone(semantics)
        assert semantics is not None
        self.assertEqual(semantics.selection_type, "point")
        self.assertEqual(semantics.origin_type, "selected_point")
        self.assertEqual(semantics.effect_timing, "persistent")

    def test_spell_context_meta_exists(self):
        meta = CombatService.UTILITY_SPELL_CONTEXT_META.get("silent_image")
        self.assertIsInstance(meta, dict)
        assert isinstance(meta, dict)
        self.assertEqual(meta.get("type"), "illusion")
        self.assertTrue(meta.get("purelyVisual"))
        self.assertTrue(meta.get("physicalInteractionReveals"))
        self.assertEqual(meta.get("investigationAbility"), "intelligence")
        self.assertEqual(meta.get("investigationSkill"), "investigation")
        self.assertTrue(meta.get("createsIllusion"))
        self.assertFalse(meta.get("outOfCombatCastable"))


class SilentImageCastTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.attacker = self.state.participants[0]
        self.enemy = self.state.participants[1]

    def _spell_context(self):
        return {
            "spell_name": "Silent Image",
            "spell_canonical_key": "silent_image",
            "spell_mode": "utility",
            "effect_kind": None,
            "effect_timing": "persistent",
            "origin_type": "selected_point",
            "target_anchor": "selected_point",
            "selection_type": "point",
            "attack_type": "none",
            "range_kind": "distance",
            "area_shape": "cube",
            "range_meters": 18,
            "side_meters": 4.5,
            "duration": "Concentration, up to 10 minutes",
            "duration_seconds": 600,
            "concentration": True,
            "action_cost": "action",
            "source_kind": "prepared_spell",
            "slot_level": None,
            "damage_type": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "persistent_area": {"kind": "illusion", "params": {"illusionKind": "visual_image"}},
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "material_component_consumed": False,
            "consumable_material_options_json": None,
        }

    def _targeting_result(self):
        return TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=[],
            target_kind="",
            spatial_metadata=SpatialMetadata(
                affected_cells=[{"x": 10, "y": 7}],
                affected_token_ids=[],
                area_shape="cube",
                map_version=1,
                targeting_authority="limiar_map",
            ),
        )

    async def _cast(self, appearance):
        material_ok = MaterialConsumptionResult(
            required=False, consumed=False, material_key=None,
            material_label=None, quantity=0, inventory_item_id=None,
        )
        req = CombatCastSpellRequest(
            actor_participant_id=self.attacker["id"],
            origin_cell=CombatGridCell(x=8, y=8),
            anchor_cell=CombatGridCell(x=10, y=7),
            spell_canonical_key="silent_image",
            illusion_appearance=appearance,
        )
        with patch(
            "app.services.combat_service.spells.cast_area.get_combat_targeting_service",
            return_value=SimpleNamespace(validate=MagicMock(return_value=self._targeting_result())),
        ), patch(
            "app.services.combat_service.spells.cast_area.validate_spell_material",
            return_value=material_ok,
        ), patch(
            "app.services.combat_service.spells.cast_area.consume_spell_material",
            return_value=material_ok,
        ), patch(
            "app.services.combat_service.spells.cast_area.get_game_time_seconds",
            return_value=1000,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            return_value=(SimpleNamespace(), 10, 10, [], 2, 3),
        ), patch(
            "app.services.combat.CombatService._emit_state",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_and_persist_log",
            new_callable=AsyncMock,
        ), patch(
            "app.services.combat_service.spells.cast_area.maybe_sync_active_area_effects_to_limiar_map",
        ):
            return await CombatService._cast_area_spell(
                self.db,
                "session-123",
                req,
                attacker=self.attacker,
                attacker_model=SimpleNamespace(),
                actor_user_id="user-1",
                is_gm=False,
                state=self.state,
                spell_context=self._spell_context(),
                area_spec={"shape": "cube", "size_meters": 4.5, "range_meters": 18},
            )

    async def test_cast_creates_illusion_entity(self):
        result = await self._cast({"description": "Uma parede de pedra", "category": "object"})
        self.assertEqual(result["spell_canonical_key"], "silent_image")
        illusions = [e for e in (self.state.active_area_effects or []) if e.get("effect_kind") == "illusion"]
        self.assertEqual(len(illusions), 1)
        illusion = illusions[0]
        self.assertEqual(illusion["appearance"]["description"], "Uma parede de pedra")
        self.assertEqual(illusion["appearance"]["category"], "object")
        self.assertEqual(illusion["discerned_by_ref_ids"], [])
        self.assertEqual(illusion["investigation_dc"], 13)  # 8 + 2 + 3
        self.assertTrue(illusion.get("concentration_group"))
        self.assertEqual(illusion.get("caster_participant_id"), self.attacker["id"])

    async def test_cast_anchors_concentration_on_caster_without_creature_condition(self):
        await self._cast({"description": "Um lobo espectral", "category": "creature"})
        anchors = [
            e for e in (self.attacker.get("active_effects") or [])
            if (e.get("metadata") or {}).get("source_spell_key") == "silent_image"
        ]
        self.assertEqual(len(anchors), 1)
        self.assertTrue((anchors[0]["metadata"]).get("concentration"))
        # Enemy gains no condition from the illusion.
        self.assertEqual(self.enemy.get("active_effects") or [], [])

    async def test_cast_clears_prior_concentration(self):
        self.state.active_area_effects = [
            {
                "id": "area_effect:old",
                "effect_kind": "illusion",
                "concentration_group": "old-grp",
                "source_spell_canonical_key": "silent_image",
            }
        ]
        self.attacker["active_effects"] = [
            {
                "id": "anchor-old",
                "source_participant_id": self.attacker["id"],
                "kind": "spell_effect",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "old-grp",
                    "source_spell_key": "silent_image",
                },
            }
        ]
        await self._cast({"description": "Nova imagem", "category": "phenomenon"})
        illusions = [e for e in (self.state.active_area_effects or []) if e.get("effect_kind") == "illusion"]
        self.assertEqual(len(illusions), 1)
        self.assertNotEqual(illusions[0]["id"], "area_effect:old")

    async def test_cast_rejects_empty_description(self):
        with self.assertRaises(CombatServiceError):
            await self._cast({"description": "   ", "category": "object"})

    async def test_cast_rejects_invalid_category(self):
        with self.assertRaises(CombatServiceError):
            await self._cast({"description": "algo", "category": "monstro"})


def _make_illusion(*, illusion_id="area_effect:img1", group="grp-1", caster_id="p1", dc=13):
    return {
        "id": illusion_id,
        "effect_kind": "illusion",
        "source_spell_canonical_key": "silent_image",
        "source_spell_name": "Silent Image",
        "caster_participant_id": caster_id,
        "caster_ref_id": "player-123",
        "concentration_group": group,
        "origin_point": {"x": 10, "y": 7},
        "anchor_cell": {"x": 10, "y": 7},
        "appearance": {"description": "Uma parede", "category": "object"},
        "investigation_dc": dc,
        "discerned_by_ref_ids": [],
    }


class SilentImageInvestigationTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 1  # Goblin's turn
        self.actor = self.state.participants[1]  # Goblin investigates
        self.state.active_area_effects = [_make_illusion()]

    async def _investigate(self, *, success):
        roll_result = SimpleNamespace(success=success, total=18 if success else 5, is_gm_roll=False)
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat_service.spells.illusions.resolve_skill_check",
            return_value=roll_result,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=SimpleNamespace(),
        ), patch(
            "app.services.combat.CombatService._emit_state", new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log", new_callable=AsyncMock,
        ), patch(
            "app.services.combat_service.spells.illusions.maybe_sync_active_area_effects_to_limiar_map",
        ):
            return await CombatService.resolve_illusion_investigation(
                self.db,
                "session-123",
                actor_participant_id=self.actor["id"],
                illusion_id="area_effect:img1",
                actor_user_id="user-1",
                is_gm=True,
            )

    async def test_failed_check_does_not_discern(self):
        result = await self._investigate(success=False)
        self.assertFalse(result["discerned"])
        illusion = find_silent_image_effect(self.state, "area_effect:img1")
        self.assertEqual(illusion["discerned_by_ref_ids"], [])
        self.assertTrue(self.actor["turn_resources"]["action_used"])

    async def test_success_marks_discerned_for_that_creature(self):
        result = await self._investigate(success=True)
        self.assertTrue(result["discerned"])
        illusion = find_silent_image_effect(self.state, "area_effect:img1")
        self.assertEqual(illusion["discerned_by_ref_ids"], [self.actor["ref_id"]])

    async def test_uses_skill_check_not_saving_throw(self):
        # If resolve_skill_check is invoked, the patched value drives the outcome.
        with patch(
            "app.services.combat_service.spells.illusions.resolve_skill_check",
        ) as skill_mock:
            skill_mock.return_value = SimpleNamespace(success=True, total=20, is_gm_roll=False)
            with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
                "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                return_value=SimpleNamespace(),
            ), patch(
                "app.services.combat.CombatService._emit_state", new_callable=AsyncMock,
            ), patch(
                "app.services.combat.CombatService._emit_log", new_callable=AsyncMock,
            ), patch(
                "app.services.combat_service.spells.illusions.maybe_sync_active_area_effects_to_limiar_map",
            ):
                await CombatService.resolve_illusion_investigation(
                    self.db,
                    "session-123",
                    actor_participant_id=self.actor["id"],
                    illusion_id="area_effect:img1",
                    actor_user_id="user-1",
                    is_gm=True,
                )
        skill_mock.assert_called_once()
        self.assertEqual(skill_mock.call_args.args[1], "investigation")

    async def test_invalid_illusion_does_not_consume_action(self):
        with patch("app.services.combat.CombatService.get_state", return_value=self.state):
            with self.assertRaises(CombatServiceError):
                await CombatService.resolve_illusion_investigation(
                    self.db,
                    "session-123",
                    actor_participant_id=self.actor["id"],
                    illusion_id="missing-illusion",
                    actor_user_id="user-1",
                    is_gm=True,
                )
        self.assertNotEqual(self.actor.get("turn_resources", {}).get("action_used"), True)


class SilentImageRevealTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.active_area_effects = [_make_illusion()]

    async def _reveal(self, *, is_gm, actor_ref_id="enemy-123"):
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._emit_state", new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log", new_callable=AsyncMock,
        ), patch(
            "app.services.combat_service.spells.illusions.maybe_sync_active_area_effects_to_limiar_map",
        ):
            return await CombatService.resolve_illusion_reveal_by_interaction(
                self.db,
                "session-123",
                actor_ref_id=actor_ref_id,
                illusion_id="area_effect:img1",
                is_gm=is_gm,
            )

    async def test_gm_reveal_marks_discerned_without_removing(self):
        result = await self._reveal(is_gm=True)
        self.assertTrue(result["discerned"])
        illusion = find_silent_image_effect(self.state, "area_effect:img1")
        self.assertIsNotNone(illusion)
        self.assertEqual(illusion["discerned_by_ref_ids"], ["enemy-123"])

    async def test_non_gm_reveal_rejected(self):
        with self.assertRaises(CombatServiceError):
            await self._reveal(is_gm=False)

    async def test_reveal_is_per_creature(self):
        await self._reveal(is_gm=True)
        illusion = find_silent_image_effect(self.state, "area_effect:img1")
        self.assertNotIn("player-123", illusion["discerned_by_ref_ids"])


class SilentImageUpdateTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.caster = self.state.participants[0]
        illusion = _make_illusion(caster_id=self.caster["id"])
        illusion["discerned_by_ref_ids"] = ["enemy-123"]
        self.state.active_area_effects = [illusion]

    async def _update(self, *, is_gm, actor_id, point=None, appearance=None):
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._emit_state", new_callable=AsyncMock,
        ), patch(
            "app.services.combat.CombatService._emit_log", new_callable=AsyncMock,
        ), patch(
            "app.services.combat_service.spells.illusions.maybe_sync_active_area_effects_to_limiar_map",
        ):
            return await CombatService.resolve_illusion_update(
                self.db,
                "session-123",
                actor_participant_id=actor_id,
                illusion_id="area_effect:img1",
                actor_user_id="user-1",
                is_gm=is_gm,
                point=point,
                appearance=appearance,
            )

    async def test_caster_update_consumes_action_and_moves(self):
        await self._update(
            is_gm=False,
            actor_id=self.caster["id"],
            point={"x": 12, "y": 9},
            appearance={"description": "A parede desliza", "category": "object"},
        )
        illusion = find_silent_image_effect(self.state, "area_effect:img1")
        self.assertEqual(illusion["origin_point"], {"x": 12, "y": 9})
        self.assertEqual(illusion["appearance"]["description"], "A parede desliza")
        self.assertTrue(self.caster["turn_resources"]["action_used"])
        # Discernment preserved + concentration group preserved.
        self.assertEqual(illusion["discerned_by_ref_ids"], ["enemy-123"])
        self.assertEqual(illusion["concentration_group"], "grp-1")

    async def test_gm_update_bypasses_turn_ownership(self):
        # Make it the enemy's turn; GM can still update.
        self.state.current_turn_index = 1
        await self._update(is_gm=True, actor_id=None, point={"x": 1, "y": 1})
        illusion = find_silent_image_effect(self.state, "area_effect:img1")
        self.assertEqual(illusion["origin_point"], {"x": 1, "y": 1})

    async def test_non_caster_cannot_update(self):
        self.state.current_turn_index = 1
        with self.assertRaises(CombatServiceError):
            await self._update(is_gm=False, actor_id=self.state.participants[1]["id"], point={"x": 1, "y": 1})


class SilentImageCleanupTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.caster = self.state.participants[0]
        self.caster["active_effects"] = [
            {
                "id": "anchor-1",
                "source_participant_id": self.caster["id"],
                "kind": "spell_effect",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "grp-1",
                    "source_spell_key": "silent_image",
                },
            }
        ]

    def test_losing_concentration_removes_illusion(self):
        self.state.active_area_effects = [_make_illusion(group="grp-1", caster_id=self.caster["id"])]
        result = CombatService._clear_concentration_for_source(
            self.state, source_participant_id=self.caster["id"],
        )
        self.assertTrue(any(
            e.get("source_spell_canonical_key") == "silent_image"
            for e in result["removed_area_effects"]
        ))
        remaining = [e for e in (self.state.active_area_effects or []) if e.get("effect_kind") == "illusion"]
        self.assertEqual(remaining, [])

    def test_cleanup_of_one_illusion_keeps_another(self):
        other = _make_illusion(illusion_id="area_effect:img2", group="grp-2", caster_id="e1")
        self.state.active_area_effects = [
            _make_illusion(group="grp-1", caster_id=self.caster["id"]),
            other,
        ]
        CombatService._clear_concentration_for_source(
            self.state, source_participant_id=self.caster["id"],
        )
        remaining_ids = {e["id"] for e in (self.state.active_area_effects or [])}
        self.assertIn("area_effect:img2", remaining_ids)
        self.assertNotIn("area_effect:img1", remaining_ids)


class SilentImageHelperTests(TestCombatServiceBase):
    def test_mark_idempotent(self):
        self.state.active_area_effects = [_make_illusion()]
        self.assertTrue(mark_illusion_discerned(self.state, "area_effect:img1", "enemy-123"))
        self.assertTrue(mark_illusion_discerned(self.state, "area_effect:img1", "enemy-123"))
        illusion = find_silent_image_effect(self.state, "area_effect:img1")
        self.assertEqual(illusion["discerned_by_ref_ids"], ["enemy-123"])

    def test_update_missing_returns_none(self):
        self.state.active_area_effects = []
        self.assertIsNone(update_illusion(self.state, "missing", point={"x": 1, "y": 1}))
