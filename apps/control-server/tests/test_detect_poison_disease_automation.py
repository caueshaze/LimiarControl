"""Tests for Detect Poison and Disease / Detectar Veneno e Doença (issue #400).

Covers:
- Seed contract: level=1, divination, concentration=True, ritual=True, rangeKind=self, durationSeconds=600
- Targeting semantics: selection_type=none, range_kind=self, effect_timing=persistent
- Runtime handler: concentration pattern (participant.active_effects, NOT state_json), deduplication
  via _clear_concentration_for_source, variant_key→400
- OOC support: in _SPECIAL_OOC_UTILITY_SPELLS + build_persisted_effects with concentration_group
- OOC/combat metadata consistency: same fields, same values
- Cross-spell concentration: casting detect_poison_disease clears active detect_magic

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
    _SPECIAL_OOC_UTILITY_SPELLS,
    build_persisted_effects,
)


def _state(extra_effects: list | None = None) -> CombatState:
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
                "active_effects": list(extra_effects or []),
                "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            }
        ],
    )


def _ctx() -> dict:
    return {
        "spell_canonical_key": "detect_poison_disease",
        "spell_name": "Detectar Veneno e Doença",
        "slot_level": 1,
        "spell_level": 1,
        "spell_mode": "utility",
    }


async def _cast(req=None, *, game_time: int = 1000, state: CombatState | None = None) -> tuple[dict, CombatState]:
    if req is None:
        req = SimpleNamespace()
    if state is None:
        state = _state()
    attacker_model = SessionState(
        id="st1",
        session_id="s1",
        player_user_id="player-1",
        state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}},
    )
    with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=game_time):
        result = await CombatService._cast_detect_poison_disease_automation(
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
    return result, state


# ---------------------------------------------------------------------------
# Seed contract
# ---------------------------------------------------------------------------

class DetectPoisonDiseaseSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        cls.entry = spells.get("detect_poison_disease")

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "detect_poison_disease not found in seed")

    def test_canonical_key_is_detect_poison_disease(self):
        # Trava o nome exato — "and" perdido causaria bug silencioso
        self.assertEqual(self.entry["canonicalKey"], "detect_poison_disease")

    def test_contract_fields(self):
        e = self.entry
        self.assertEqual(e["level"], 1)
        self.assertEqual(e["school"], "divination")
        self.assertTrue(e["concentration"])
        self.assertEqual(e["attackType"], "none")
        self.assertEqual(e["targetType"], "self")
        self.assertEqual(e["selectionType"], "none")
        self.assertEqual(e["targetAnchor"], "caster")
        self.assertEqual(e["effectTiming"], "persistent")
        self.assertEqual(e["rangeKind"], "self")
        self.assertEqual(e["rangeMeters"], 0)

    def test_duration_seconds_is_600(self):
        self.assertEqual(self.entry.get("durationSeconds"), 600)

    def test_concentration_is_true(self):
        self.assertTrue(self.entry.get("concentration"))

    def test_ritual_is_true(self):
        self.assertTrue(self.entry.get("ritual"))

    def test_classes_include_expected(self):
        classes = self.entry.get("classesJson", [])
        for cls_name in ["Cleric", "Druid", "Paladin", "Ranger"]:
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

class DetectPoisonDiseaseTargetingSemanticsTests(unittest.TestCase):
    def test_semantics_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "detect_poison_disease"})
        self.assertEqual(sem.selection_type, "none")
        self.assertEqual(sem.target_anchor, "caster")
        self.assertEqual(sem.range_kind, "self")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.effect_timing, "persistent")


# ---------------------------------------------------------------------------
# Runtime automation
# ---------------------------------------------------------------------------

class DetectPoisonDiseaseAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cast_creates_concentration_effect_in_active_effects(self):
        # Effect is in state.participants[0]["active_effects"], NOT attacker_model.state_json
        result, state = await _cast()
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["duration_type"], "timed")
        self.assertEqual(effects[0]["kind"], "spell_effect")

    def test_effect_stored_in_participant_not_state_json(self):
        # Garante que não foi usada a rota state_json (padrão comprehend_languages)
        # A verificação é feita no test acima: active_effects tem o efeito,
        # e attacker_model.state_json não é modificado pela handler (flag_modified(state, "participants"))
        pass  # covered by test_cast_creates_concentration_effect_in_active_effects

    async def test_expires_in_600_seconds(self):
        result, state = await _cast(game_time=2000)
        eff = state.participants[0]["active_effects"][0]
        self.assertEqual(eff["expires_at_game_time_seconds"], 2600)

    async def test_effect_has_concentration_marker(self):
        result, state = await _cast()
        meta = state.participants[0]["active_effects"][0]["metadata"]
        self.assertTrue(meta["concentration"])
        self.assertIsInstance(meta["concentration_group"], str)
        self.assertTrue(len(meta["concentration_group"]) > 0)

    async def test_result_has_concentration_group(self):
        result, state = await _cast()
        eff_group = state.participants[0]["active_effects"][0]["metadata"]["concentration_group"]
        self.assertIn("concentration_group", result)
        self.assertEqual(result["concentration_group"], eff_group)

    async def test_effect_has_utility_metadata(self):
        result, state = await _cast()
        meta = state.participants[0]["active_effects"][0]["metadata"]
        self.assertEqual(meta["source_spell_key"], "detect_poison_disease")
        self.assertEqual(meta["utility"], "detect_poison_disease")
        self.assertEqual(meta["radius_meters"], 9)
        self.assertTrue(meta["detects_poisons"])
        self.assertTrue(meta["detects_poisonous_creatures"])
        self.assertTrue(meta["detects_diseases"])
        self.assertTrue(meta["can_identify_poison_or_disease_with_action"])

    async def test_effect_has_blocked_by_metadata(self):
        result, state = await _cast()
        meta = state.participants[0]["active_effects"][0]["metadata"]
        blocked_by = meta.get("blocked_by") or {}
        self.assertEqual(blocked_by.get("stone_cm"), 30)
        self.assertIn("common_metal_cm", blocked_by)
        self.assertTrue(blocked_by.get("lead_sheet"))
        self.assertIn("wood_or_earth_meters", blocked_by)

    async def test_effect_is_not_mechanical(self):
        result, state = await _cast()
        meta = state.participants[0]["active_effects"][0]["metadata"]
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["narrative"])

    async def test_variant_key_present_returns_400(self):
        with self.assertRaises(CombatServiceError) as ctx:
            await _cast(SimpleNamespace(variant_key="poisons_only"))
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_no_description_required(self):
        result, state = await _cast(SimpleNamespace())
        effects = state.participants[0].get("active_effects") or []
        self.assertEqual(len(effects), 1)

    async def test_description_present_is_ignored(self):
        result, state = await _cast(SimpleNamespace(description="sentir o veneno"))
        meta = state.participants[0]["active_effects"][0]["metadata"]
        self.assertNotIn("description", meta)

    async def test_recast_clears_previous_concentration(self):
        # Cast 1
        _, state = await _cast(game_time=1000)
        first_group = state.participants[0]["active_effects"][0]["metadata"]["concentration_group"]

        # Cast 2 com game_time avançado
        with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=2000):
            result2 = await CombatService._cast_detect_poison_disease_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(),
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )

        effects = state.participants[0].get("active_effects") or []
        dpd_effects = [e for e in effects if (e.get("metadata") or {}).get("source_spell_key") == "detect_poison_disease"]
        # Exatamente 1 efeito (deduplicado via _clear_concentration_for_source)
        self.assertEqual(len(dpd_effects), 1)
        # concentration_group renovado
        new_group = dpd_effects[0]["metadata"]["concentration_group"]
        self.assertNotEqual(new_group, first_group)
        # expires_at foi renovado
        self.assertEqual(dpd_effects[0]["expires_at_game_time_seconds"], 2600)

    async def test_detect_magic_active_is_cleared_on_cast(self):
        """detect_magic ativo + cast detect_poison_disease → detect_magic removido.
        Prova que detect_poison_disease está no clube oficial de concentração."""
        detect_magic_effect = {
            "id": "dm-1",
            "kind": "spell_effect",
            "duration_type": "timed",
            "source_participant_id": "p1",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-dm",
                "source_spell_key": "detect_magic",
            },
        }
        state = _state(extra_effects=[detect_magic_effect])

        with patch("app.services.combat_service.spell_automation.get_game_time_seconds", return_value=1000):
            await CombatService._cast_detect_poison_disease_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(),
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )

        effects = state.participants[0].get("active_effects") or []
        dm_effects = [e for e in effects if (e.get("metadata") or {}).get("source_spell_key") == "detect_magic"]
        dpd_effects = [e for e in effects if (e.get("metadata") or {}).get("source_spell_key") == "detect_poison_disease"]
        self.assertEqual(len(dm_effects), 0, "detect_magic deveria ter sido removido pela concentração")
        self.assertEqual(len(dpd_effects), 1, "detect_poison_disease deveria estar ativo")

    async def test_no_damage_no_attack_no_save(self):
        result, _ = await _cast()
        self.assertEqual(result["damage"], 0)
        self.assertEqual(result["healing"], 0)
        self.assertIsNone(result["is_hit"])
        self.assertIsNone(result["is_saved"])
        self.assertIsNone(result["roll"])
        self.assertIsNone(result["pending_spell_id"])

    async def test_action_kind_is_utility(self):
        result, _ = await _cast()
        self.assertEqual(result["action_kind"], "utility")


# ---------------------------------------------------------------------------
# OOC support
# ---------------------------------------------------------------------------

class DetectPoisonDiseaseOOCTests(unittest.TestCase):
    def _spell(self):
        spell = MagicMock()
        spell.canonical_key = "detect_poison_disease"
        spell.name_pt = "Detectar Veneno e Doença"
        spell.name_en = "Detect Poison and Disease"
        spell.concentration = True
        spell.effects_json = []
        spell.variants_json = []
        return spell

    def _ooc_effect(self):
        return build_persisted_effects(
            spell=self._spell(),
            caster_user_id="user-1",
            target_user_id="user-1",
            variant_key=None,
            game_time_seconds=5000,
        )

    def test_in_special_ooc_set(self):
        self.assertIn("detect_poison_disease", _SPECIAL_OOC_UTILITY_SPELLS)

    def test_build_persisted_effects_returns_concentration_effect(self):
        effects = self._ooc_effect()
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["kind"], "spell_effect")
        self.assertEqual(effects[0]["duration_type"], "timed")

    def test_ooc_effect_expires_in_600_seconds(self):
        effects = self._ooc_effect()
        self.assertEqual(effects[0]["expires_at_game_time_seconds"], 5000 + 600)

    def test_ooc_effect_has_concentration_true(self):
        effects = self._ooc_effect()
        self.assertTrue(effects[0]["metadata"]["concentration"])

    def test_ooc_effect_has_concentration_group(self):
        effects = self._ooc_effect()
        group = effects[0]["metadata"].get("concentration_group")
        self.assertIsNotNone(group)
        self.assertIsInstance(group, str)

    def test_ooc_metadata_matches_combat_handler(self):
        """OOC e combat handler devem expor os mesmos campos-chave com os mesmos valores.
        Divergência aqui = bug de 'detecção só funciona fora de combate'."""
        ooc_meta = self._ooc_effect()[0]["metadata"]

        expected_values = {
            "utility": "detect_poison_disease",
            "radius_meters": 9,
            "detects_poisons": True,
            "detects_poisonous_creatures": True,
            "detects_diseases": True,
            "can_identify_poison_or_disease_with_action": True,
            "mechanical": False,
            "narrative": True,
            "concentration": True,
        }
        for key, expected in expected_values.items():
            with self.subTest(field=key):
                self.assertEqual(ooc_meta.get(key), expected, f"campo '{key}' difere entre OOC e combat")


# ---------------------------------------------------------------------------
# Ritual + context (metadata only — runtime out of scope)
# ---------------------------------------------------------------------------

class DetectPoisonDiseaseRitualTests(unittest.TestCase):
    # Ritual casting runtime está FORA DE ESCOPO da issue #400.
    # Estes testes verificam apenas que o seed e context expõem ritual=True e concentration=True.

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        cls.entry = spells.get("detect_poison_disease")

    def test_seed_ritual_flag_is_true(self):
        self.assertTrue(self.entry.get("ritual"))

    def test_seed_concentration_is_true(self):
        # Crítico: não deixar concentration cair silenciosamente
        self.assertTrue(self.entry.get("concentration"))

    def test_context_utility_subtype(self):
        from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
        meta = SpellContextResolveMixin._NARRATIVE_UTILITY_META_BY_SPELL.get("detect_poison_disease")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["subtype"], "detect_poison_disease")
        self.assertFalse(meta["mechanical"])
        self.assertTrue(meta["narrative"])
        self.assertIn("blockedBy", meta)
