from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatResolveSpellContextRequest
from app.services.combat import CombatService
from app.services.combat_service.spells.spell_context_resolve import (
    SpellContextResolveMixin,
)
from app.services.out_of_combat_cast import (
    OOC_FACTORY_EFFECT_SPELLS,
    OOC_NARRATIVE_UTILITY_SPELLS,
    OOC_REMOVAL_UTILITY_SPELLS,
    OOC_SPECIAL_INPUT_SPELLS,
    _OOC_PERSISTED_FACTORY_REGISTRY,
    _is_ooc_utility_spell,
)
from app.services.spell_keys import normalize_spell_key
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


ONBOARDING_REQUIRED_SPELLS = {
    "barkskin",
    "blur",
    "protection_from_evil_and_good",
    "jump",
    "spider_climb",
}


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
            }
        ],
    )


def _build_attacker_state() -> SessionState:
    return SessionState(
        id="state-1",
        session_id="session-1",
        player_user_id="user-1",
        state_json={
            "level": 5,
            "abilities": {"wisdom": 16, "charisma": 16},
            "spellcasting": {
                "spells": [
                    {"name": "Barkskin", "canonicalKey": "barkskin", "level": 2, "prepared": True},
                    {"name": "Blur", "canonicalKey": "blur", "level": 2, "prepared": True},
                    {
                        "name": "Protection from Evil and Good",
                        "canonicalKey": "protection_from_evil_and_good",
                        "level": 1,
                        "prepared": True,
                    },
                    {"name": "Jump", "canonicalKey": "jump", "level": 1, "prepared": True},
                    {"name": "Spider Climb", "canonicalKey": "spider_climb", "level": 2, "prepared": True},
                ],
                "slots": {"1": {"used": 0, "max": 4}, "2": {"used": 0, "max": 3}},
            },
        },
    )


def _catalog_spell(**overrides):
    defaults = {
        "canonical_key": "barkskin",
        "name_en": "Barkskin",
        "name_pt": "Pele de Árvore",
        "level": 2,
        "resolution_type": "utility",
        "saving_throw": None,
        "save_success_outcome": None,
        "damage_type": None,
        "damage_dice": None,
        "heal_dice": None,
        "upcast_json": None,
        "cantrip_scaling_json": None,
        "casting_time_type": "action",
        "target_type": "touch",
        "selection_type": "creature",
        "origin_type": "caster",
        "target_anchor": "selected_target",
        "attack_type": "none",
        "range_kind": "touch",
        "effect_timing": "persistent",
        "area_shape": None,
        "range_meters": 1,
        "radius_meters": None,
        "length_meters": None,
        "side_meters": None,
        "duration": "1 hour",
        "duration_seconds": 3600,
        "concentration": True,
        "cover_applies_to_save": None,
        "max_targets": 1,
        "variants_json": None,
        "material_component_text": None,
        "material_component_consumed": False,
        "consumable_material_options_json": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class SpellContextContractCoreTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = _build_state()
        self.attacker_state = _build_attacker_state()

    def _get_stats_side_effect(self, _db, ref_id, kind, _session_id):
        if ref_id == "player-1" and kind == "player":
            return (self.attacker_state, 12, 10, 10, 3, 3)
        raise AssertionError(f"Unexpected _get_stats lookup for {ref_id}/{kind}")

    def _resolve(self, spell_key: str, catalog_spell):
        req = CombatResolveSpellContextRequest(
            actor_participant_id="p1",
            spell_canonical_key=spell_key,
            spell_mode="utility",
            slot_level=1 if spell_key in {"jump", "protection_from_evil_and_good"} else 2,
        )
        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
            return_value=catalog_spell,
        ), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=self._get_stats_side_effect,
        ):
            return CombatService.resolve_spell_context(self.db, "session-1", req, "user-1", False)

    def _assert_core_context_fields(self, payload: dict):
        for field in ("spell_canonical_key", "resolution_type", "selection_type"):
            self.assertIn(field, payload)
            self.assertIsNotNone(payload[field])
        self.assertEqual(payload.get("resolution_type"), "utility")
        self.assertIn(payload.get("selection_type"), {"self", "creature", "single_target"})
        self.assertIn("requires_attack_roll", payload)
        self.assertIn("requires_saving_throw", payload)
        self.assertIsInstance(payload.get("utility"), dict)

    def test_core_spells_context_contract(self):
        spell_configs = {
            "barkskin": _catalog_spell(canonical_key="barkskin", name_en="Barkskin", duration_seconds=3600),
            "blur": _catalog_spell(
                canonical_key="blur",
                name_en="Blur",
                target_type="self",
                selection_type="self",
                range_kind="self",
                range_meters=0,
                duration_seconds=60,
            ),
            "jump": _catalog_spell(
                canonical_key="jump",
                name_en="Jump",
                level=1,
                concentration=False,
                duration_seconds=60,
            ),
            "spider_climb": _catalog_spell(
                canonical_key="spider_climb",
                name_en="Spider Climb",
                duration_seconds=3600,
            ),
            "protection_from_evil_and_good": _catalog_spell(
                canonical_key="protection_from_evil_and_good",
                name_en="Protection from Evil and Good",
                level=1,
                duration_seconds=600,
                material_component_text="holy water or powdered silver and iron, which the spell consumes",
                material_component_consumed=True,
                consumable_material_options_json=[
                    {"key": "holy_water", "nameEn": "Holy water", "namePt": "Água benta", "quantity": 1},
                    {"key": "powdered_silver_and_iron", "nameEn": "Powdered silver and iron", "namePt": "Prata e ferro em pó", "quantity": 1},
                ],
            ),
        }
        for spell_key, spell in spell_configs.items():
            with self.subTest(spell_key=spell_key):
                payload = self._resolve(spell_key, spell)
                self._assert_core_context_fields(payload)
                utility = payload["utility"]
                self.assertEqual(utility.get("subtype"), spell_key)
                if spell_key == "barkskin":
                    self.assertEqual(utility.get("armorClassFloor"), 16)
                elif spell_key == "blur":
                    self.assertTrue(utility.get("attackDisadvantageAgainstTarget"))
                elif spell_key == "jump":
                    self.assertEqual(utility.get("jumpDistanceMultiplier"), 3)
                elif spell_key == "spider_climb":
                    self.assertTrue(utility.get("grantsClimbSpeed"))
                elif spell_key == "protection_from_evil_and_good":
                    self.assertTrue(utility.get("savingThrowAdvantageAgainstCreatureTypes"))
                    self.assertFalse(utility.get("savingThrowAdvantageDeferred"))
                    material = payload.get("materialComponent") or {}
                    self.assertTrue(material.get("consumed"))
                    self.assertTrue(material.get("requiresSelection"))


class SpellOnboardingSubsetChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_path = Path(__file__).resolve().parents[3] / "Base" / "base_spells.seed.json"
        payload = json.loads(seed_path.read_text(encoding="utf-8"))
        cls.seed_spell_keys = {
            normalize_spell_key(entry.get("canonicalKey"))
            for entry in payload.get("spells", [])
            if isinstance(entry, dict)
        }
        cls.seed_spell_keys.discard("")

    def test_onboarding_subset_minimum_integrity(self):
        ooc_categories = (
            OOC_NARRATIVE_UTILITY_SPELLS
            | OOC_FACTORY_EFFECT_SPELLS
            | OOC_REMOVAL_UTILITY_SPELLS
            | OOC_SPECIAL_INPUT_SPELLS
        )
        utility_keys = set(SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META.keys())

        for key in ONBOARDING_REQUIRED_SPELLS:
            with self.subTest(spell_key=key):
                normalized = normalize_spell_key(key)
                self.assertEqual(key, normalized)
                self.assertIn(normalized, self.seed_spell_keys)
                semantics = resolve_spell_targeting_semantics({"canonicalKey": normalized})
                self.assertIsNotNone(semantics)
                self.assertTrue(bool(semantics.to_dict().get("selection_type")))

                if normalized in ooc_categories:
                    self.assertTrue(_is_ooc_utility_spell(normalized))
                if normalized in OOC_FACTORY_EFFECT_SPELLS:
                    self.assertIn(normalized, _OOC_PERSISTED_FACTORY_REGISTRY)
                    self.assertIn(normalized, utility_keys)


if __name__ == "__main__":
    unittest.main()
