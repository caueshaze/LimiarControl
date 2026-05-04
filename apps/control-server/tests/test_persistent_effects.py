"""Tests for persistent spell effects across combat boundaries.

Covers:
- persist_surviving_spell_effects (end_combat → state_json)
- restore_persisted_effects (combat start ← state_json)
- sync_effect_removal_to_state_json (remove_effect → state_json)
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat_service.persistent_effects import (
    persist_surviving_spell_effects,
    restore_persisted_effects,
    sync_effect_removal_to_state_json,
)


def _manual_spell_effect(effect_id: str = "eff-1", concentration: bool = False) -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "source_participant_id": "caster-1",
        "duration_type": "manual",
        "created_at": "2026-01-01T00:00:00+00:00",
        "display_label": "Owl's Wisdom",
        "metadata": {
            "source_spell_name": "Owl's Wisdom",
            "concentration": concentration,
            "concentration_group": "group-1" if concentration else None,
            "declarative_effect": {
                "type": "passive_skill_bonus",
                "params": {"skill": "perception", "bonus": 5},
            },
        },
    }


def _rounds_spell_effect(effect_id: str = "eff-rounds") -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "source_participant_id": "caster-1",
        "duration_type": "rounds",
        "remaining_rounds": 5,
        "created_at": "2026-01-01T00:00:00+00:00",
        "metadata": {"source_spell_name": "Friends"},
    }


def _condition_effect(effect_id: str = "eff-cond") -> dict:
    return {
        "id": effect_id,
        "kind": "condition",
        "condition_type": "frightened",
        "duration_type": "manual",
        "created_at": "2026-01-01T00:00:00+00:00",
        "metadata": {},
    }


def _temp_ac_bonus_effect(effect_id: str = "eff-ac") -> dict:
    return {
        "id": effect_id,
        "kind": "temp_ac_bonus",
        "numeric_value": 2,
        "duration_type": "manual",
        "created_at": "2026-01-01T00:00:00+00:00",
        "metadata": {},
    }


def _make_state_with_participants(effects: list[dict] | None = None) -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=3,
        current_turn_index=0,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Hero",
                "status": "active",
                "team": "players",
                "active_effects": list(effects or []),
            },
            {
                "id": "e1",
                "ref_id": "enemy-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "status": "active",
                "team": "enemies",
                "active_effects": [],
            },
        ],
    )


def _make_session_state(state_json: dict | None = None) -> SessionState:
    mock = MagicMock(spec=SessionState)
    mock.state_json = state_json or {}
    mock._sa_instance_state = MagicMock()
    return mock


class TestPersistSurvivingSpellEffects(unittest.TestCase):
    def test_persists_manual_spell_effect(self):
        effect = _manual_spell_effect("eff-1")
        state = _make_state_with_participants([effect])
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        persisted = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["id"], "eff-1")

    def test_persists_manual_temp_ac_bonus(self):
        effect = _temp_ac_bonus_effect("eff-ac")
        state = _make_state_with_participants([effect])
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        persisted = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["kind"], "temp_ac_bonus")

    def test_discards_rounds_based_effect(self):
        effects = [_manual_spell_effect("eff-1"), _rounds_spell_effect("eff-rounds")]
        state = _make_state_with_participants(effects)
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        persisted = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["id"], "eff-1")

    def test_discards_concentration_effect(self):
        effect = _manual_spell_effect("eff-1", concentration=True)
        state = _make_state_with_participants([effect])
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        self.assertNotIn("active_spell_effects", session_state.state_json)

    def test_discards_condition_effect(self):
        effect = _condition_effect("eff-cond")
        state = _make_state_with_participants([effect])
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        self.assertNotIn("active_spell_effects", session_state.state_json)

    def test_skips_entity_participants(self):
        state = _make_state_with_participants()
        state.participants[1]["active_effects"] = [_manual_spell_effect("eff-1")]
        db = MagicMock()

        persist_surviving_spell_effects(db, state)

        db.exec.assert_not_called()

    def test_no_persist_when_no_surviving(self):
        state = _make_state_with_participants([_rounds_spell_effect()])
        db = MagicMock()

        persist_surviving_spell_effects(db, state)

        db.exec.assert_not_called()


class TestRestorePersistedEffects(unittest.TestCase):
    def test_restores_persisted_effects(self):
        effect = _manual_spell_effect("eff-1")
        participant = {"kind": "player", "ref_id": "player-1", "active_effects": []}
        db = MagicMock()
        session_state = _make_session_state({"active_spell_effects": [effect]})
        db.exec.return_value.first.return_value = session_state

        restore_persisted_effects(db, "session-1", participant)

        self.assertEqual(len(participant["active_effects"]), 1)
        self.assertEqual(participant["active_effects"][0]["id"], "eff-1")

    def test_does_not_duplicate_existing(self):
        effect = _manual_spell_effect("eff-1")
        participant = {"kind": "player", "ref_id": "player-1", "active_effects": [effect]}
        db = MagicMock()
        session_state = _make_session_state({"active_spell_effects": [effect]})
        db.exec.return_value.first.return_value = session_state

        restore_persisted_effects(db, "session-1", participant)

        self.assertEqual(len(participant["active_effects"]), 1)

    def test_skips_non_player(self):
        participant = {"kind": "session_entity", "ref_id": "enemy-1", "active_effects": []}
        db = MagicMock()

        restore_persisted_effects(db, "session-1", participant)

        db.exec.assert_not_called()
        self.assertEqual(participant["active_effects"], [])

    def test_handles_empty_persisted(self):
        participant = {"kind": "player", "ref_id": "player-1", "active_effects": []}
        db = MagicMock()
        session_state = _make_session_state({"active_spell_effects": []})
        db.exec.return_value.first.return_value = session_state

        restore_persisted_effects(db, "session-1", participant)

        self.assertEqual(participant["active_effects"], [])


class TestSyncEffectRemovalToStateJson(unittest.TestCase):
    def test_removes_effect_from_state_json(self):
        effect = _manual_spell_effect("eff-1")
        participant = {"kind": "player", "ref_id": "player-1"}
        db = MagicMock()
        session_state = _make_session_state({"active_spell_effects": [effect]})
        db.exec.return_value.first.return_value = session_state

        sync_effect_removal_to_state_json(db, "session-1", participant, "eff-1")

        self.assertNotIn("active_spell_effects", session_state.state_json)

    def test_removes_only_matching_effect(self):
        eff1 = _manual_spell_effect("eff-1")
        eff2 = _manual_spell_effect("eff-2")
        participant = {"kind": "player", "ref_id": "player-1"}
        db = MagicMock()
        session_state = _make_session_state({"active_spell_effects": [eff1, eff2]})
        db.exec.return_value.first.return_value = session_state

        sync_effect_removal_to_state_json(db, "session-1", participant, "eff-1")

        remaining = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], "eff-2")

    def test_noop_when_effect_not_persisted(self):
        effect = _manual_spell_effect("eff-1")
        participant = {"kind": "player", "ref_id": "player-1"}
        db = MagicMock()
        session_state = _make_session_state({"active_spell_effects": [effect]})
        db.exec.return_value.first.return_value = session_state

        sync_effect_removal_to_state_json(db, "session-1", participant, "eff-other")

        self.assertEqual(len(session_state.state_json["active_spell_effects"]), 1)

    def test_skips_non_player(self):
        participant = {"kind": "session_entity", "ref_id": "enemy-1"}
        db = MagicMock()

        sync_effect_removal_to_state_json(db, "session-1", participant, "eff-1")

        db.exec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
