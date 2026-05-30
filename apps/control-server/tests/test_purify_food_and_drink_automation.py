"""Tests for Purify Food and Drink / Purificar Alimentos e Bebidas (issue #402).

Covers:
- Seed contract: level=1, transmutation, concentration=False, ritual=True, rangeMeters=3, durationSeconds=0
- areaShape/radiusMeters are descriptive metadata only — NOT runtime AoE mechanics
- Targeting semantics: selection_type=none, range_kind=distance, effect_timing=immediate
- Runtime handler: instantaneous, no active_effect, no state modification, no concentration
- OOC: in _is_ooc_utility_spell, build_persisted_effects returns [] (intentionally — no false
  persistent effect for an instantaneous spell)
- Context: narrative_utility metadata with purification fields
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
        "spell_canonical_key": "purify_food_and_drink",
        "spell_name": "Purificar Alimentos e Bebidas",
        "slot_level": 1,
        "spell_level": 1,
        "spell_mode": "utility",
    }


async def _cast(req=None) -> tuple[dict, CombatState, SessionState]:
    if req is None:
        req = SimpleNamespace()
    state = _state()
    attacker_model = SessionState(
        id="st1",
        session_id="s1",
        player_user_id="player-1",
        state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}},
    )
    result = await CombatService._cast_purify_food_and_drink_automation(
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
    return result, state, attacker_model


# ---------------------------------------------------------------------------
# Seed contract
# ---------------------------------------------------------------------------

class PurifyFoodDrinkSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        cls.entry = spells.get("purify_food_and_drink")

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "purify_food_and_drink not found in seed")

    def test_canonical_key(self):
        self.assertEqual(self.entry["canonicalKey"], "purify_food_and_drink")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "transmutation")
        self.assertFalse(e["concentration"])
        self.assertTrue(e["ritual"])
        self.assertEqual(e["attackType"], "none")
        self.assertEqual(e["effectTiming"], "immediate")
        self.assertEqual(e["rangeKind"], "distance")
        self.assertEqual(e["rangeMeters"], 3)

    def test_duration_seconds_is_0(self):
        self.assertEqual(self.entry.get("durationSeconds"), 0)

    def test_classes_include_expected(self):
        classes = self.entry.get("classesJson", [])
        for cls_name in ["Cleric", "Druid", "Paladin"]:
            self.assertIn(cls_name, classes)

    def test_resolution_type_narrative_utility(self):
        self.assertEqual(self.entry.get("resolutionType"), "narrative_utility")

    def test_area_metadata(self):
        # areaShape/radiusMeters são metadados descritivos para o frontend/context.
        # Não representam AoE mecânica de dano ou controle no runtime.
        self.assertEqual(self.entry.get("areaShape"), "sphere")
        self.assertEqual(self.entry.get("radiusMeters"), 1.5)

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

class PurifyFoodDrinkTargetingSemanticsTests(unittest.TestCase):
    def test_semantics_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "purify_food_and_drink"})
        self.assertEqual(sem.selection_type, "none")
        self.assertEqual(sem.target_anchor, "caster")
        self.assertEqual(sem.range_kind, "distance")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.effect_timing, "immediate")


# ---------------------------------------------------------------------------
# Runtime automation
# ---------------------------------------------------------------------------

class PurifyFoodDrinkAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_action_kind_is_utility(self):
        result, _, _ = await _cast()
        self.assertEqual(result["action_kind"], "utility")

    async def test_no_damage_no_attack_no_save(self):
        result, _, _ = await _cast()
        self.assertEqual(result["damage"], 0)
        self.assertEqual(result["healing"], 0)
        self.assertIsNone(result["is_hit"])
        self.assertIsNone(result["is_saved"])
        self.assertIsNone(result["roll"])
        self.assertIsNone(result["pending_spell_id"])

    async def test_no_concentration_created(self):
        result, _, _ = await _cast()
        self.assertIsNone(result.get("concentration_group"))

    async def test_cast_does_not_modify_participant_active_effects(self):
        # Cast instantânea não deve criar nenhum active_effect no participante
        result, state, _ = await _cast()
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 0)

    async def test_cast_does_not_modify_state_json(self):
        # state_json deve permanecer inalterado — nenhum active_spell_effects da magia
        result, _, attacker_model = await _cast()
        spell_effects = attacker_model.state_json.get("active_spell_effects") or []
        purify_effects = [
            e for e in spell_effects
            if (e.get("metadata") or {}).get("source_spell_key") == "purify_food_and_drink"
        ]
        self.assertEqual(len(purify_effects), 0)

    async def test_result_has_purify_extra(self):
        result, _, _ = await _cast()
        self.assertEqual(result.get("utility"), "purify_food_and_drink")
        self.assertTrue(result.get("purified_food_and_drink"))
        self.assertEqual(result.get("radius_meters"), 1.5)
        self.assertTrue(result.get("instantaneous"))

    async def test_variant_key_present_returns_400(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await _cast(SimpleNamespace(variant_key="only_food"))
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_no_description_required(self):
        result, _, _ = await _cast(SimpleNamespace())
        self.assertEqual(result["action_kind"], "utility")

    async def test_description_present_is_ignored(self):
        result, state, _ = await _cast(SimpleNamespace(description="purificar a comida"))
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 0)

    async def test_summary_text_describes_purification(self):
        result, _, _ = await _cast()
        summary = result.get("summary_text") or ""
        self.assertIn("purificad", summary.lower())


# ---------------------------------------------------------------------------
# OOC support
# ---------------------------------------------------------------------------

class PurifyFoodDrinkOOCTests(unittest.TestCase):
    def _spell(self):
        spell = MagicMock()
        spell.canonical_key = "purify_food_and_drink"
        spell.name_pt = "Purificar Alimentos e Bebidas"
        spell.name_en = "Purify Food and Drink"
        spell.concentration = False
        spell.effects_json = []
        spell.variants_json = []
        return spell

    def test_in_special_ooc_set(self):
        self.assertTrue(_is_ooc_utility_spell("purify_food_and_drink"))

    def test_build_persisted_effects_returns_empty_list(self):
        # Magia instantânea: OOC retorna [] de propósito.
        # Não deve persistir nenhum efeito falso — purificação não tem estado a gravar.
        effects = build_persisted_effects(
            spell=self._spell(),
            caster_user_id="user-1",
            target_user_id="user-1",
            variant_key=None,
            game_time_seconds=5000,
        )
        self.assertEqual(effects, [])


# ---------------------------------------------------------------------------
# Context resolve
# ---------------------------------------------------------------------------

class PurifyFoodDrinkContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
        cls.meta = SpellContextResolveMixin._NARRATIVE_UTILITY_META_BY_SPELL.get("purify_food_and_drink")

    def test_context_utility_subtype(self):
        self.assertIsNotNone(self.meta)
        self.assertEqual(self.meta["subtype"], "purify_food_and_drink")

    def test_context_type_is_narrative_utility(self):
        self.assertEqual(self.meta["type"], "narrative_utility")

    def test_context_has_expected_fields(self):
        self.assertTrue(self.meta["purifiesFood"])
        self.assertTrue(self.meta["purifiesDrink"])
        self.assertTrue(self.meta["removesPoisonFromFoodAndDrink"])
        self.assertTrue(self.meta["removesDiseaseFromFoodAndDrink"])
        self.assertFalse(self.meta["affectsCreatures"])
        self.assertFalse(self.meta["affectsMagicalFoodOrDrink"])
        self.assertEqual(self.meta["radiusMeters"], 1.5)
        self.assertTrue(self.meta["instantaneous"])
        self.assertFalse(self.meta["mechanical"])
        self.assertTrue(self.meta["narrative"])


# ---------------------------------------------------------------------------
# Ritual (metadata only — runtime out of scope)
# ---------------------------------------------------------------------------

class PurifyFoodDrinkRitualTests(unittest.TestCase):
    # Ritual casting runtime está FORA DE ESCOPO da issue #402.

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        cls.entry = spells.get("purify_food_and_drink")

    def test_seed_ritual_flag_is_true(self):
        self.assertTrue(self.entry.get("ritual"))

    def test_seed_concentration_is_false(self):
        self.assertFalse(self.entry.get("concentration"))
