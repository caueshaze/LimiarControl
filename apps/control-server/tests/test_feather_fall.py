from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat import CombatCastSpellRequest
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.condition_effects_predicates import (
    has_feather_fall_protection,
)
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.out_of_combat_cast import _SPECIAL_OOC_UTILITY_SPELLS
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


class FeatherFallSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next(
            (s for s in data.get("spells", []) if s.get("canonicalKey") == "feather_fall"),
            None,
        )

    def test_contract(self):
        self.assertIsNotNone(self.entry)
        self.assertEqual(self.entry["level"], 1)
        self.assertEqual(self.entry["school"], "transmutation")
        self.assertIn("Bard", self.entry["classesJson"])
        self.assertIn("Sorcerer", self.entry["classesJson"])
        self.assertIn("Wizard", self.entry["classesJson"])
        self.assertEqual(self.entry["castingTimeType"], "reaction")
        self.assertEqual(self.entry["rangeMeters"], 18)
        self.assertEqual(self.entry["durationSeconds"], 60)
        self.assertFalse(self.entry["concentration"])
        self.assertEqual(self.entry["resolutionType"], "utility")
        self.assertEqual(self.entry["selectionType"], "multi_creature")
        self.assertEqual(self.entry["maxTargets"], 5)
        self.assertNotIn("outOfCombatCastable", self.entry)


class FeatherFallTargetingAndRegistryTests(unittest.TestCase):
    def test_targeting_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "feather_fall"})
        self.assertEqual(sem.selection_type, "multi_creature")
        self.assertEqual(sem.target_anchor, "selected_targets")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.range_kind, "distance")
        self.assertEqual(sem.effect_timing, "persistent")

    def test_registry_entry(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("feather_fall")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.default_mode, "utility")
        self.assertFalse(spec.requires_effect_payload)
        self.assertEqual(spec.handler_name, "_cast_feather_fall_automation")


class FeatherFallContractTests(unittest.TestCase):
    def test_request_accepts_camel_case_trigger_fields(self):
        req = CombatCastSpellRequest.model_validate(
            {
                "spell_canonical_key": "feather_fall",
                "target_ref_ids": ["a"],
                "reactionTrigger": "fall",
                "fallingTargetRefIds": ["a"],
            }
        )
        self.assertEqual(req.reaction_trigger, "fall")
        self.assertEqual(req.falling_target_ref_ids, ["a"])

    def test_spell_id_and_canonical_key_mismatch_rejected(self):
        with self.assertRaises(CombatServiceError) as ctx:
            CombatService._resolve_spell_source_context(
                MagicMock(),
                "s1",
                {"actor_user_id": "u1", "ref_id": "player-1"},
                SimpleNamespace(
                    inventory_item_id=None,
                    spell_canonical_key="shillelagh",
                    spell_id="cure_wounds",
                ),
                {},
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_feather_fall_requires_explicit_fall_event_subset(self):
        targets = [{"ref_id": "player-a"}, {"ref_id": "npc-b"}]
        with self.assertRaises(CombatServiceError):
            CombatService._validate_feather_fall_trigger_context(
                req=SimpleNamespace(
                    spell_canonical_key="feather_fall",
                    reaction_trigger="fall",
                    falling_target_ref_ids=["player-a"],
                ),
                spell_context={"spell_canonical_key": "feather_fall"},
                targets=targets,
            )


def _make_state_with_feather() -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "entity-e1",
                "ref_id": "entity-ref-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "initiative": 8,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "active_effects": [
                    {
                        "id": "ff-1",
                        "kind": "spell_effect",
                        "metadata": {
                            "source_spell_key": "feather_fall",
                            "prevents_fall_damage": True,
                            "prevents_prone_from_fall": True,
                            "ends_on_landing": True,
                        },
                    }
                ],
                "actor_user_id": None,
            }
        ],
    )


class FeatherFallFallProtectionTests(unittest.IsolatedAsyncioTestCase):
    def test_helper_detects_protection(self):
        participant = _make_state_with_feather().participants[0]
        self.assertTrue(has_feather_fall_protection(participant))

    @patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock)
    @patch.object(CombatService, "_emit_state", new_callable=AsyncMock)
    @patch.object(CombatService, "get_state")
    async def test_resolve_fall_prevented_and_effect_removed(
        self,
        mock_get_state,
        mock_emit_state,
        mock_emit_log,
    ):
        state = _make_state_with_feather()
        mock_get_state.return_value = state
        db = MagicMock()

        result = await CombatService.resolve_fall(
            db,
            "session-1",
            "entity-e1",
            12.0,
            "gm-user",
            is_gm=True,
        )

        resolution = result["resolution"]
        self.assertTrue(resolution["causes_damage"])
        self.assertFalse(resolution["applied_damage"])
        self.assertTrue(resolution["prevented"])
        self.assertEqual(resolution["damage_total"], 0)
        self.assertEqual(
            len(
                [
                    e
                    for e in state.participants[0].get("active_effects", [])
                    if (e.get("metadata") or {}).get("source_spell_key")
                    == "feather_fall"
                ]
            ),
            0,
        )


class FeatherFallOocGuardrailTests(unittest.TestCase):
    def test_not_ooc_allowlisted(self):
        self.assertNotIn("feather_fall", _SPECIAL_OOC_UTILITY_SPELLS)


if __name__ == "__main__":
    unittest.main()
