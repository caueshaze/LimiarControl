"""Tests for Thaumaturgy / Taumaturgia (issue #394).

Covers:
- Seed contract: level=0, transmutation, Cleric, 9m, durationSeconds=60, narrative_utility
- Targeting semantics override: selection_type=none, target_anchor=caster
- Runtime automation: description validation, variant validation, effect structure
- No mechanical side-effects: no damage, no attack roll, no save, no concentration
- expires_at 60s (not 3600s like druidcraft)
- OOC support: thaumaturgy in _SPECIAL_OOC_UTILITY_SPELLS + build_persisted_effects
- Consistency: allowed_effects list is the same in handler, OOC, and context_resolve
"""

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
    _THAUMATURGY_ALLOWED_EFFECTS,
    build_persisted_effects,
)

_EXPECTED_ALLOWED_EFFECTS = frozenset({
    "alter_eyes",
    "booming_voice",
    "flame_omen",
    "harmless_tremor",
    "instantaneous_sound",
    "open_or_close_unlocked_door",
})


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
                "display_name": "Clérigo",
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
        "spell_canonical_key": "thaumaturgy",
        "spell_name": "Taumaturgia",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "utility",
    }


async def _cast(req, *, game_time: int = 1000) -> tuple[dict, SessionState]:
    state = _state()
    attacker_model = SessionState(
        id="st1",
        session_id="s1",
        player_user_id="player-1",
        state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}},
    )
    with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=game_time):
        result = await CombatService._cast_thaumaturgy_automation(
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
    return result, attacker_model


# ---------------------------------------------------------------------------
# Seed contract
# ---------------------------------------------------------------------------

class ThaumaturgySeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        cls.entry = spells.get("thaumaturgy")

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "thaumaturgy not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 0)
        self.assertEqual(e["school"], "transmutation")
        self.assertIn("Cleric", e["classesJson"])
        self.assertEqual(e["rangeMeters"], 9)
        self.assertEqual(e["resolutionType"], "narrative_utility")
        self.assertFalse(e["concentration"])
        self.assertFalse(e["ritual"])
        self.assertEqual(e["attackType"], "none")
        self.assertEqual(e["targetType"], "self")
        self.assertEqual(e["selectionType"], "none")
        self.assertEqual(e["targetAnchor"], "caster")
        self.assertEqual(e["effectTiming"], "immediate")

    def test_duration_seconds_is_60(self):
        self.assertEqual(self.entry.get("durationSeconds"), 60)

    def test_no_damage_fields(self):
        self.assertNotIn("damageDice", self.entry)
        self.assertNotIn("damageType", self.entry)

    def test_no_saving_throw(self):
        self.assertNotIn("savingThrow", self.entry)

    def test_no_cantrip_scaling(self):
        self.assertIsNone(self.entry.get("cantripScaling"))


# ---------------------------------------------------------------------------
# Targeting semantics
# ---------------------------------------------------------------------------

class ThaumaturgyTargetingSemanticsTests(unittest.TestCase):
    def test_semantics_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "thaumaturgy"})
        self.assertEqual(sem.selection_type, "none")
        self.assertEqual(sem.target_anchor, "caster")
        self.assertEqual(sem.range_kind, "distance")
        self.assertEqual(sem.attack_type, "none")


# ---------------------------------------------------------------------------
# Runtime automation
# ---------------------------------------------------------------------------

class ThaumaturgyAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cast_creates_timed_narrative_effect(self):
        result, attacker_model = await _cast(SimpleNamespace(description="voz troveja pelo templo"))
        effects = attacker_model.state_json.get("active_spell_effects", [])
        self.assertEqual(len(effects), 1)
        eff = effects[0]
        self.assertEqual(eff["duration_type"], "timed")
        self.assertTrue(eff["id"].startswith("narrative_effect:"))

    async def test_expires_in_60_seconds(self):
        result, attacker_model = await _cast(SimpleNamespace(description="trovão distante"), game_time=2000)
        eff = attacker_model.state_json["active_spell_effects"][0]
        self.assertEqual(eff["expires_at_game_time_seconds"], 2060)

    async def test_effect_has_correct_metadata(self):
        result, attacker_model = await _cast(SimpleNamespace(description="olhos brilham em âmbar"))
        meta = attacker_model.state_json["active_spell_effects"][0]["metadata"]
        self.assertEqual(meta["source_spell_key"], "thaumaturgy")
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["narrative"])
        self.assertTrue(meta["visible_to_all"])
        self.assertEqual(meta["utility"], "thaumaturgy")
        self.assertEqual(meta["spell_level"], 0)

    async def test_result_has_created_effect_id(self):
        result, attacker_model = await _cast(SimpleNamespace(description="chamas tremeluzem"))
        eff = attacker_model.state_json["active_spell_effects"][0]
        self.assertIn("created_effect_id", result)
        self.assertEqual(result["created_effect_id"], eff["id"])

    async def test_default_variant_when_absent(self):
        result, attacker_model = await _cast(SimpleNamespace(description="voz amplificada"))
        self.assertEqual(result["selected_variant_key"], "booming_voice")
        meta = attacker_model.state_json["active_spell_effects"][0]["metadata"]
        self.assertEqual(meta["selected_variant_key"], "booming_voice")

    async def test_valid_variant_accepted(self):
        for variant in _EXPECTED_ALLOWED_EFFECTS:
            with self.subTest(variant=variant):
                result, _ = await _cast(SimpleNamespace(description="efeito narrativo", variant_key=variant))
                self.assertEqual(result["selected_variant_key"], variant)

    async def test_invalid_variant_returns_400(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await _cast(SimpleNamespace(description="algo", variant_key="summon_demon"))
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_empty_description_returns_400(self):
        with self.assertRaises(CombatServiceError):
            await _cast(SimpleNamespace(description="   "))

    async def test_description_over_300_chars_returns_400(self):
        with self.assertRaises(CombatServiceError):
            await _cast(SimpleNamespace(description="x" * 301))

    async def test_missing_description_returns_400(self):
        with self.assertRaises(CombatServiceError):
            await _cast(SimpleNamespace())

    async def test_no_damage_in_result(self):
        result, _ = await _cast(SimpleNamespace(description="tremor inofensivo"))
        self.assertEqual(result["damage"], 0)
        self.assertEqual(result["healing"], 0)

    async def test_no_pending_attack_or_save(self):
        result, _ = await _cast(SimpleNamespace(description="porta se abre"))
        self.assertIsNone(result["is_hit"])
        self.assertIsNone(result["is_saved"])
        self.assertIsNone(result["roll"])
        self.assertIsNone(result["pending_spell_id"])

    async def test_no_concentration_marker_applied(self):
        result, attacker_model = await _cast(SimpleNamespace(description="som instantâneo"))
        effects = attacker_model.state_json.get("active_spell_effects", [])
        concentration_effects = [
            e for e in effects if e.get("metadata", {}).get("concentration")
        ]
        self.assertEqual(len(concentration_effects), 0)

    async def test_action_kind_is_utility(self):
        result, _ = await _cast(SimpleNamespace(description="voz ressoa"))
        self.assertEqual(result["action_kind"], "utility")

    async def test_effect_has_allowed_effects_in_metadata(self):
        result, attacker_model = await _cast(SimpleNamespace(description="olhos mudam de cor"))
        meta = attacker_model.state_json["active_spell_effects"][0]["metadata"]
        self.assertIn("allowed_effects", meta)
        self.assertEqual(frozenset(meta["allowed_effects"]), _EXPECTED_ALLOWED_EFFECTS)

    async def test_allowed_effects_consistent_with_ooc(self):
        result, attacker_model = await _cast(SimpleNamespace(description="chamas escurecem"))
        handler_effects = frozenset(attacker_model.state_json["active_spell_effects"][0]["metadata"]["allowed_effects"])
        ooc_effects = frozenset(_THAUMATURGY_ALLOWED_EFFECTS)
        self.assertEqual(handler_effects, ooc_effects, "handler e OOC devem expor as mesmas variantes")

    async def test_allowed_effects_consistent_with_context_resolve(self):
        from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
        context_meta = SpellContextResolveMixin._NARRATIVE_UTILITY_META_BY_SPELL.get("thaumaturgy")
        self.assertIsNotNone(context_meta)
        result, attacker_model = await _cast(SimpleNamespace(description="trovão distante"))
        handler_effects = frozenset(attacker_model.state_json["active_spell_effects"][0]["metadata"]["allowed_effects"])
        context_effects = frozenset(context_meta["allowedEffects"])
        self.assertEqual(handler_effects, context_effects, "handler e context_resolve devem expor as mesmas variantes")


# ---------------------------------------------------------------------------
# OOC support
# ---------------------------------------------------------------------------

class ThaumaturgyOOCTests(unittest.TestCase):
    def test_in_special_ooc_set(self):
        self.assertIn("thaumaturgy", _SPECIAL_OOC_UTILITY_SPELLS)

    def test_build_persisted_effects_returns_narrative_effect(self):
        spell = MagicMock()
        spell.canonical_key = "thaumaturgy"
        spell.name_pt = "Taumaturgia"
        spell.name_en = "Thaumaturgy"
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

    def test_ooc_effect_expires_in_60_seconds(self):
        spell = MagicMock()
        spell.canonical_key = "thaumaturgy"
        spell.name_pt = "Taumaturgia"
        spell.name_en = "Thaumaturgy"
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
        self.assertEqual(effects[0]["expires_at_game_time_seconds"], 5060)

    def test_ooc_effect_has_correct_metadata(self):
        spell = MagicMock()
        spell.canonical_key = "thaumaturgy"
        spell.name_pt = "Taumaturgia"
        spell.name_en = "Thaumaturgy"
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
        meta = effects[0]["metadata"]
        self.assertEqual(meta["source_spell_key"], "thaumaturgy")
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["narrative"])
        self.assertEqual(meta["utility"], "thaumaturgy")
        self.assertEqual(meta["context_origin"], "out_of_combat_cast")
        self.assertIn("allowed_effects", meta)
        self.assertEqual(frozenset(meta["allowed_effects"]), _EXPECTED_ALLOWED_EFFECTS)
