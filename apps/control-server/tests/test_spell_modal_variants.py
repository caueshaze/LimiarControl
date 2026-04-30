from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat import CombatCastSpellRequest
from app.services.combat import CombatService, CombatServiceError


def _build_state() -> CombatState:
    return CombatState(
        id="combat-variants",
        session_id="session-variants",
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
            },
            {
                "id": "e1",
                "ref_id": "enemy-1",
                "kind": "session_entity",
                "display_name": "Goblin A",
                "initiative": 8,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
            },
            {
                "id": "e2",
                "ref_id": "enemy-2",
                "kind": "session_entity",
                "display_name": "Goblin B",
                "initiative": 7,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
            },
        ],
    )


def _spell_context() -> dict:
    return {
        "spell_name": "Enhance Ability",
        "spell_canonical_key": "enhance_ability",
        "max_targets": 2,
        "selection_type": "creature",
        "variant_definitions": [
            {
                "key": "bears_endurance",
                "labelPt": "Resistência do Urso",
                "effects": [
                    {
                        "type": "advantage_on_checks",
                        "target": "selected_target",
                        "params": {"ability": "constitution"},
                        "stacking": "replace",
                    }
                ],
                "manualNotes": [
                    {
                        "key": "grant_temp_hp",
                        "label": "PV temporários",
                        "description": "Conceda 2d6 PV temporários manualmente.",
                    }
                ],
            },
            {
                "key": "foxs_cunning",
                "labelPt": "Esperteza da Raposa",
                "effects": [
                    {
                        "type": "advantage_on_checks",
                        "target": "selected_target",
                        "params": {"ability": "intelligence"},
                        "stacking": "replace",
                    }
                ],
            },
        ],
        "effects": [],
        "on_end_effects": [],
    }


class SpellModalVariantTests(unittest.TestCase):
    def setUp(self):
        self.state = _build_state()

    def test_single_target_modal_spell_requires_variant_key(self):
        with self.assertRaises(CombatServiceError):
            CombatService._validate_modal_target_variant_assignments(
                req=CombatCastSpellRequest(
                    actor_participant_id="p1",
                    target_ref_id="enemy-1",
                    spell_canonical_key="enhance_ability",
                ),
                spell_context=_spell_context(),
                state=self.state,
            )

    def test_multi_target_modal_spell_rejects_duplicate_target_assignments(self):
        with self.assertRaises(CombatServiceError):
            CombatService._validate_modal_target_variant_assignments(
                req=CombatCastSpellRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="enhance_ability",
                    target_variant_assignments=[
                        {"target_participant_id": "e1", "variant_key": "bears_endurance"},
                        {"target_participant_id": "e1", "variant_key": "foxs_cunning"},
                    ],
                ),
                spell_context=_spell_context(),
                state=self.state,
            )

    def test_multi_target_modal_spell_accepts_per_target_assignments(self):
        assignments = CombatService._validate_modal_target_variant_assignments(
            req=CombatCastSpellRequest(
                actor_participant_id="p1",
                spell_canonical_key="enhance_ability",
                target_variant_assignments=[
                    {"target_participant_id": "e1", "variant_key": "bears_endurance"},
                    {"target_participant_id": "e2", "variant_key": "foxs_cunning"},
                ],
            ),
            spell_context=_spell_context(),
            state=self.state,
        )

        self.assertEqual(len(assignments), 2)
        self.assertEqual(assignments[0]["variant_key"], "bears_endurance")
        self.assertEqual(assignments[1]["participant"]["ref_id"], "enemy-2")

    def test_merge_spell_context_with_variant_only_adds_selected_variant_effects(self):
        variant = CombatService._get_spell_variants_map(_spell_context())["bears_endurance"]
        participant = self.state.participants[1]

        merged = CombatService._merge_spell_context_with_variant(
            spell_context=_spell_context(),
            variant=variant,
            participant=participant,
            target_variant_assignments=[
                {"target_participant_id": "e1", "variant_key": "bears_endurance"}
            ],
        )

        self.assertEqual(len(merged["effects"]), 1)
        self.assertEqual(merged["effects"][0]["params"]["ability"], "constitution")
        self.assertEqual(merged["manual_notes_by_target"][0]["variant_key"], "bears_endurance")
