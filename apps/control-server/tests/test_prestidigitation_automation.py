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
                "display_name": "Lia",
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
        "spell_canonical_key": "prestidigitation",
        "spell_name": "Prestidigitação",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "utility",
    }


class TestPrestidigitationCatalogAndSemantics(unittest.TestCase):
    def _seed(self):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        return {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_entry(self):
        s = self._seed()["prestidigitation"]
        self.assertEqual(s["level"], 0)
        self.assertEqual(s["school"], "transmutation")
        self.assertEqual(s["rangeMeters"], 3)
        self.assertEqual(s["duration"], "Up to 1 hour")
        self.assertEqual(s["resolutionType"], "narrative_utility")
        self.assertNotIn("damageDice", s)
        self.assertNotIn("saveAbility", s)

    def test_semantics_no_variant_requirement(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "prestidigitation"})
        self.assertEqual(sem.selection_type, "none")
        self.assertEqual(sem.target_anchor, "caster")


class TestPrestidigitationAutomation(unittest.IsolatedAsyncioTestCase):
    async def test_cast_creates_narrative_timed_effect(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}},
        )
        req = SimpleNamespace(description="  marca azul na porta  ")
        with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=1000):
            result = await CombatService._cast_prestidigitation_automation(
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
        self.assertEqual(eff["metadata"]["source_spell_key"], "prestidigitation")
        self.assertFalse(eff["metadata"]["mechanical"])
        self.assertEqual(eff["metadata"]["description"], "marca azul na porta")
        self.assertIn("created_effect_id", result)

    async def test_description_validation(self):
        state = _state()
        attacker_model = SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={},
        )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_prestidigitation_automation(
                MagicMock(), "s1", attacker=state.participants[0], attacker_model=attacker_model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(description="   "),
                state=state, spell_context=_ctx(), target_participant=None,
            )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_prestidigitation_automation(
                MagicMock(), "s1", attacker=state.participants[0], attacker_model=attacker_model,
                actor_user_id="u1", is_gm=False, req=SimpleNamespace(description="x" * 301),
                state=state, spell_context=_ctx(), target_participant=None,
            )

