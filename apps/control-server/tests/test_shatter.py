"""Tests for Shatter (Despedaçar).

Covers:
- Seed contract: level 2, sphere 3m, CON save, half_damage on success, 3d8 thunder, upcast +1d8/level
- Registry: targeting semantics (point/immediate) + descriptive context metadata
- Upcast damage dice scaling: slot 2=3d8, slot 3=4d8, slot 4=5d8
- Half-damage rounding via _resolve_save_damage_amount
- Inorganic material predicate (explicit metadata only, no creature-type heuristic)
- Per-save inorganic disadvantage hook wired into the area save loop
"""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from _combat_test_shared import TestCombatServiceBase
from app.models.combat import CombatPhase
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest, CombatGridCell
from app.schemas.roll import RollActorStats
from app.services.combat import CombatService
from app.services.combat_service.spell_dice_math import CombatSpellDiceMathMixin
from app.services.shatter import is_inorganic_participant
from app.services.spell_targeting_semantics import explicit_spell_targeting_overrides
from app.services.combat_service.targeting_result import SpatialMetadata, TargetingResult
from app.services.seed_paths import resolve_base_seed_path


def _apply_upcast(base_dice: str, slot_level: int, spell_level: int = 2, upcast_config=None):
    if upcast_config is None:
        upcast_config = {"mode": "extra_damage_dice", "dice": "1d8", "perLevel": 1}
    result = CombatSpellDiceMathMixin._apply_structured_spell_upcast(
        spell_level=spell_level,
        slot_level=slot_level,
        effect_kind="damage",
        effect_dice=base_dice,
        effect_bonus=0,
        upcast=upcast_config,
    )
    return result["effect_dice"]


class ShatterSeedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_path = resolve_base_seed_path(__file__, "base_spells.seed.json")
        with open(seed_path) as f:
            raw = json.load(f)
        spells = raw["spells"] if isinstance(raw, dict) else raw
        cls.entry = next(
            (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "shatter"),
            None,
        )

    def test_seed_entry_exists(self):
        self.assertIsNotNone(self.entry, "shatter not found in seed")

    def test_seed_basic_fields(self):
        entry = self.entry
        assert entry is not None
        self.assertEqual(entry.get("level"), 2)
        self.assertEqual(entry.get("school"), "evocation")
        self.assertEqual(set(entry.get("classesJson") or []), {"Bard", "Sorcerer", "Warlock", "Wizard"})
        self.assertEqual(entry.get("rangeMeters"), 18)
        self.assertEqual(entry.get("durationSeconds"), 0)
        self.assertFalse(entry.get("concentration"))
        self.assertEqual(entry.get("resolutionType"), "damage")
        self.assertEqual(entry.get("savingThrow"), "CON")
        self.assertEqual(entry.get("saveSuccessOutcome"), "half_damage")
        self.assertEqual(entry.get("damageDice"), "3d8")
        self.assertEqual(entry.get("damageType"), "Thunder")
        self.assertEqual(entry.get("areaShape"), "sphere")
        self.assertEqual(entry.get("radiusMeters"), 3)
        self.assertFalse(entry.get("outOfCombatCastable"))

    def test_seed_upcast(self):
        entry = self.entry
        assert entry is not None
        self.assertEqual(entry.get("upcast"), {"mode": "extra_damage_dice", "dice": "1d8", "perLevel": 1})


class ShatterRegistryTests(unittest.TestCase):
    def test_targeting_semantics_override_exists(self):
        semantics = explicit_spell_targeting_overrides().get("shatter")
        self.assertIsNotNone(semantics)
        assert semantics is not None
        self.assertEqual(semantics.selection_type, "point")
        self.assertEqual(semantics.effect_timing, "immediate")

    def test_context_meta_descriptive_flags(self):
        meta = CombatService.UTILITY_SPELL_CONTEXT_META.get("shatter")
        self.assertIsInstance(meta, dict)
        assert isinstance(meta, dict)
        self.assertEqual(meta.get("type"), "area_damage")
        self.assertTrue(meta.get("inorganicCreatureSaveDisadvantage"))
        self.assertEqual(meta.get("inorganicMaterials"), ["stone", "crystal", "metal"])
        self.assertTrue(meta.get("affectsNonmagicalObjects"))
        self.assertTrue(meta.get("affectsUnwornUncarriedObjects"))
        self.assertFalse(meta.get("outOfCombatCastable"))


class ShatterUpcastTests(unittest.TestCase):
    def test_slot_2_base(self):
        self.assertEqual(_apply_upcast("3d8", slot_level=2), "3d8")

    def test_slot_3_adds_1d8(self):
        self.assertEqual(_apply_upcast("3d8", slot_level=3), "4d8")

    def test_slot_4_adds_2d8(self):
        self.assertEqual(_apply_upcast("3d8", slot_level=4), "5d8")


class ShatterHalfDamageTests(unittest.TestCase):
    def test_failed_save_full_damage(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(15, is_saved=False, save_success_outcome="half_damage"),
            15,
        )

    def test_save_half_rounds_down(self):
        self.assertEqual(
            CombatService._resolve_save_damage_amount(15, is_saved=True, save_success_outcome="half_damage"),
            7,
        )
        self.assertEqual(
            CombatService._resolve_save_damage_amount(14, is_saved=True, save_success_outcome="half_damage"),
            7,
        )


class ShatterInorganicPredicateTests(unittest.TestCase):
    def test_material_type_inorganic(self):
        for material in ("stone", "crystal", "metal"):
            self.assertTrue(is_inorganic_participant({"material_type": material}), material)

    def test_metadata_material_inorganic(self):
        self.assertTrue(is_inorganic_participant({"metadata": {"material_type": "Crystal"}}))

    def test_tag_inorganic(self):
        self.assertTrue(is_inorganic_participant({"creature_tags": ["inorganic"]}))
        self.assertTrue(is_inorganic_participant({"metadata": {"tags": ["metal", "large"]}}))

    def test_organic_or_missing_is_false(self):
        self.assertFalse(is_inorganic_participant({"material_type": "flesh"}))
        self.assertFalse(is_inorganic_participant({"creature_type": "construct"}))  # no heuristic
        self.assertFalse(is_inorganic_participant({}))
        self.assertFalse(is_inorganic_participant(None))


class ShatterSaveModeHookTests(unittest.TestCase):
    def test_shatter_inorganic_gets_disadvantage(self):
        mode, source = CombatService._area_save_spell_specific_mode(
            {"spell_canonical_key": "shatter"}, {"material_type": "metal"}
        )
        self.assertEqual(mode, "disadvantage")
        self.assertEqual(source, "shatter_inorganic_material")

    def test_shatter_organic_normal(self):
        mode, source = CombatService._area_save_spell_specific_mode(
            {"spell_canonical_key": "shatter"}, {"material_type": "flesh"}
        )
        self.assertEqual(mode, "normal")
        self.assertIsNone(source)

    def test_non_shatter_normal_even_if_inorganic(self):
        mode, source = CombatService._area_save_spell_specific_mode(
            {"spell_canonical_key": "fireball"}, {"material_type": "metal"}
        )
        self.assertEqual(mode, "normal")
        self.assertIsNone(source)


def _make_map_targeting_result(affected_ref_ids):
    return TargetingResult(
        is_valid=True,
        validated_primary_target_ref_id=affected_ref_ids[0] if affected_ref_ids else "",
        affected_target_ref_ids=affected_ref_ids,
        target_kind="session_entity",
        spatial_metadata=SpatialMetadata(
            source_token_id="tok_player",
            affected_token_ids=[f"tok_{r}" for r in affected_ref_ids],
            affected_cells=[{"x": 10, "y": 10}],
            area_shape="sphere",
            map_version=1,
            targeting_authority="limiar_map",
        ),
    )


def _make_shatter_catalog_entry():
    return MagicMock(
        canonical_key="shatter",
        name_en="Shatter",
        name_pt="Despedaçar",
        level=2,
        resolution_type="saving_throw",
        saving_throw="constitution",
        save_success_outcome="half_damage",
        damage_type="thunder",
        damage_dice="3d8",
        heal_dice=None,
        upcast_json=None,
        casting_time_type="action",
        target_type="ranged",
        area_shape="sphere",
        range_meters=18,
        radius_meters=3,
        cover_applies_to_save="physical",
        material_component_consumed=False,
        consumable_material_options_json=None,
        concentration=False,
        duration=None,
        effects_json=None,
        max_targets=None,
        variants_json=None,
        persistent_area_json=None,
        requires_target_hearing=None,
        on_end_effects_json=None,
        attack_advantage_condition_json=None,
        material_component_text=None,
    )


def _make_attacker_state():
    return SessionState(
        id="state-player",
        session_id="session-123",
        player_user_id="player-123",
        state_json={
            "abilities": {"intelligence": 18},
            "spellcasting": {
                "spells": [{"name": "Shatter", "canonicalKey": "shatter", "level": 2, "prepared": True}],
                "slots": {"2": {"used": 0, "max": 2}},
            },
        },
    )


def _make_roll_actor_stats(ref_id):
    return RollActorStats(
        display_name="Target",
        abilities={"constitution": 10},
        actor_kind="session_entity",
        actor_ref_id=ref_id,
    )


class ShatterCastIntegrationTests(TestCombatServiceBase):
    def setUp(self):
        super().setUp()
        self.state.phase = CombatPhase.active
        self.state.current_turn_index = 0
        # enemy-123 (organic Goblin) already present; add an inorganic golem.
        self.state.participants.append({
            "id": "g1",
            "ref_id": "golem-1",
            "kind": "session_entity",
            "display_name": "Stone Golem",
            "initiative": None,
            "status": "active",
            "team": "enemies",
            "visible": True,
            "actor_user_id": None,
            "material_type": "stone",
        })

    async def test_inorganic_target_rolls_save_with_disadvantage(self):
        captured: dict[str, str] = {}

        def _save_side_effect(stats, **kwargs):
            captured[stats.actor_ref_id] = kwargs.get("advantage_mode")
            return MagicMock(total=12, success=True, check_modifier_sources=[])

        mock_save = MagicMock(side_effect=_save_side_effect)
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), \
             patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                   return_value=_make_shatter_catalog_entry()), \
             patch("app.services.combat.CombatService._get_stats",
                   return_value=(_make_attacker_state(), 30, 30, 12, 3, 4)), \
             patch("app.services.combat.CombatService._build_roll_actor_stats_for_save",
                   side_effect=lambda _db, _sid, ref_id, *a, **kw: _make_roll_actor_stats(ref_id)), \
             patch("app.services.combat_service.spells.cast_area.get_combat_targeting_service",
                   return_value=SimpleNamespace(validate=MagicMock(
                       return_value=_make_map_targeting_result(["enemy-123", "golem-1"])))), \
             patch("app.services.combat.CombatService._get_area_per_target_cover",
                   return_value={"enemy-123": None, "golem-1": None}), \
             patch("app.services.combat_service.spells.cast_area.resolve_saving_throw", mock_save), \
             patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock), \
             patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock):
            result = await CombatService.cast_spell(
                self.db,
                "session-123",
                CombatCastSpellRequest(
                    actor_participant_id="p1",
                    origin_cell=CombatGridCell(x=8, y=8),
                    anchor_cell=CombatGridCell(x=10, y=10),
                    spell_canonical_key="shatter",
                ),
                "user-1",
                False,
            )

        # Inorganic golem rolled with disadvantage; organic goblin rolled normal.
        self.assertEqual(captured.get("golem-1"), "disadvantage")
        self.assertEqual(captured.get("enemy-123"), "normal")
        # Area save+damage produces a pending spell, not an immediate effect.
        self.assertTrue(result.get("effect_roll_required"))
        self.assertIsNotNone(result.get("pending_spell_id"))
        # Outcome records the inorganic disadvantage source for the golem.
        outcomes = {o["target_ref_id"]: o for o in result.get("area_target_outcomes", [])}
        self.assertEqual(
            outcomes["golem-1"].get("save_disadvantage_sources"),
            ["shatter_inorganic_material"],
        )
        self.assertEqual(outcomes["enemy-123"].get("save_disadvantage_sources"), [])
        # No persistent participant effect created by the cast.
        for participant in self.state.participants:
            self.assertEqual(participant.get("active_effects") or [], [])
