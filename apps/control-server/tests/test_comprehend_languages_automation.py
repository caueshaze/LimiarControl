"""Tests for Comprehend Languages / Compreender Idiomas (issue #395).

Covers:
- Seed contract: level=1, divination, ritual=True, rangeKind=self, durationSeconds=3600
- Targeting semantics: selection_type=none, range_kind=self, effect_timing=persistent
- Runtime handler: no description required, variant_key→400, deduplication on recast
- No mechanical effects: no damage, attack, save, concentration
- OOC support: in _is_ooc_utility_spell + build_persisted_effects
- OOC/combat metadata consistency: same fields, same values

Note: ritual casting runtime is OUT OF SCOPE for this issue.
      This issue only marks ritual=True in seed/context metadata.
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
    _is_ooc_utility_spell,
    build_persisted_effects,
)

_EXPECTED_METADATA_KEYS = {
    "utility",
    "duration_seconds",
    "understands_spoken_languages",
    "understands_written_languages",
    "requires_touch_for_written_text",
    "literal_meaning_only",
    "deciphers_secret_messages",
    "mechanical",
    "narrative",
}


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
                "display_name": "Mago",
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
        "spell_canonical_key": "comprehend_languages",
        "spell_name": "Compreender Idiomas",
        "slot_level": 1,
        "spell_level": 1,
        "spell_mode": "utility",
    }


async def _cast(req=None, *, game_time: int = 1000) -> tuple[dict, SessionState]:
    if req is None:
        req = SimpleNamespace()
    state = _state()
    attacker_model = SessionState(
        id="st1",
        session_id="s1",
        player_user_id="player-1",
        state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}},
    )
    with patch("app.services.combat_service.spells.automation._detection_spells.get_game_time_seconds", return_value=game_time):
        result = await CombatService._cast_comprehend_languages_automation(
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

class ComprehendLanguagesSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        cls.entry = spells.get("comprehend_languages")

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "comprehend_languages not found in seed")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "divination")
        self.assertFalse(e["concentration"])
        self.assertEqual(e["attackType"], "none")
        self.assertEqual(e["targetType"], "self")
        self.assertEqual(e["selectionType"], "none")
        self.assertEqual(e["targetAnchor"], "caster")
        self.assertEqual(e["effectTiming"], "persistent")
        self.assertEqual(e["rangeKind"], "self")
        self.assertEqual(e["rangeMeters"], 0)

    def test_duration_seconds_is_3600(self):
        self.assertEqual(self.entry.get("durationSeconds"), 3600)

    def test_ritual_is_true(self):
        self.assertTrue(self.entry.get("ritual"))

    def test_classes_include_expected(self):
        classes = self.entry.get("classesJson", [])
        for cls_name in ["Bard", "Sorcerer", "Warlock", "Wizard"]:
            self.assertIn(cls_name, classes)

    def test_resolution_type_narrative_utility(self):
        self.assertEqual(self.entry.get("resolutionType"), "narrative_utility")

    def test_no_damage_fields(self):
        self.assertNotIn("damageDice", self.entry)
        self.assertNotIn("damageType", self.entry)

    def test_no_saving_throw(self):
        self.assertNotIn("savingThrow", self.entry)

    def test_no_cantrip_scaling(self):
        self.assertIsNone(self.entry.get("cantripScaling"))

    def test_no_upcast(self):
        self.assertIsNone(self.entry.get("upcast"))


# ---------------------------------------------------------------------------
# Targeting semantics
# ---------------------------------------------------------------------------

class ComprehendLanguagesTargetingSemanticsTests(unittest.TestCase):
    def test_semantics_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "comprehend_languages"})
        self.assertEqual(sem.selection_type, "none")
        self.assertEqual(sem.target_anchor, "caster")
        self.assertEqual(sem.range_kind, "self")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.effect_timing, "persistent")


# ---------------------------------------------------------------------------
# Runtime automation
# ---------------------------------------------------------------------------

class ComprehendLanguagesAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cast_creates_timed_effect(self):
        result, attacker_model = await _cast()
        effects = attacker_model.state_json.get("active_spell_effects", [])
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["duration_type"], "timed")
        self.assertTrue(effects[0]["id"].startswith("narrative_effect:"))

    async def test_expires_in_3600_seconds(self):
        result, attacker_model = await _cast(game_time=2000)
        eff = attacker_model.state_json["active_spell_effects"][0]
        self.assertEqual(eff["expires_at_game_time_seconds"], 5600)

    async def test_effect_has_utility_metadata(self):
        result, attacker_model = await _cast()
        meta = attacker_model.state_json["active_spell_effects"][0]["metadata"]
        self.assertEqual(meta["source_spell_key"], "comprehend_languages")
        self.assertEqual(meta["utility"], "comprehend_languages")
        self.assertEqual(meta["duration_seconds"], 3600)
        self.assertTrue(meta["understands_spoken_languages"])
        self.assertTrue(meta["understands_written_languages"])
        self.assertTrue(meta["requires_touch_for_written_text"])
        self.assertTrue(meta["literal_meaning_only"])
        self.assertFalse(meta["deciphers_secret_messages"])

    async def test_effect_is_not_mechanical(self):
        result, attacker_model = await _cast()
        meta = attacker_model.state_json["active_spell_effects"][0]["metadata"]
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["narrative"])

    async def test_result_has_created_effect_id(self):
        result, attacker_model = await _cast()
        eff = attacker_model.state_json["active_spell_effects"][0]
        self.assertIn("created_effect_id", result)
        self.assertEqual(result["created_effect_id"], eff["id"])

    async def test_no_description_required(self):
        # Cast sem description não deve levantar erro
        result, attacker_model = await _cast(SimpleNamespace())
        self.assertIn("created_effect_id", result)

    async def test_description_present_is_ignored(self):
        # description presente não deve ser persistida nem causar erro
        result, attacker_model = await _cast(SimpleNamespace(description="entender élfico"))
        meta = attacker_model.state_json["active_spell_effects"][0]["metadata"]
        self.assertNotIn("description", meta)

    async def test_variant_key_present_returns_400(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await _cast(SimpleNamespace(variant_key="spoken_only"))
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_recast_deduplicates_previous_effect(self):
        # Cast 1
        _, attacker_model = await _cast(game_time=1000)
        first_id = attacker_model.state_json["active_spell_effects"][0]["id"]
        first_expires = attacker_model.state_json["active_spell_effects"][0]["expires_at_game_time_seconds"]

        # Cast 2 com attacker_model já atualizado, game_time avançado
        state = _state()
        req = SimpleNamespace()
        with patch("app.services.combat_service.spells.automation._detection_spells.get_game_time_seconds", return_value=2000):
            await CombatService._cast_comprehend_languages_automation(
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
        cl_effects = [e for e in effects if e.get("metadata", {}).get("source_spell_key") == "comprehend_languages"]
        # Ainda um só efeito (deduplicação)
        self.assertEqual(len(cl_effects), 1)
        # effect_id mudou (renovado, não o mesmo)
        self.assertNotEqual(cl_effects[0]["id"], first_id)
        # expires_at foi renovado
        self.assertGreater(cl_effects[0]["expires_at_game_time_seconds"], first_expires)
        self.assertEqual(cl_effects[0]["expires_at_game_time_seconds"], 5600)

    async def test_no_damage_no_attack_no_save(self):
        result, _ = await _cast()
        self.assertEqual(result["damage"], 0)
        self.assertEqual(result["healing"], 0)
        self.assertIsNone(result["is_hit"])
        self.assertIsNone(result["is_saved"])
        self.assertIsNone(result["roll"])
        self.assertIsNone(result["pending_spell_id"])

    async def test_no_concentration_marker(self):
        result, attacker_model = await _cast()
        effects = attacker_model.state_json.get("active_spell_effects", [])
        concentration_effects = [e for e in effects if e.get("metadata", {}).get("concentration")]
        self.assertEqual(len(concentration_effects), 0)

    async def test_action_kind_is_utility(self):
        result, _ = await _cast()
        self.assertEqual(result["action_kind"], "utility")


# ---------------------------------------------------------------------------
# OOC support
# ---------------------------------------------------------------------------

class ComprehendLanguagesOOCTests(unittest.TestCase):
    def _ooc_effect(self):
        spell = MagicMock()
        spell.canonical_key = "comprehend_languages"
        spell.name_pt = "Compreender Idiomas"
        spell.name_en = "Comprehend Languages"
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
        return effects

    def test_in_special_ooc_set(self):
        self.assertTrue(_is_ooc_utility_spell("comprehend_languages"))

    def test_build_persisted_effects_returns_narrative_effect(self):
        effects = self._ooc_effect()
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["kind"], "spell_effect")
        self.assertEqual(effects[0]["duration_type"], "timed")

    def test_ooc_effect_expires_in_3600_seconds(self):
        effects = self._ooc_effect()
        self.assertEqual(effects[0]["expires_at_game_time_seconds"], 5000 + 3600)

    def test_ooc_metadata_matches_combat_handler(self):
        """OOC e combat handler devem expor os mesmos campos-chave com os mesmos valores.
        Divergência aqui = bug de 'compreensão só funciona fora de combate'."""
        ooc_meta = self._ooc_effect()[0]["metadata"]

        expected_values = {
            "utility": "comprehend_languages",
            "duration_seconds": 3600,
            "understands_spoken_languages": True,
            "understands_written_languages": True,
            "requires_touch_for_written_text": True,
            "literal_meaning_only": True,
            "deciphers_secret_messages": False,
            "mechanical": False,
            "narrative": True,
        }
        for key, expected in expected_values.items():
            with self.subTest(field=key):
                self.assertEqual(ooc_meta.get(key), expected, f"campo '{key}' difere entre OOC e combat")


# ---------------------------------------------------------------------------
# Ritual (metadata only — runtime out of scope)
# ---------------------------------------------------------------------------

class ComprehendLanguagesRitualTests(unittest.TestCase):
    # Ritual casting runtime está FORA DE ESCOPO da issue #395.
    # Estes testes verificam apenas que o seed e context expõem ritual=True.
    # Quando ritual casting for implementado, adicionar testes de slot consumption aqui.

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        cls.entry = spells.get("comprehend_languages")

    def test_seed_ritual_flag_is_true(self):
        self.assertTrue(self.entry.get("ritual"))

    def test_context_utility_subtype(self):
        from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
        meta = SpellContextResolveMixin._NARRATIVE_UTILITY_META_BY_SPELL.get("comprehend_languages")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["subtype"], "comprehend_languages")
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["narrative"])
