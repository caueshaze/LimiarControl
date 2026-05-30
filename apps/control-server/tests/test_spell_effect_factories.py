from __future__ import annotations

import unittest

from app.services.spell_effect_factories import (
    SpellEffectBuildContext,
    build_barkskin_effect,
    build_blur_effect,
    build_jump_effect,
    build_protection_from_evil_and_good_effect,
    build_shillelagh_effect,
    build_spider_climb_effect,
)


def _normalize_metadata_for_mechanical_parity(metadata: dict) -> dict:
    normalized = dict(metadata)
    for key in (
        "context_origin",
        "created_out_of_combat",
        "source_participant_id",
        "caster_player_user_id",
        "target_player_user_id",
        "owner_participant_id",
        "created_by_participant_id",
        "selected_variant_key",
        "selected_variant_label",
    ):
        normalized.pop(key, None)
    return normalized


def _combat_ctx(spell_key: str, spell_name: str, duration_seconds: int) -> SpellEffectBuildContext:
    return SpellEffectBuildContext(
        spell_key=spell_key,
        spell_name=spell_name,
        game_time_seconds=100,
        duration_seconds=duration_seconds,
        concentration=True,
        concentration_group="cg-1",
        source_participant_id="src-1",
        owner_participant_id="owner-1",
        created_by_participant_id="src-1",
        context_origin="combat",
    )


def _ooc_ctx(spell_key: str, spell_name: str, duration_seconds: int) -> SpellEffectBuildContext:
    return SpellEffectBuildContext(
        spell_key=spell_key,
        spell_name=spell_name,
        game_time_seconds=100,
        duration_seconds=duration_seconds,
        concentration=True,
        concentration_group="cg-1",
        source_participant_id=None,
        owner_participant_id="user-2",
        created_by_participant_id="user-1",
        context_origin="out_of_combat_cast",
        caster_user_id="user-1",
        target_user_id="user-2",
        created_out_of_combat=True,
    )


class SpellEffectFactoriesTests(unittest.TestCase):
    def test_timed_shape_and_expiration(self):
        effect = build_barkskin_effect(_combat_ctx("barkskin", "Barkskin", 3600))
        self.assertEqual(effect["kind"], "spell_effect")
        self.assertEqual(effect["duration_type"], "timed")
        self.assertEqual(effect["created_at_game_time_seconds"], 100)
        self.assertEqual(effect["expires_at_game_time_seconds"], 3700)

    def test_protection_contains_rich_metadata(self):
        effect = build_protection_from_evil_and_good_effect(
            _combat_ctx("protection_from_evil_and_good", "Protection", 600)
        )
        md = effect["metadata"]
        self.assertTrue(md["condition_immunity"])
        self.assertIn("declarative_effect", md)
        self.assertIn("declarative_save_effect", md)
        self.assertEqual(md["declarative_effect"]["type"], "attack_disadvantage_against_target")
        self.assertEqual(
            md["declarative_save_effect"]["type"],
            "saving_throw_advantage_against_creature_types",
        )

    def test_blur_contains_declarative_attack_disadvantage(self):
        effect = build_blur_effect(_combat_ctx("blur", "Blur", 60))
        md = effect["metadata"]
        self.assertEqual(md["source_spell_key"], "blur")
        self.assertEqual(md["declarative_effect"]["type"], "attack_disadvantage_against_target")
        self.assertEqual(md["declarative_effect"]["params"]["mode"], "disadvantage")

    def test_barkskin_contains_ac_floor_metadata(self):
        effect = build_barkskin_effect(_combat_ctx("barkskin", "Barkskin", 3600))
        md = effect["metadata"]
        self.assertEqual(md["armor_class_floor"], 16)
        self.assertTrue(md["sets_minimum_ac"])
        self.assertFalse(md["is_flat_bonus"])

    def test_concentration_group_preserved(self):
        effect = build_blur_effect(_combat_ctx("blur", "Blur", 60))
        self.assertEqual(effect["metadata"]["concentration_group"], "cg-1")

    def test_protection_combat_ooc_mechanical_parity(self):
        combat = build_protection_from_evil_and_good_effect(
            _combat_ctx("protection_from_evil_and_good", "Protection", 600)
        )
        ooc = build_protection_from_evil_and_good_effect(
            _ooc_ctx("protection_from_evil_and_good", "Protection", 600)
        )
        self.assertEqual(
            _normalize_metadata_for_mechanical_parity(combat["metadata"]),
            _normalize_metadata_for_mechanical_parity(ooc["metadata"]),
        )

    def test_blur_combat_ooc_mechanical_parity(self):
        combat = build_blur_effect(_combat_ctx("blur", "Blur", 60))
        ooc = build_blur_effect(_ooc_ctx("blur", "Blur", 60))
        self.assertEqual(
            _normalize_metadata_for_mechanical_parity(combat["metadata"]),
            _normalize_metadata_for_mechanical_parity(ooc["metadata"]),
        )

    def test_barkskin_combat_ooc_mechanical_parity(self):
        combat = build_barkskin_effect(_combat_ctx("barkskin", "Barkskin", 3600))
        ooc = build_barkskin_effect(_ooc_ctx("barkskin", "Barkskin", 3600))
        self.assertEqual(
            _normalize_metadata_for_mechanical_parity(combat["metadata"]),
            _normalize_metadata_for_mechanical_parity(ooc["metadata"]),
        )

    def test_jump_contains_movement_metadata(self):
        effect = build_jump_effect(_combat_ctx("jump", "Jump", 60))
        md = effect["metadata"]
        self.assertTrue(md["movement_modifier"])
        self.assertEqual(md["jump_distance_multiplier"], 3)
        self.assertTrue(md["affects_jump_distance"])

    def test_spider_climb_contains_movement_mode_metadata(self):
        effect = build_spider_climb_effect(_combat_ctx("spider_climb", "Spider Climb", 3600))
        md = effect["metadata"]
        self.assertEqual(md["movement_mode"], "spider_climb")
        self.assertTrue(md["grants_climb_speed"])
        self.assertTrue(md["can_move_on_ceilings"])

    def test_shillelagh_contains_weapon_and_override_metadata(self):
        effect = build_shillelagh_effect(
            SpellEffectBuildContext(
                spell_key="shillelagh",
                spell_name="Shillelagh",
                game_time_seconds=100,
                duration_seconds=60,
                concentration=False,
                concentration_group=None,
                source_participant_id="src-1",
                owner_participant_id="owner-1",
                created_by_participant_id="src-1",
                context_origin="combat",
                extra_metadata={
                    "weapon_item_id": "inv-1",
                    "weapon_key": "club",
                    "weapon_name": "Club",
                    "weapon_canonical_key": "club",
                },
            )
        )
        md = effect["metadata"]
        self.assertEqual(md["weapon_item_id"], "inv-1")
        self.assertEqual(md["weapon_key"], "club")
        self.assertEqual(md["override_damage_die"], "1d8")
        self.assertTrue(md["damage_counts_as_magical"])

    def test_jump_combat_ooc_mechanical_parity(self):
        combat = build_jump_effect(_combat_ctx("jump", "Jump", 60))
        ooc = build_jump_effect(_ooc_ctx("jump", "Jump", 60))
        self.assertEqual(
            _normalize_metadata_for_mechanical_parity(combat["metadata"]),
            _normalize_metadata_for_mechanical_parity(ooc["metadata"]),
        )

    def test_spider_climb_combat_ooc_mechanical_parity(self):
        combat = build_spider_climb_effect(_combat_ctx("spider_climb", "Spider Climb", 3600))
        ooc = build_spider_climb_effect(_ooc_ctx("spider_climb", "Spider Climb", 3600))
        self.assertEqual(
            _normalize_metadata_for_mechanical_parity(combat["metadata"]),
            _normalize_metadata_for_mechanical_parity(ooc["metadata"]),
        )

    def test_shillelagh_combat_ooc_mechanical_parity(self):
        combat = build_shillelagh_effect(
            SpellEffectBuildContext(
                spell_key="shillelagh",
                spell_name="Shillelagh",
                game_time_seconds=100,
                duration_seconds=60,
                concentration=False,
                concentration_group=None,
                source_participant_id="src-1",
                owner_participant_id="owner-1",
                created_by_participant_id="src-1",
                context_origin="combat",
                extra_metadata={
                    "weapon_item_id": "inv-1",
                    "weapon_key": "club",
                    "weapon_name": "Club",
                    "weapon_canonical_key": "club",
                },
            )
        )
        ooc = build_shillelagh_effect(
            SpellEffectBuildContext(
                spell_key="shillelagh",
                spell_name="Shillelagh",
                game_time_seconds=100,
                duration_seconds=60,
                concentration=False,
                concentration_group=None,
                source_participant_id=None,
                owner_participant_id="user-1",
                created_by_participant_id="user-1",
                context_origin="out_of_combat_cast",
                caster_user_id="user-1",
                target_user_id="user-1",
                created_out_of_combat=True,
                extra_metadata={
                    "weapon_item_id": "inv-1",
                    "weapon_key": "club",
                    "weapon_name": "Club",
                    "weapon_canonical_key": "club",
                },
            )
        )
        self.assertEqual(
            _normalize_metadata_for_mechanical_parity(combat["metadata"]),
            _normalize_metadata_for_mechanical_parity(ooc["metadata"]),
        )


if __name__ == "__main__":
    unittest.main()
