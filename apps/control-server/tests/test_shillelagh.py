from __future__ import annotations

import inspect
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat_spells import CombatCastSpellRequest
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.out_of_combat_cast import _SPECIAL_OOC_UTILITY_SPELLS, build_persisted_effects
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


class ShillelaghSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "shillelagh"),
            None,
        )

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry)

    def test_contract(self):
        self.assertEqual(self.entry["level"], 0)
        self.assertEqual(self.entry["school"], "transmutation")
        self.assertIn("Druid", self.entry["classesJson"])
        self.assertEqual(self.entry["castingTimeType"], "bonus_action")
        self.assertEqual(self.entry["rangeMeters"], 1.5)
        self.assertEqual(self.entry["durationSeconds"], 60)
        self.assertFalse(self.entry["concentration"])
        self.assertFalse(self.entry["ritual"])
        self.assertEqual(self.entry["resolutionType"], "utility")
        self.assertEqual(self.entry["selectionType"], "self")
        self.assertEqual(self.entry["attackType"], "none")
        self.assertNotIn("damageDice", self.entry)
        self.assertNotIn("savingThrow", self.entry)
        self.assertIsNone(self.entry.get("cantripScaling"))
        self.assertIsNone(self.entry.get("upcast"))
        self.assertNotIn("outOfCombatCastable", self.entry)


class ShillelaghSchemaTests(unittest.TestCase):
    def test_accepts_camel_case_weapon_item_id(self):
        req = CombatCastSpellRequest.model_validate(
            {
                "spell_canonical_key": "shillelagh",
                "weaponItemId": "inv-1",
            }
        )
        self.assertEqual(req.weapon_item_id, "inv-1")

    def test_accepts_snake_case_weapon_item_id(self):
        req = CombatCastSpellRequest.model_validate(
            {
                "spell_canonical_key": "shillelagh",
                "weapon_item_id": "inv-1",
            }
        )
        self.assertEqual(req.weapon_item_id, "inv-1")


class ShillelaghTargetingAndRegistryTests(unittest.TestCase):
    def test_targeting_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "shillelagh"})
        self.assertEqual(sem.selection_type, "self")
        self.assertEqual(sem.target_anchor, "caster")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.range_kind, "touch")
        self.assertEqual(sem.effect_timing, "persistent")

    def test_registry_entry(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("shillelagh")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.default_mode, "utility")
        self.assertFalse(spec.requires_effect_payload)
        self.assertEqual(spec.handler_name, "_cast_shillelagh_automation")


class ShillelaghAutomationTests(unittest.IsolatedAsyncioTestCase):
    def _state(self) -> CombatState:
        return CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "caster-p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Druida",
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "u1",
                    "active_effects": [],
                }
            ],
        )

    async def test_requires_weapon_item_id(self):
        state = self._state()
        attacker = state.participants[0]
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_shillelagh_automation(
                MagicMock(),
                "s1",
                attacker=attacker,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(variant_key=None, weapon_item_id=None),
                state=state,
                spell_context={
                    "spell_name": "Bordão Místico",
                    "spell_canonical_key": "shillelagh",
                },
                target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_creates_effect_and_recast_replaces_previous(self):
        state = self._state()
        attacker = state.participants[0]
        attacker["active_effects"] = [
            {
                "id": "old",
                "kind": "spell_effect",
                "metadata": {"source_spell_key": "shillelagh", "weapon_item_id": "inv-old"},
            }
        ]
        req = SimpleNamespace(variant_key=None, weapon_item_id="inv-new")
        with (
            patch.object(CombatService, "_resolve_player_weapon_item", return_value=(
                SimpleNamespace(id="inv-new", is_equipped=True),
                SimpleNamespace(name="Bordão", canonical_key_snapshot="quarterstaff"),
            )),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=100),
        ):
            result = await CombatService._cast_shillelagh_automation(
                MagicMock(),
                "s1",
                attacker=attacker,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context={
                    "spell_name": "Bordão Místico",
                    "spell_canonical_key": "shillelagh",
                    "spell_mode": "utility",
                    "spell_level": 0,
                    "slot_level": None,
                },
                target_participant=None,
            )
        effects = attacker["active_effects"]
        self.assertEqual(len(effects), 1)
        metadata = effects[0]["metadata"]
        self.assertEqual(metadata["source_spell_key"], "shillelagh")
        self.assertEqual(metadata["weapon_item_id"], "inv-new")
        self.assertEqual(metadata["override_damage_die"], "1d8")
        self.assertEqual(metadata["override_attack_ability"], "spellcasting")
        self.assertTrue(metadata["damage_counts_as_magical"])
        self.assertEqual(result["action_kind"], "utility")


class ShillelaghWeaponOverrideTests(unittest.TestCase):
    def test_override_uses_spellcasting_ability_modifier(self):
        attacker_data = {
            "abilities": {"strength": 8, "wisdom": 18},
            "spellcasting": {"ability": "wisdom"},
        }
        override = CombatService._resolve_shillelagh_weapon_override(
            attacker_data=attacker_data,
            attacker_effects=[
                {
                    "metadata": {
                        "source_spell_key": "shillelagh",
                        "weapon_item_id": "inv-1",
                    }
                }
            ],
            inventory_item_id="inv-1",
            weapon_canonical_key="quarterstaff",
            weapon_range_type="melee",
        )
        self.assertIsNotNone(override)
        self.assertEqual(override["attack_ability"], "wisdom")
        self.assertEqual(override["damage_ability"], "wisdom")
        self.assertEqual(override["attack_ability_mod"], 4)
        self.assertEqual(override["damage_die"], "1d8")
        self.assertTrue(override["damage_counts_as_magical"])

    def test_override_does_not_apply_to_other_weapon(self):
        override = CombatService._resolve_shillelagh_weapon_override(
            attacker_data={"abilities": {"strength": 10, "wisdom": 16}, "spellcasting": {"ability": "wisdom"}},
            attacker_effects=[
                {"metadata": {"source_spell_key": "shillelagh", "weapon_item_id": "inv-1"}}
            ],
            inventory_item_id="inv-2",
            weapon_canonical_key="quarterstaff",
            weapon_range_type="melee",
        )
        self.assertIsNone(override)


class ShillelaghOocScopeTests(unittest.TestCase):
    def test_not_in_special_ooc_utility_spells(self):
        self.assertNotIn("shillelagh", _SPECIAL_OOC_UTILITY_SPELLS)

    def test_no_build_persisted_effects_branch(self):
        src = inspect.getsource(build_persisted_effects)
        self.assertNotIn('canonical_key == "shillelagh"', src)


if __name__ == "__main__":
    unittest.main()
