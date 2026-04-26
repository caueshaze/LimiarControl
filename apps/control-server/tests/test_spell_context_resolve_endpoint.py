from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatResolveSpellContextRequest
from app.services.combat import CombatService, CombatServiceError


def _build_state() -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
          {
              "id": "p1",
              "ref_id": "player-1",
              "kind": "player",
              "display_name": "Hero",
              "initiative": 10,
              "status": "active",
              "team": "players",
              "visible": True,
              "actor_user_id": "user-1",
          },
          {
              "id": "e1",
              "ref_id": "enemy-1",
              "kind": "session_entity",
              "display_name": "Goblin",
              "initiative": 8,
              "status": "active",
              "team": "enemies",
              "visible": True,
              "actor_user_id": None,
          },
        ],
    )


def _build_attacker_state() -> SessionState:
    return SessionState(
        id="state-1",
        session_id="session-1",
        player_user_id="user-1",
        state_json={
            "level": 5,
            "abilities": {
                "intelligence": 18,
                "charisma": 18,
            },
            "spellcasting": {
                "spells": [
                    {
                        "name": "Magic Missile",
                        "canonicalKey": "magic_missile",
                        "level": 1,
                        "prepared": True,
                    },
                    {
                        "name": "Eldritch Blast",
                        "canonicalKey": "eldritch_blast",
                        "level": 0,
                        "prepared": True,
                    },
                    {
                        "name": "Acid Splash",
                        "canonicalKey": "acid_splash",
                        "level": 0,
                        "prepared": True,
                    },
                ],
                "slots": {
                    "1": {"used": 0, "max": 4},
                    "2": {"used": 0, "max": 3},
                    "3": {"used": 0, "max": 2},
                },
            },
        },
    )


def _catalog_spell(**overrides):
    defaults = {
        "canonical_key": "magic_missile",
        "name_en": "Magic Missile",
        "name_pt": "Mísseis Mágicos",
        "level": 1,
        "resolution_type": "damage",
        "saving_throw": None,
        "save_success_outcome": None,
        "damage_type": "Force",
        "damage_dice": "3d4+3",
        "heal_dice": None,
        "upcast_json": {
            "mode": "additional_effect_instances",
            "dice": "1d4+1",
            "perLevel": 1,
            "baseEffectInstances": 3,
        },
        "cantrip_scaling_json": None,
        "casting_time_type": "action",
        "target_type": "ranged",
        "selection_type": "creature",
        "origin_type": "caster",
        "target_anchor": "selected_target",
        "attack_type": "none",
        "range_kind": "distance",
        "effect_timing": "immediate",
        "area_shape": None,
        "range_meters": 36,
        "radius_meters": None,
        "length_meters": None,
        "side_meters": None,
        "duration": "Instantaneous",
        "concentration": False,
        "cover_applies_to_save": None,
        "max_targets": 3,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class ResolveSpellContextTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = _build_state()
        self.attacker_state = _build_attacker_state()

    def _get_stats_side_effect(self, _db, ref_id, kind, _session_id):
        if ref_id == "player-1" and kind == "player":
            return (self.attacker_state, 12, 10, 10, 3, 4)
        raise AssertionError(f"Unexpected _get_stats lookup for {ref_id}/{kind}")

    def _resolve(self, req: CombatResolveSpellContextRequest, catalog_spell):
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=catalog_spell,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=self._get_stats_side_effect,
        ):
            return CombatService.resolve_spell_context(
                self.db,
                "session-1",
                req,
                "user-1",
                False,
            )

    def test_resolves_magic_missile_slot_1_effect_instance_count_3(self):
        result = self._resolve(
            CombatResolveSpellContextRequest(
                actor_participant_id="p1",
                spell_canonical_key="magic_missile",
                spell_mode="direct_damage",
                slot_level=1,
            ),
            _catalog_spell(),
        )

        self.assertEqual(result["spell_name"], "Mísseis Mágicos")
        self.assertEqual(result["spell_level"], 1)
        self.assertEqual(result["slot_level"], 1)
        self.assertEqual(result["effect_instance_count"], 3)
        self.assertEqual(result["effect_instance_dice"], "1d4+1")
        self.assertEqual(result["damage_preview"], "3d4+3")

    def test_resolves_magic_missile_slot_3_effect_instance_count_5(self):
        result = self._resolve(
            CombatResolveSpellContextRequest(
                actor_participant_id="p1",
                spell_canonical_key="magic_missile",
                spell_mode="direct_damage",
                slot_level=3,
            ),
            _catalog_spell(),
        )

        self.assertEqual(result["slot_level"], 3)
        self.assertEqual(result["effect_instance_count"], 5)
        self.assertEqual(result["upcast_added_instances"], 2)
        self.assertEqual(result["upcast_instance_effect_dice"], "1d4+1")
        self.assertEqual(result["damage_preview"], "5d4+5")

    def test_resolves_eldritch_blast_level_5_effect_instance_count_2(self):
        result = self._resolve(
            CombatResolveSpellContextRequest(
                actor_participant_id="p1",
                spell_canonical_key="eldritch_blast",
            ),
            _catalog_spell(
                canonical_key="eldritch_blast",
                name_en="Eldritch Blast",
                name_pt="Explosão Eldritch",
                level=0,
                damage_dice="1d10",
                cantrip_scaling_json={
                    "scalingMode": "character_level",
                    "scalingEffectType": "effect_instances",
                    "thresholds": [
                        {"characterLevel": 1, "instances": 1, "instanceDamage": {"dice": "1d10"}},
                        {"characterLevel": 5, "instances": 2, "instanceDamage": {"dice": "1d10"}},
                    ],
                },
                upcast_json=None,
                attack_type="ranged_spell",
            ),
        )

        self.assertEqual(result["resolution_type"], "spell_attack")
        self.assertTrue(result["requires_attack_roll"])
        self.assertEqual(result["effect_instance_count"], 2)
        self.assertEqual(result["effect_instance_dice"], "1d10")
        self.assertEqual(result["damage_preview"], "2d10")

    def test_resolves_acid_splash_level_5_effect_instance_count_1(self):
        result = self._resolve(
            CombatResolveSpellContextRequest(
                actor_participant_id="p1",
                spell_canonical_key="acid_splash",
            ),
            _catalog_spell(
                canonical_key="acid_splash",
                name_en="Acid Splash",
                name_pt="Acid Splash",
                level=0,
                damage_dice="1d6",
                damage_type="Acid",
                saving_throw="DEX",
                save_success_outcome="none",
                cantrip_scaling_json={
                    "scalingMode": "character_level",
                    "scalingEffectType": "damage_dice",
                    "thresholds": [
                        {"characterLevel": 1, "damage": {"dice": "1d6"}},
                        {"characterLevel": 5, "damage": {"dice": "2d6"}},
                    ],
                },
                upcast_json=None,
            ),
        )

        self.assertEqual(result["resolution_type"], "saving_throw")
        self.assertTrue(result["requires_saving_throw"])
        self.assertEqual(result["effect_instance_count"], 1)
        self.assertIsNone(result["effect_instance_dice"])
        self.assertEqual(result["damage_preview"], "2d6")

    def test_resolve_spell_context_does_not_alter_combat_state(self):
        self.state.participants[0]["pending_attack"] = {"id": "pending-1"}

        self._resolve(
            CombatResolveSpellContextRequest(
                actor_participant_id="p1",
                spell_canonical_key="magic_missile",
                spell_mode="direct_damage",
                slot_level=3,
            ),
            _catalog_spell(),
        )

        self.assertEqual(
            self.state.participants[0]["pending_attack"],
            {"id": "pending-1"},
        )

    def test_invalid_slot_returns_clear_error(self):
        with self.assertRaises(CombatServiceError) as context:
            self._resolve(
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="magic_missile",
                    spell_mode="direct_damage",
                    slot_level=9,
                ),
                _catalog_spell(),
            )

        self.assertIn("Spell slot level 9 is not available", str(context.exception))

    def test_spell_not_available_on_sheet_returns_existing_authorization_error(self):
        self.attacker_state.state_json["spellcasting"]["spells"] = []

        with self.assertRaises(CombatServiceError) as context:
            self._resolve(
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="magic_missile",
                    spell_mode="direct_damage",
                    slot_level=1,
                ),
                _catalog_spell(),
            )

        self.assertIn("Spell is not available on the player's sheet.", str(context.exception))
