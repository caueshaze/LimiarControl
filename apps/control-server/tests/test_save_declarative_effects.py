from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_predicates import (
    _get_save_declarative_context,
    combine_advantage_modes,
)


def _participant_with_save_effects(effects: list[dict]) -> dict:
    return {"id": "p1", "kind": "player", "ref_id": "user-1", "active_effects": effects}


def _save_effect(effect_type: str, abilities: list[str], source_name: str = "Test Spell") -> dict:
    return {
        "id": f"eff-{effect_type}",
        "kind": "spell_effect",
        "metadata": {
            "declarative_effect": {
                "type": effect_type,
                "params": {"abilities": abilities},
            },
            "source_spell_name": source_name,
        },
    }


class TestGetSaveDeclarativeContext(unittest.TestCase):
    def test_no_effects_returns_normal(self):
        mode, adv_strs, dis_strs, details = _get_save_declarative_context(
            _participant_with_save_effects([]), "strength"
        )
        self.assertEqual(mode, "normal")
        self.assertEqual(adv_strs, [])
        self.assertEqual(dis_strs, [])
        self.assertEqual(details, [])

    def test_matching_advantage(self):
        p = _participant_with_save_effects([_save_effect("advantage_on_saves", ["strength"])])
        mode, adv_strs, dis_strs, details = _get_save_declarative_context(p, "strength")
        self.assertEqual(mode, "advantage")
        self.assertEqual(adv_strs, ["Test Spell"])
        self.assertEqual(dis_strs, [])
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["modifier_type"], "advantage")

    def test_matching_disadvantage(self):
        p = _participant_with_save_effects([_save_effect("disadvantage_on_saves", ["dexterity"])])
        mode, adv_strs, dis_strs, details = _get_save_declarative_context(p, "dexterity")
        self.assertEqual(mode, "disadvantage")
        self.assertEqual(adv_strs, [])
        self.assertEqual(dis_strs, ["Test Spell"])
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["modifier_type"], "disadvantage")

    def test_unrelated_ability_ignored(self):
        p = _participant_with_save_effects([_save_effect("advantage_on_saves", ["strength"])])
        mode, adv_strs, dis_strs, details = _get_save_declarative_context(p, "dexterity")
        self.assertEqual(mode, "normal")
        self.assertEqual(adv_strs, [])
        self.assertEqual(details, [])

    def test_advantage_and_disadvantage_cancel(self):
        p = _participant_with_save_effects(
            [
                _save_effect("advantage_on_saves", ["strength"], "Buff"),
                _save_effect("disadvantage_on_saves", ["strength"], "Debuff"),
            ]
        )
        mode, adv_strs, dis_strs, details = _get_save_declarative_context(p, "strength")
        self.assertEqual(mode, "normal")
        self.assertEqual(len(adv_strs), 1)
        self.assertEqual(len(dis_strs), 1)
        self.assertEqual(len(details), 2)

    def test_deduplication_by_group_key(self):
        p = _participant_with_save_effects(
            [
                _save_effect("advantage_on_saves", ["strength"], "Same"),
                _save_effect("advantage_on_saves", ["strength"], "Same"),
            ]
        )
        mode, adv_strs, dis_strs, details = _get_save_declarative_context(p, "strength")
        self.assertEqual(mode, "advantage")
        self.assertEqual(len(adv_strs), 1)
        self.assertEqual(len(details), 1)

    def test_empty_abilities_list_ignored(self):
        p = _participant_with_save_effects(
            [
                {
                    "id": "eff-1",
                    "kind": "spell_effect",
                    "metadata": {
                        "declarative_effect": {
                            "type": "advantage_on_saves",
                            "params": {"abilities": []},
                        },
                    },
                }
            ]
        )
        mode, adv_strs, dis_strs, details = _get_save_declarative_context(p, "strength")
        self.assertEqual(mode, "normal")
        self.assertEqual(details, [])

    def test_non_spell_effect_ignored(self):
        p = _participant_with_save_effects(
            [
                {
                    "id": "eff-1",
                    "kind": "condition",
                    "condition_type": "blinded",
                    "metadata": {
                        "declarative_effect": {
                            "type": "advantage_on_saves",
                            "params": {"abilities": ["strength"]},
                        },
                    },
                }
            ]
        )
        mode, adv_strs, dis_strs, details = _get_save_declarative_context(p, "strength")
        self.assertEqual(mode, "normal")
        self.assertEqual(details, [])


class TestResolveSaveAdvantageModeForActor(unittest.TestCase):
    @patch("app.services.combat.CombatService.get_state")
    def test_no_combat_state_returns_normal(self, mock_get_state):
        mock_get_state.return_value = None
        result = CombatService._resolve_save_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
            manual_mode="normal",
        )
        self.assertEqual(result, "normal")

    @patch("app.services.combat.CombatService.get_state")
    def test_ended_combat_returns_normal(self, mock_get_state):
        mock_get_state.return_value = CombatState(
            id="cs-1",
            session_id="session-1",
            phase=CombatPhase.ended,
            round=1,
            current_turn_index=0,
            participants=[],
        )
        result = CombatService._resolve_save_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
            manual_mode="normal",
        )
        self.assertEqual(result, "normal")

    @patch("app.services.combat.CombatService.get_state")
    def test_valid_participant_with_declared_advantage(self, mock_get_state):
        state = CombatState(
            id="cs-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "kind": "player",
                    "ref_id": "user-1",
                    "active_effects": [
                        _save_effect("advantage_on_saves", ["strength"], "Aumentar"),
                    ],
                }
            ],
        )
        mock_get_state.return_value = state
        result = CombatService._resolve_save_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
            manual_mode="normal",
        )
        self.assertEqual(result, "advantage")

    @patch("app.services.combat.CombatService.get_state")
    def test_kind_mismatch_returns_normal(self, mock_get_state):
        state = CombatState(
            id="cs-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "kind": "session_entity",
                    "ref_id": "user-1",
                    "active_effects": [],
                }
            ],
        )
        mock_get_state.return_value = state
        result = CombatService._resolve_save_advantage_mode_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
            manual_mode="normal",
        )
        self.assertEqual(result, "normal")


class TestExplainSaveModifierSourcesForActor(unittest.TestCase):
    @patch("app.services.combat.CombatService.get_state")
    def test_no_combat_state_returns_empty(self, mock_get_state):
        mock_get_state.return_value = None
        result = CombatService._explain_save_modifier_sources_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
        )
        self.assertEqual(result, [])

    @patch("app.services.combat.CombatService.get_state")
    def test_valid_participant_returns_sources(self, mock_get_state):
        state = CombatState(
            id="cs-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "kind": "player",
                    "ref_id": "user-1",
                    "active_effects": [
                        _save_effect("advantage_on_saves", ["strength"], "Aumentar"),
                    ],
                }
            ],
        )
        mock_get_state.return_value = state
        result = CombatService._explain_save_modifier_sources_for_actor(
            MagicMock(),
            "session-1",
            actor_kind="player",
            actor_ref_id="user-1",
            ability="strength",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_label"], "Aumentar")
        self.assertEqual(result[0]["modifier_type"], "advantage")
        self.assertTrue(result[0]["applied"])


if __name__ == "__main__":
    unittest.main()
