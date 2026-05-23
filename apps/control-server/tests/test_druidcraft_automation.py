from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat import CombatService
from app.services.combat_service.exceptions import CombatServiceError
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics
from app.services.out_of_combat_cast import (
    _SPECIAL_OOC_UTILITY_SPELLS,
    build_persisted_effects,
)


def _state() -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        use_map=True,
        map_selection={"gridWidth": 10, "gridHeight": 10, "blockedCells": [], "obstacles": []},
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Druida",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "u1",
                "position": {"x": 1, "y": 1},
                "active_effects": [],
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            }
        ],
    )


def _ctx() -> dict:
    return {
        "spell_canonical_key": "druidcraft",
        "spell_name": "Druidismo",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "utility",
    }


class TestDruidcraftCatalogAndSemantics(unittest.TestCase):
    def _seed(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        return {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_entry(self):
        s = self._seed()["druidcraft"]
        self.assertEqual(s["level"], 0)
        self.assertEqual(s["school"], "transmutation")
        self.assertIn("Druid", s["classesJson"])
        self.assertEqual(s["rangeMeters"], 9)
        self.assertEqual(s["resolutionType"], "narrative_utility")
        self.assertFalse(s["concentration"])
        self.assertFalse(s["ritual"])
        self.assertNotIn("damageDice", s)
        self.assertNotIn("saveAbility", s)
        self.assertEqual(s["attackType"], "none")
        self.assertEqual(s["targetType"], "self")
        self.assertEqual(s["selectionType"], "none")
        self.assertEqual(s["targetAnchor"], "caster")
        self.assertEqual(s["effectTiming"], "immediate")

    def test_semantics(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "druidcraft"})
        self.assertEqual(sem.selection_type, "none")
        self.assertEqual(sem.target_anchor, "caster")


class TestDruidcraftAutomation(unittest.IsolatedAsyncioTestCase):
    async def test_cast_creates_narrative_timed_effect(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}},
        )
        req = SimpleNamespace(description="uma flor desabrocha na mão do druida")
        with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=1000):
            result = await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=attacker_model,
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )
        effects = attacker_model.state_json.get("active_spell_effects", [])
        self.assertEqual(len(effects), 1)
        eff = effects[0]
        self.assertEqual(eff["duration_type"], "timed")
        self.assertEqual(eff["expires_at_game_time_seconds"], 4600)
        self.assertEqual(eff["metadata"]["source_spell_key"], "druidcraft")
        self.assertFalse(eff["metadata"]["mechanical"])
        self.assertTrue(eff["metadata"]["narrative"])
        self.assertEqual(eff["metadata"]["description"], "uma flor desabrocha na mão do druida")
        self.assertIn("created_effect_id", result)
        self.assertEqual(result["created_effect_id"], eff["id"])
        self.assertEqual(result["damage"], 0)
        self.assertIsNone(result["is_hit"])
        self.assertIsNone(result["is_saved"])

    async def test_description_validation_empty(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1", attacker=state.participants[0], attacker_model=attacker_model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(description="   "),
                state=state, spell_context=_ctx(), target_participant=None,
            )

    async def test_description_validation_too_long(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1", attacker=state.participants[0], attacker_model=attacker_model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(description="x" * 301),
                state=state, spell_context=_ctx(), target_participant=None,
            )

    async def test_description_validation_missing(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1", attacker=state.participants[0], attacker_model=attacker_model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(),
                state=state, spell_context=_ctx(), target_participant=None,
            )

    async def test_default_variant_when_absent(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        req = SimpleNamespace(description="folhas caem suavemente")
        with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=1000):
            result = await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=attacker_model,
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )
        self.assertEqual(result["selected_variant_key"], "minor_natural_sensory_effect")
        effects = attacker_model.state_json.get("active_spell_effects", [])
        self.assertEqual(effects[0]["metadata"]["selected_variant_key"], "minor_natural_sensory_effect")

    async def test_valid_variant(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        req = SimpleNamespace(description="previsão de chuva amanhã", variant_key="weather_prediction")
        with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=1000):
            result = await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=attacker_model,
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )
        self.assertEqual(result["selected_variant_key"], "weather_prediction")

    async def test_invalid_variant_returns_400(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        req = SimpleNamespace(description="algo", variant_key="invalid_variant")
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=attacker_model,
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )

    async def test_no_mechanical_effects(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        req = SimpleNamespace(description="acender uma vela")
        with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=1000):
            result = await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=attacker_model,
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )
        self.assertEqual(result["action_kind"], "utility")
        self.assertEqual(result["damage"], 0)
        self.assertEqual(result["healing"], 0)
        self.assertIsNone(result["is_hit"])
        self.assertIsNone(result["is_saved"])
        self.assertIsNone(result["save_ability"])
        self.assertIsNone(result["save_dc"])
        self.assertIsNone(result["roll"])
        self.assertIsNone(result["pending_spell_id"])

    async def test_allowed_effects_in_metadata(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        req = SimpleNamespace(description="uma semente brota")
        with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=1000):
            await CombatService._cast_druidcraft_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=attacker_model,
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )
        effects = attacker_model.state_json.get("active_spell_effects", [])
        allowed = effects[0]["metadata"]["allowed_effects"]
        self.assertIn("weather_prediction", allowed)
        self.assertIn("minor_natural_sensory_effect", allowed)
        self.assertIn("plant_bloom", allowed)
        self.assertIn("harmless_natural_effect", allowed)
        self.assertIn("ignite_or_extinguish_small_flame", allowed)


class TestDruidcraftOutOfCombat(unittest.TestCase):
    def test_in_special_ooc_set(self):
        self.assertIn("druidcraft", _SPECIAL_OOC_UTILITY_SPELLS)

    def test_build_persisted_effects_returns_narrative(self):
        spell = MagicMock()
        spell.canonical_key = "druidcraft"
        spell.name_pt = "Druidismo"
        spell.name_en = "Druidcraft"
        spell.concentration = False
        spell.effects_json = []
        spell.variants_json = []
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="user-1",
            target_user_id="user-1",
            variant_key=None,
            game_time_seconds=5000,
        )
        self.assertEqual(len(effects), 1)
        eff = effects[0]
        self.assertEqual(eff["kind"], "spell_effect")
        self.assertEqual(eff["duration_type"], "timed")
        self.assertEqual(eff["expires_at_game_time_seconds"], 5000 + 3600)
        meta = eff["metadata"]
        self.assertEqual(meta["source_spell_key"], "druidcraft")
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["narrative"])
        self.assertEqual(meta["context_origin"], "out_of_combat_cast")
        self.assertIn("allowed_effects", meta)
        self.assertIn("weather_prediction", meta["allowed_effects"])
