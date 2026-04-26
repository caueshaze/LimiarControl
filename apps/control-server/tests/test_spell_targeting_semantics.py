from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.services.combat import CombatService
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


def _source(**overrides):
    base = {
        "canonical_key": "custom_spell",
        "target_type": "ranged",
        "area_shape": None,
        "range_meters": 18,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _req(**overrides):
    base = {
        "spell_mode": None,
        "is_heal": False,
        "is_attack": False,
        "slot_level": None,
        "dice_expression": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class SpellTargetingSemanticsTests(unittest.TestCase):
    def assert_semantics(self, source, expected: dict[str, str]) -> None:
        resolved = resolve_spell_targeting_semantics(source)
        self.assertEqual(resolved.to_dict(), expected)

    def test_required_spell_overrides(self) -> None:
        cases = {
            "fire_bolt": {
                "selection_type": "creature_or_object",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "ranged_spell",
                "range_kind": "distance",
                "effect_timing": "immediate",
            },
            "thorn_whip": {
                "selection_type": "creature",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "melee_spell",
                "range_kind": "distance",
                "effect_timing": "immediate",
            },
            "fireball": {
                "selection_type": "point",
                "origin_type": "selected_point",
                "target_anchor": "selected_point",
                "attack_type": "none",
                "range_kind": "distance",
                "effect_timing": "immediate",
            },
            "burning_hands": {
                "selection_type": "direction",
                "origin_type": "caster",
                "target_anchor": "caster",
                "attack_type": "none",
                "range_kind": "self",
                "effect_timing": "immediate",
            },
            "thunderwave": {
                "selection_type": "direction",
                "origin_type": "caster",
                "target_anchor": "caster",
                "attack_type": "none",
                "range_kind": "self",
                "effect_timing": "immediate",
            },
            "cure_wounds": {
                "selection_type": "creature",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "none",
                "range_kind": "touch",
                "effect_timing": "immediate",
            },
            "shield": {
                "selection_type": "none",
                "origin_type": "caster",
                "target_anchor": "caster",
                "attack_type": "none",
                "range_kind": "self",
                "effect_timing": "triggered",
            },
            "spike_growth": {
                "selection_type": "point",
                "origin_type": "selected_point",
                "target_anchor": "selected_point",
                "attack_type": "none",
                "range_kind": "distance",
                "effect_timing": "persistent",
            },
            "hail_of_thorns": {
                "selection_type": "none",
                "origin_type": "caster",
                "target_anchor": "trigger_target",
                "attack_type": "none",
                "range_kind": "self",
                "effect_timing": "triggered",
            },
            "ensnaring_strike": {
                "selection_type": "none",
                "origin_type": "caster",
                "target_anchor": "trigger_target",
                "attack_type": "none",
                "range_kind": "self",
                "effect_timing": "triggered",
            },
        }

        for canonical_key, expected in cases.items():
            with self.subTest(canonical_key=canonical_key):
                self.assert_semantics(_source(canonical_key=canonical_key), expected)

    def test_legacy_target_type_backfill(self) -> None:
        self.assert_semantics(
            _source(target_type="self"),
            {
                "selection_type": "self",
                "origin_type": "caster",
                "target_anchor": "caster",
                "attack_type": "none",
                "range_kind": "self",
                "effect_timing": "immediate",
            },
        )
        self.assert_semantics(
            _source(target_type="touch"),
            {
                "selection_type": "creature",
                "origin_type": "caster",
                "target_anchor": "selected_target",
                "attack_type": "none",
                "range_kind": "touch",
                "effect_timing": "immediate",
            },
        )
        self.assert_semantics(
            _source(target_type="ranged", area_shape="sphere"),
            {
                "selection_type": "point",
                "origin_type": "selected_point",
                "target_anchor": "selected_point",
                "attack_type": "none",
                "range_kind": "distance",
                "effect_timing": "immediate",
            },
        )
        self.assert_semantics(
            _source(target_type="ranged", area_shape="cone", range_meters=0),
            {
                "selection_type": "direction",
                "origin_type": "caster",
                "target_anchor": "caster",
                "attack_type": "none",
                "range_kind": "self",
                "effect_timing": "immediate",
            },
        )


class SpellContextTargetingSemanticsTests(unittest.TestCase):
    def test_spell_attack_mode_comes_from_attack_type(self) -> None:
        resolved = CombatService._resolve_spell_mode_and_targeting(
            _req(),
            _source(
                canonical_key="custom_ranged_attack",
                selection_type="creature",
                origin_type="caster",
                target_anchor="selected_target",
                attack_type="ranged_spell",
                range_kind="distance",
                effect_timing="immediate",
                resolution_type="damage",
                saving_throw=None,
                casting_time_type="action",
            ),
            "custom_ranged_attack",
            0,
            2,
            3,
            "spellcasting",
        )

        self.assertEqual(resolved["spell_mode"], "spell_attack")
        self.assertEqual(resolved["targeting_semantics"].attack_type, "ranged_spell")

    def test_ranged_target_type_does_not_imply_spell_attack(self) -> None:
        resolved = CombatService._resolve_spell_mode_and_targeting(
            _req(),
            _source(
                canonical_key="custom_direct_damage",
                target_type="ranged",
                range_meters=36,
                area_shape=None,
                resolution_type="damage",
                saving_throw=None,
                casting_time_type="action",
            ),
            "custom_direct_damage",
            1,
            2,
            3,
            "spellcasting",
        )

        self.assertEqual(resolved["spell_mode"], "direct_damage")
        self.assertEqual(resolved["targeting_semantics"].attack_type, "none")

    def test_required_spell_context_modes(self) -> None:
        cases = {
            "fire_bolt": "spell_attack",
            "thorn_whip": "spell_attack",
            "magic_missile": "direct_damage",
            "shield": "utility",
            "spike_growth": "utility",
            "hail_of_thorns": "utility",
            "ensnaring_strike": "utility",
        }

        for canonical_key, expected_mode in cases.items():
            with self.subTest(canonical_key=canonical_key):
                resolved = CombatService._resolve_spell_mode_and_targeting(
                    _req(),
                    _source(
                        canonical_key=canonical_key,
                        resolution_type="damage",
                        saving_throw=None,
                        casting_time_type="action",
                    ),
                    canonical_key,
                    1,
                    2,
                    3,
                    "spellcasting",
                )
                self.assertEqual(resolved["spell_mode"], expected_mode)


class SpellCantripScalingTests(unittest.TestCase):
    def test_character_level_scaling_uses_cantrip_breakpoints(self) -> None:
        cases = {
            1: "1d6",
            4: "1d6",
            5: "2d6",
            10: "2d6",
            11: "3d6",
            16: "3d6",
            17: "4d6",
            20: "4d6",
        }

        for caster_level, expected in cases.items():
            with self.subTest(caster_level=caster_level):
                self.assertEqual(
                    CombatService._apply_character_level_cantrip_scaling(
                        spell_level=0,
                        caster_level=caster_level,
                        effect_dice="1d6",
                        cantrip_scaling={
                            "mode": "character_level",
                            "thresholds": [
                                {"characterLevel": 1, "damage": {"dice": "1d6"}},
                                {"characterLevel": 5, "damage": {"dice": "2d6"}},
                                {"characterLevel": 11, "damage": {"dice": "3d6"}},
                                {"characterLevel": 17, "damage": {"dice": "4d6"}},
                            ],
                        },
                    ),
                    expected,
                )

    def test_cantrip_scaling_requires_explicit_catalog_config(self) -> None:
        self.assertEqual(
            CombatService._apply_character_level_cantrip_scaling(
                spell_level=0,
                caster_level=17,
                effect_dice="1d6",
            ),
            "1d6",
        )

    def test_character_level_scaling_does_not_apply_to_leveled_spells(self) -> None:
        self.assertEqual(
            CombatService._apply_character_level_cantrip_scaling(
                spell_level=1,
                caster_level=17,
                effect_dice="1d6",
            ),
            "1d6",
        )

    def test_structured_additional_effect_instances_upcast_adds_configured_dice(self) -> None:
        result = CombatService._apply_structured_spell_upcast(
            spell_level=1,
            slot_level=3,
            effect_kind="damage",
            effect_dice="3d4+3",
            effect_bonus=0,
            upcast={"mode": "additional_effect_instances", "dice": "1d4+1", "perLevel": 1},
        )

        self.assertEqual(result["effect_dice"], "5d4+5")
        self.assertEqual(result["upcast_levels"], 2)
        self.assertEqual(result["upcast_added_instances"], 2)
        self.assertEqual(result["upcast_instance_effect_dice"], "1d4+1")
        self.assertTrue(result["upcast_applied"])


class SpellTargetingSeedTests(unittest.TestCase):
    def test_seed_contains_required_targeting_overrides(self) -> None:
        seed_path = Path(__file__).resolve().parents[3] / "Base" / "base_spells.seed.json"
        spells = {
            entry["canonicalKey"]: entry
            for entry in json.loads(seed_path.read_text(encoding="utf-8"))["spells"]
        }

        expected = {
            "acid_splash": ("creature", "none", "immediate"),
            "fire_bolt": ("creature_or_object", "ranged_spell", "immediate"),
            "thorn_whip": ("creature", "melee_spell", "immediate"),
            "fireball": ("point", "none", "immediate"),
            "burning_hands": ("direction", "none", "immediate"),
            "thunderwave": ("direction", "none", "immediate"),
            "cure_wounds": ("creature", "none", "immediate"),
            "shield": ("none", "none", "triggered"),
            "spike_growth": ("point", "none", "persistent"),
            "hail_of_thorns": ("none", "none", "triggered"),
            "ensnaring_strike": ("none", "none", "triggered"),
        }

        for canonical_key, (selection_type, attack_type, effect_timing) in expected.items():
            with self.subTest(canonical_key=canonical_key):
                entry = spells[canonical_key]
                self.assertEqual(entry["selectionType"], selection_type)
                self.assertEqual(entry["attackType"], attack_type)
                self.assertEqual(entry["effectTiming"], effect_timing)

        acid_splash = spells["acid_splash"]
        self.assertEqual(acid_splash["maxTargets"], 2)
        self.assertNotIn("areaShape", acid_splash)
        self.assertNotIn("upcast", acid_splash)
        self.assertEqual(
            [
                threshold["damage"]["dice"]
                for threshold in acid_splash["cantripScaling"]["thresholds"]
            ],
            ["1d6", "2d6", "3d6", "4d6"],
        )

        self.assertEqual(spells["magic_missile"]["maxTargets"], 3)
        self.assertEqual(
            spells["magic_missile"]["upcast"]["mode"],
            "additional_effect_instances",
        )
        self.assertNotIn("cantripScaling", spells["magic_missile"])

        self.assertEqual(spells["sacred_flame"]["coverAppliesToSave"], "none")
