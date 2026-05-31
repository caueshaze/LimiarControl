from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.services.combat import CombatService
from app.services.combat_service.condition_effects import resolve_attack_advantage
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult
from app.services.seed_paths import resolve_base_seed_path
from app.services.spell_material_components import MaterialConsumptionResult
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides


def _participant(conditions: list[str] | None = None, extra_effects: list[dict] | None = None) -> dict:
    effects: list[dict] = []
    for ctype in conditions or []:
        effects.append({"kind": "condition", "condition_type": ctype})
    effects.extend(extra_effects or [])
    return {"id": "p1", "active_effects": effects, "status": "active"}


def _faerie_fire_effect(group: str, source_id: str = "caster-1") -> dict:
    return {
        "id": f"ff-{group}-{source_id}",
        "kind": "spell_effect",
        "source_participant_id": source_id,
        "metadata": {
            "source_spell_key": "faerie_fire",
            "concentration": True,
            "concentration_group": group,
            "faerie_fire": True,
            "attack_advantage_against_this_target": True,
            "suppresses_invisibility_benefit": True,
        },
    }


class FaerieFireSeedContractTests(TestCombatServiceBase):
    @classmethod
    def setUpClass(cls):
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "faerie_fire"),
            None,
        )

    def test_seed_entry_exists(self):
        self.assertIsNotNone(self.entry, "faerie_fire not found in seed")

    def test_seed_contract(self):
        entry = self.entry
        assert entry is not None
        self.assertEqual(entry.get("level"), 1)
        self.assertEqual(entry.get("savingThrowAbility"), "dexterity")
        self.assertEqual(entry.get("areaShape"), "cube")
        self.assertEqual(entry.get("sideMeters"), 6)
        self.assertTrue(entry.get("concentration"))
        self.assertFalse(entry.get("outOfCombatCastable"))


class FaerieFireRegistryTests(TestCombatServiceBase):
    def test_targeting_semantics_override_exists(self):
        ff = explicit_spell_targeting_overrides().get("faerie_fire")
        self.assertIsNotNone(ff)
        assert ff is not None
        self.assertEqual(ff.selection_type, "point")
        self.assertEqual(ff.origin_type, "selected_point")
        self.assertEqual(ff.target_anchor, "selected_point")
        self.assertEqual(ff.effect_timing, "persistent")

    def test_spell_context_meta_exists(self):
        meta = CombatService.UTILITY_SPELL_CONTEXT_META.get("faerie_fire")
        self.assertIsInstance(meta, dict)
        assert isinstance(meta, dict)
        self.assertEqual(meta.get("initialSaveAbility"), "dexterity")
        self.assertTrue(meta.get("grantsAttackAdvantageAgainstTarget"))
        self.assertTrue(meta.get("suppressesInvisibilityBenefit"))
        self.assertEqual(meta.get("lightType"), "dim")
        self.assertEqual(meta.get("lightRadiusMeters"), 3)

    def test_automation_registry_entry_exists(self):
        spec = CombatService._get_spell_automation_spec("faerie_fire")
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.handler_name, "_cast_faerie_fire_automation")


class FaerieFireCastTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        self.attacker = self.state.participants[0]
        self.enemy = self.state.participants[1]

    def _spell_context(self):
        return {
            "spell_name": "Faerie Fire",
            "spell_canonical_key": "faerie_fire",
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
            "side_meters": 6,
            "duration_seconds": 60,
            "concentration": True,
            "action_cost": "action",
            "source_kind": "prepared_spell",
            "save_ability": "dexterity",
            "save_dc": 14,
            "save_success_outcome": "none",
            "elemental_affinity_eligible": False,
            "elemental_affinity_damage_type": None,
            "elemental_affinity_bonus": None,
            "material_component_consumed": False,
            "consumable_material_options_json": None,
        }

    async def test_failed_save_applies_faerie_fire_effect_without_area_hazard(self):
        targeting_result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=[self.enemy["ref_id"]],
            target_kind="",
            spatial_metadata=SpatialMetadata(
                affected_cells=[{"x": 10, "y": 10}],
                affected_token_ids=[],
                area_shape="cube",
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
            "app.services.combat_service.spells.cast_area_faerie_fire.resolve_saving_throw",
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
        ):
            result = await CombatService._cast_area_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id=self.attacker["id"],
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="faerie_fire",
                ),
                attacker=self.attacker,
                attacker_model=SimpleNamespace(),
                actor_user_id="user-1",
                is_gm=False,
                state=self.state,
                spell_context=self._spell_context(),
                area_spec={"shape": "cube", "size_meters": 6, "range_meters": 18},
            )

        self.assertEqual(result["spell_canonical_key"], "faerie_fire")
        self.assertIsNone(result["active_area_effect"])
        self.assertEqual(self.state.active_area_effects or [], [])
        effects = self.enemy.get("active_effects") or []
        ff_effects = [e for e in effects if (e.get("metadata") or {}).get("source_spell_key") == "faerie_fire"]
        self.assertEqual(len(ff_effects), 1)
        meta = ff_effects[0]["metadata"]
        self.assertTrue(meta.get("faerie_fire"))
        self.assertTrue(meta.get("suppresses_invisibility_benefit"))
        self.assertEqual(meta.get("light_type"), "dim")
        self.assertEqual(meta.get("light_radius_meters"), 3)

    async def test_successful_save_does_not_apply_effect(self):
        targeting_result = TargetingResult(
            is_valid=True,
            validated_primary_target_ref_id="",
            affected_target_ref_ids=[self.enemy["ref_id"]],
            target_kind="",
            spatial_metadata=SpatialMetadata(
                affected_cells=[{"x": 10, "y": 10}],
                affected_token_ids=[],
                area_shape="cube",
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
        roll_result = SimpleNamespace(success=True, total=17, check_modifier_sources=[], is_gm_roll=False)

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
            "app.services.combat_service.spells.cast_area_faerie_fire.resolve_saving_throw",
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
        ):
            await CombatService._cast_area_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id=self.attacker["id"],
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="faerie_fire",
                ),
                attacker=self.attacker,
                attacker_model=SimpleNamespace(),
                actor_user_id="user-1",
                is_gm=False,
                state=self.state,
                spell_context=self._spell_context(),
                area_spec={"shape": "cube", "size_meters": 6, "range_meters": 18},
            )

        effects = self.enemy.get("active_effects") or []
        ff_effects = [e for e in effects if (e.get("metadata") or {}).get("source_spell_key") == "faerie_fire"]
        self.assertEqual(ff_effects, [])


class FaerieFireAdvantageTests(TestCombatServiceBase):
    def test_advantage_when_target_has_faerie_fire_and_visible(self):
        target = _participant(
            extra_effects=[_faerie_fire_effect("grp-1")],
        )
        ctx = resolve_attack_advantage(_participant(), target, attack_kind="ranged", attacker_can_see_target=True)
        self.assertIn("faerie_fire", ctx.advantage_sources)
        self.assertEqual(ctx.result, "advantage")

    def test_no_advantage_when_target_has_faerie_fire_but_not_visible(self):
        target = _participant(
            extra_effects=[_faerie_fire_effect("grp-1")],
        )
        ctx = resolve_attack_advantage(_participant(), target, attack_kind="ranged", attacker_can_see_target=False)
        self.assertNotIn("faerie_fire", ctx.advantage_sources)

    def test_invisible_target_with_faerie_fire_suppresses_invisibility_disadvantage(self):
        target = _participant(
            conditions=["invisible"],
            extra_effects=[_faerie_fire_effect("grp-1")],
        )
        ctx = resolve_attack_advantage(_participant(), target, attack_kind="ranged", attacker_can_see_target=True)
        self.assertNotIn("target_invisible", ctx.disadvantage_sources)
        self.assertIn("faerie_fire", ctx.advantage_sources)


class FaerieFireCleanupTests(TestCombatServiceBase):
    def test_clear_concentration_removes_only_matching_group(self):
        caster1 = self.state.participants[0]
        caster2 = {
            "id": "p2",
            "ref_id": "player-456",
            "kind": "player",
            "display_name": "Second Caster",
            "initiative": None,
            "status": "active",
            "team": "players",
            "visible": True,
            "actor_user_id": "user-2",
            "active_effects": [],
        }
        target = self.state.participants[1]
        self.state.participants.append(caster2)
        target["active_effects"] = [
            {"kind": "condition", "condition_type": "invisible", "metadata": {}},
            _faerie_fire_effect("grp-1", source_id=caster1["id"]),
            _faerie_fire_effect("grp-2", source_id=caster2["id"]),
        ]

        CombatService._clear_concentration_for_source(self.state, source_participant_id=caster1["id"])
        effects = target.get("active_effects") or []
        ff_groups = sorted(
            (e.get("metadata") or {}).get("concentration_group")
            for e in effects
            if (e.get("metadata") or {}).get("source_spell_key") == "faerie_fire"
        )
        self.assertEqual(ff_groups, ["grp-2"])
        self.assertTrue(any(e.get("kind") == "condition" and e.get("condition_type") == "invisible" for e in effects))
