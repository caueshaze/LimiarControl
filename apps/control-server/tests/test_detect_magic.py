from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatCastSpellRequest
from app.services.combat import CombatService
from app.services.combat_service.persistent_effects import derive_active_concentration, restore_persisted_effects
from app.services.out_of_combat_cast import (
    build_persisted_effects,
    check_out_of_combat_cast_eligibility,
    has_castable_effects,
)
from app.services.persistent_effect_expiry import prune_expired_persisted_effects_from_state


class DetectMagicSeedTests(unittest.TestCase):
    def test_detect_magic_seed_contract(self):
        payload = json.loads(open("Base/base_spells.seed.json", encoding="utf-8").read())
        raw = next(entry for entry in payload["spells"] if entry["canonicalKey"] == "detect_magic")

        self.assertEqual(raw["level"], 1)
        self.assertEqual(raw["school"], "divination")
        self.assertEqual(raw["castingTimeType"], "action")
        self.assertEqual(raw["rangeKind"], "self")
        self.assertEqual(raw["rangeMeters"], 0)
        self.assertTrue(raw["concentration"])
        self.assertTrue(raw["ritual"])
        self.assertEqual(raw["selectionType"], "self")
        self.assertEqual(raw["targetAnchor"], "caster")
        self.assertEqual(raw["attackType"], "none")
        self.assertEqual(raw.get("savingThrow"), None)
        self.assertEqual(raw.get("damageDice"), None)
        self.assertEqual(raw.get("upcast"), None)


class DetectMagicRegistryTests(unittest.TestCase):
    def test_detect_magic_is_registered_as_special_handler(self):
        registry = CombatService._SPELL_AUTOMATION_REGISTRY
        self.assertIn("detect_magic", registry)
        self.assertEqual(registry["detect_magic"].handler_name, "_cast_detect_magic_automation")


class DetectMagicCombatCastTests(unittest.IsolatedAsyncioTestCase):
    def _state(self) -> CombatState:
        return CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "caster",
                    "kind": "player",
                    "display_name": "Lia",
                    "status": "active",
                    "team": "players",
                    "actor_user_id": "u1",
                    "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
                    "active_effects": [],
                }
            ],
            use_map=False,
        )

    async def test_cast_consumes_slot_and_applies_narrative_spell_effect_with_concentration(self):
        state = self._state()
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {
                "slots": {"1": {"used": 0, "max": 2}},
                "spells": [{"canonicalKey": "detect_magic", "name": "Detect Magic", "prepared": True, "level": 1}],
            }
        }
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="detect_magic", slot_level=1)
        spell_context = {
            "spell_name": "Detect Magic",
            "spell_canonical_key": "detect_magic",
            "spell_mode": "utility",
            "selection_type": "self",
            "slot_level": 1,
            "action_cost": "action",
            "source_kind": "spell",
            "effect_kind": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "target_type": "self",
            "range_kind": "self",
            "attack_type": "none",
            "requires_target_sight": False,
            "requires_target_effect": False,
            "concentration": True,
            "effect_timing": "persistent",
        }

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=1000),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 1)
        effect = effects[0]
        metadata = effect.get("metadata") or {}
        self.assertEqual(effect.get("kind"), "spell_effect")
        self.assertEqual(effect.get("duration_type"), "timed")
        self.assertEqual(effect.get("created_at_game_time_seconds"), 1000)
        self.assertEqual(effect.get("expires_at_game_time_seconds"), 1600)
        self.assertEqual(metadata.get("source_spell_key"), "detect_magic")
        self.assertFalse(metadata.get("mechanical"))
        self.assertTrue(metadata.get("narrative"))
        self.assertTrue(metadata.get("visible_to_all"))
        self.assertEqual(metadata.get("utility"), "detect_magic")
        self.assertEqual(metadata.get("radius_meters"), 9)
        self.assertTrue(metadata.get("can_reveal_aura_with_action"))
        self.assertTrue(metadata.get("reveals_magic_school"))
        self.assertEqual((metadata.get("blocked_by") or {}).get("stone_cm"), 30)
        self.assertTrue(metadata.get("concentration"))
        self.assertIsInstance(metadata.get("concentration_group"), str)
        self.assertIsInstance(result.get("concentration_group"), str)
        self.assertEqual(result.get("pending_spell_id"), None)
        self.assertEqual(result.get("pending_save_id"), None)

    async def test_replaces_existing_concentration_group_from_same_caster(self):
        state = self._state()
        state.participants[0]["active_effects"] = [
            {
                "id": "old-1",
                "kind": "spell_effect",
                "duration_type": "manual",
                "source_participant_id": "p1",
                "metadata": {
                    "concentration": True,
                    "concentration_group": "grp-old",
                    "source_spell_key": "shield_of_faith",
                },
            }
        ]

        with (
            patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=200),
        ):
            result = await CombatService._cast_detect_magic_automation(
                MagicMock(),
                "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=MagicMock(),
                state=state,
                spell_context={"spell_name": "Detect Magic", "spell_canonical_key": "detect_magic", "concentration": True},
                target_participant=state.participants[0],
            )

        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 1)
        self.assertEqual((effects[0].get("metadata") or {}).get("source_spell_key"), "detect_magic")
        self.assertNotEqual((effects[0].get("metadata") or {}).get("concentration_group"), "grp-old")
        self.assertIsInstance(result.get("concentration_group"), str)


class DetectMagicOutOfCombatTests(unittest.TestCase):
    def _spell(self):
        return SimpleNamespace(
            canonical_key="detect_magic",
            name_en="Detect Magic",
            name_pt="Detectar Magia",
            concentration=True,
            out_of_combat_castable=True,
            out_of_combat_target="self",
            effects_json=None,
            variants_json=[],
            level=1,
            ritual=True,
        )

    def test_ooc_special_spell_is_castable_without_declarative_effects(self):
        spell = self._spell()
        self.assertTrue(has_castable_effects(spell))
        ok, rejection = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 1}}}},
            slot_level=1,
            variant_key=None,
            out_of_combat_target="self",
            target_user_id="u1",
            caster_user_id="u1",
            target_state_json={},
        )
        self.assertTrue(ok)
        self.assertIsNone(rejection)

    def test_ritual_runtime_not_supported_yet_slot_still_required(self):
        spell = self._spell()
        ok, rejection = check_out_of_combat_cast_eligibility(
            spell=spell,
            state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 1}}}},
            slot_level=None,
            variant_key=None,
            out_of_combat_target="self",
            target_user_id="u1",
            caster_user_id="u1",
            target_state_json={},
        )
        self.assertFalse(ok)
        self.assertIn("slotLevel must be >= 1", str(rejection))

    def test_builds_timed_narrative_effect_and_active_concentration(self):
        spell = self._spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u1",
            variant_key=None,
            game_time_seconds=500,
        )
        self.assertEqual(len(effects), 1)
        effect = effects[0]
        meta = effect.get("metadata") or {}
        self.assertEqual(effect.get("duration_type"), "timed")
        self.assertEqual(effect.get("expires_at_game_time_seconds"), 1100)
        self.assertEqual(meta.get("source_spell_key"), "detect_magic")
        self.assertFalse(meta.get("mechanical"))
        self.assertEqual(meta.get("utility"), "detect_magic")
        self.assertEqual(meta.get("radius_meters"), 9)
        self.assertIsInstance(meta.get("concentration_group"), str)

        state_json = {"active_spell_effects": effects}
        active = derive_active_concentration(state_json)
        self.assertIsNotNone(active)
        self.assertEqual(active.get("spellKey"), "detect_magic")

    def test_expired_effect_is_pruned_and_concentration_disappears(self):
        spell = self._spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u1",
            variant_key=None,
            game_time_seconds=100,
        )
        state_json = {"active_spell_effects": effects}
        pruned = prune_expired_persisted_effects_from_state(state_json, game_time_seconds=1000)
        self.assertNotIn("active_spell_effects", pruned)
        self.assertIsNone(derive_active_concentration(pruned))

    def test_restore_to_combat_does_not_duplicate_effect(self):
        spell = self._spell()
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u1",
            variant_key=None,
            game_time_seconds=200,
        )
        session_state = SessionState(
            id="ss1",
            session_id="s1",
            player_user_id="caster",
            state_json={"active_spell_effects": effects},
        )
        db = MagicMock()
        first = MagicMock()
        first.first.return_value = session_state
        db.exec.return_value = first

        participant = {
            "id": "p1",
            "ref_id": "caster",
            "kind": "player",
            "display_name": "Lia",
            "active_effects": [],
        }

        with patch("app.services.combat_service.persistent_effects.get_game_time_seconds", return_value=200):
            restore_persisted_effects(db, "s1", participant)
            restore_persisted_effects(db, "s1", participant)

        active_effects = participant.get("active_effects") or []
        self.assertEqual(len(active_effects), 1)
        self.assertEqual((active_effects[0].get("metadata") or {}).get("source_spell_key"), "detect_magic")


if __name__ == "__main__":
    unittest.main()
