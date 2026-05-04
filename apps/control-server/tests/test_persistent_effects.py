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
    clear_persisted_concentration_effects,
    derive_active_concentration,
    enforce_single_persisted_concentration_group,
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

    def test_persists_concentration_effect(self):
        effect = _manual_spell_effect("eff-1", concentration=True)
        state = _make_state_with_participants([effect])
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        persisted = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["id"], "eff-1")
        self.assertTrue(persisted[0]["metadata"]["concentration"])

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


class TestPersistSurvivingConcentrationEffects(unittest.TestCase):
    def test_persists_concentration_and_non_concentration_together(self):
        conc = _manual_spell_effect("eff-conc", concentration=True)
        non_conc = _manual_spell_effect("eff-non")
        state = _make_state_with_participants([conc, non_conc])
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        persisted = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(persisted), 2)
        ids = {e["id"] for e in persisted}
        self.assertEqual(ids, {"eff-conc", "eff-non"})


class TestDeriveActiveConcentration(unittest.TestCase):
    def test_returns_none_when_no_effects(self):
        self.assertIsNone(derive_active_concentration({}))
        self.assertIsNone(derive_active_concentration(None))

    def test_returns_none_when_only_non_concentration_effects(self):
        effect = _manual_spell_effect("eff-1", concentration=False)
        result = derive_active_concentration({"active_spell_effects": [effect]})
        self.assertIsNone(result)

    def test_returns_concentration_info_for_single_effect(self):
        effect = _manual_spell_effect("eff-1", concentration=True)
        result = derive_active_concentration({"active_spell_effects": [effect]})
        self.assertIsNotNone(result)
        self.assertEqual(result["spellName"], "Owl's Wisdom")
        self.assertEqual(result["effectIds"], ["eff-1"])
        self.assertEqual(result["concentrationGroup"], "group-1")

    def test_groups_effects_by_concentration_group(self):
        eff1 = {
            "id": "eff-a",
            "kind": "spell_effect",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-bless",
                "source_spell_key": "bless",
                "source_spell_name": "Bless",
            },
        }
        eff2 = {
            "id": "eff-b",
            "kind": "spell_effect",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-bless",
                "source_spell_key": "bless",
                "source_spell_name": "Bless",
            },
        }
        non_conc = _manual_spell_effect("eff-other")
        result = derive_active_concentration({
            "active_spell_effects": [eff1, eff2, non_conc],
        })
        self.assertIsNotNone(result)
        self.assertEqual(result["concentrationGroup"], "grp-bless")
        self.assertIn("eff-a", result["effectIds"])
        self.assertIn("eff-b", result["effectIds"])
        self.assertEqual(len(result["effectIds"]), 2)

    def test_returns_first_group_when_multiple_groups(self):
        eff1 = {
            "id": "eff-1",
            "kind": "spell_effect",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-first",
                "source_spell_name": "Spell A",
            },
        }
        eff2 = {
            "id": "eff-2",
            "kind": "spell_effect",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-second",
                "source_spell_name": "Spell B",
            },
        }
        result = derive_active_concentration({
            "active_spell_effects": [eff2, eff1],
        })
        self.assertIsNotNone(result)
        self.assertEqual(result["concentrationGroup"], "grp-second")
        self.assertEqual(result["effectIds"], ["eff-2"])

    def test_handles_effect_without_concentration_group(self):
        eff = {
            "id": "eff-solo",
            "kind": "spell_effect",
            "metadata": {
                "concentration": True,
                "source_spell_name": "Solo Spell",
            },
        }
        result = derive_active_concentration({"active_spell_effects": [eff]})
        self.assertIsNotNone(result)
        self.assertIsNone(result["concentrationGroup"])
        self.assertEqual(result["effectIds"], ["eff-solo"])


class TestClearPersistedConcentrationEffects(unittest.TestCase):
    def test_removes_all_concentration_effects_by_default(self):
        conc = _manual_spell_effect("eff-conc", concentration=True)
        non_conc = _manual_spell_effect("eff-other")
        state_json = {"active_spell_effects": [conc, non_conc]}

        result = clear_persisted_concentration_effects(state_json)

        persisted = result["active_spell_effects"]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["id"], "eff-other")

    def test_removes_only_targeted_group_when_concentration_group_given(self):
        eff_a = {
            "id": "eff-a",
            "kind": "spell_effect",
            "metadata": {"concentration": True, "concentration_group": "grp-a"},
        }
        eff_b = {
            "id": "eff-b",
            "kind": "spell_effect",
            "metadata": {"concentration": True, "concentration_group": "grp-b"},
        }
        state_json = {"active_spell_effects": [eff_a, eff_b]}

        result = clear_persisted_concentration_effects(state_json, concentration_group="grp-a")

        persisted = result["active_spell_effects"]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["id"], "eff-b")

    def test_preserves_non_concentration_effects(self):
        conc = _manual_spell_effect("eff-conc", concentration=True)
        non_conc = _manual_spell_effect("eff-other")
        state_json = {"active_spell_effects": [conc, non_conc]}

        result = clear_persisted_concentration_effects(state_json)

        self.assertEqual(len(result["active_spell_effects"]), 1)
        self.assertEqual(result["active_spell_effects"][0]["id"], "eff-other")

    def test_removes_all_when_only_concentration_effects(self):
        conc = _manual_spell_effect("eff-conc", concentration=True)
        state_json = {"active_spell_effects": [conc]}

        result = clear_persisted_concentration_effects(state_json)

        self.assertNotIn("active_spell_effects", result)

    def test_safe_when_no_effects(self):
        result = clear_persisted_concentration_effects({})
        self.assertNotIn("active_spell_effects", result)

    def test_safe_when_no_concentration_effects(self):
        non_conc = _manual_spell_effect("eff-1")
        state_json = {"active_spell_effects": [non_conc]}

        result = clear_persisted_concentration_effects(state_json)

        self.assertEqual(len(result["active_spell_effects"]), 1)


class TestToStateReadActiveConcentration(unittest.TestCase):
    def test_active_concentration_derived_in_response(self):
        from app.api.routes.sessions.state_common import to_state_read

        conc = _manual_spell_effect("eff-conc", concentration=True)
        mock = MagicMock(spec=SessionState)
        mock.id = "ss-1"
        mock.session_id = "session-1"
        mock.player_user_id = "player-1"
        mock.state_json = {"active_spell_effects": [conc]}
        mock.created_at = "2026-01-01T00:00:00+00:00"
        mock.updated_at = None

        result = to_state_read(mock)

        self.assertIsNotNone(result.activeConcentration)
        self.assertEqual(result.activeConcentration["spellName"], "Owl's Wisdom")
        self.assertIn("eff-conc", result.activeConcentration["effectIds"])

    def test_active_concentration_none_when_no_concentration(self):
        from app.api.routes.sessions.state_common import to_state_read

        non_conc = _manual_spell_effect("eff-1")
        mock = MagicMock(spec=SessionState)
        mock.id = "ss-1"
        mock.session_id = "session-1"
        mock.player_user_id = "player-1"
        mock.state_json = {"active_spell_effects": [non_conc]}
        mock.created_at = "2026-01-01T00:00:00+00:00"
        mock.updated_at = None

        result = to_state_read(mock)

        self.assertIsNone(result.activeConcentration)


class TestEnforceSinglePersistedConcentrationGroup(unittest.TestCase):
    def test_no_concentration_effects_unchanged(self):
        effects = [_manual_spell_effect("eff-1"), _temp_ac_bonus_effect("eff-ac")]
        result = enforce_single_persisted_concentration_group(effects)
        self.assertEqual(result, effects)

    def test_single_concentration_group_unchanged(self):
        effects = [
            _manual_spell_effect("eff-a", concentration=True),
            _manual_spell_effect("eff-b", concentration=True),
        ]
        result = enforce_single_persisted_concentration_group(effects)
        self.assertEqual(len(result), 2)
        self.assertEqual({e["id"] for e in result}, {"eff-a", "eff-b"})

    def test_two_groups_keeps_newest_by_created_at(self):
        older = {
            "id": "eff-old",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-01T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-old",
                "source_spell_name": "Old Spell",
            },
        }
        newer = {
            "id": "eff-new",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-02T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-new",
                "source_spell_name": "New Spell",
            },
        }
        result = enforce_single_persisted_concentration_group([older, newer])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "eff-new")

    def test_multiple_effects_in_winning_group_all_kept(self):
        older = {
            "id": "eff-old",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-01T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-old",
                "source_spell_name": "Old Spell",
            },
        }
        new_a = {
            "id": "eff-new-a",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-02T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-new",
                "source_spell_name": "New Spell",
            },
        }
        new_b = {
            "id": "eff-new-b",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-02T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-new",
                "source_spell_name": "New Spell",
            },
        }
        result = enforce_single_persisted_concentration_group([older, new_a, new_b])
        self.assertEqual(len(result), 2)
        ids = {e["id"] for e in result}
        self.assertEqual(ids, {"eff-new-a", "eff-new-b"})

    def test_non_concentration_effects_survive(self):
        non_conc = _manual_spell_effect("eff-non")
        conc = _manual_spell_effect("eff-conc", concentration=True)
        result = enforce_single_persisted_concentration_group([non_conc, conc])
        self.assertEqual(len(result), 2)
        ids = {e["id"] for e in result}
        self.assertEqual(ids, {"eff-non", "eff-conc"})

    def test_invalid_created_at_falls_back_to_last_group(self):
        first = {
            "id": "eff-first",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-first",
            },
        }
        second = {
            "id": "eff-second",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-second",
            },
        }
        result = enforce_single_persisted_concentration_group([first, second])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "eff-second")

    def test_preserves_original_ordering(self):
        non1 = _manual_spell_effect("eff-non-1")
        non2 = _temp_ac_bonus_effect("eff-ac")
        conc = {
            "id": "eff-conc",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-01T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-1",
            },
        }
        result = enforce_single_persisted_concentration_group([non1, conc, non2])
        self.assertEqual([e["id"] for e in result], ["eff-non-1", "eff-ac", "eff-conc"])

    def test_solo_concentration_without_group_key(self):
        solo = {
            "id": "eff-solo",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-01T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "source_spell_name": "Solo Spell",
            },
        }
        result = enforce_single_persisted_concentration_group([solo])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "eff-solo")


class TestPersistSurvivingConcentrationNormalization(unittest.TestCase):
    def test_persist_surviving_keeps_only_newest_concentration_group(self):
        older = {
            "id": "eff-old",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-01T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-old",
                "source_spell_name": "Old Spell",
            },
        }
        newer = {
            "id": "eff-new",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-02T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-new",
                "source_spell_name": "New Spell",
            },
        }
        state = _make_state_with_participants([older, newer])
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        persisted = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["id"], "eff-new")

    def test_persist_surviving_preserves_non_concentration(self):
        non_conc = _manual_spell_effect("eff-non")
        conc = {
            "id": "eff-conc",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-02T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-1",
                "source_spell_name": "Conc Spell",
            },
        }
        state = _make_state_with_participants([non_conc, conc])
        db = MagicMock()
        session_state = _make_session_state({})
        db.exec.return_value.first.return_value = session_state

        persist_surviving_spell_effects(db, state)

        persisted = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(persisted), 2)
        ids = {e["id"] for e in persisted}
        self.assertEqual(ids, {"eff-non", "eff-conc"})


class TestRestorePersistedConcentrationNormalization(unittest.TestCase):
    def test_restore_normalizes_multiple_concentration_groups(self):
        older = {
            "id": "eff-old",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-01T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-old",
                "source_spell_name": "Old Spell",
            },
        }
        newer = {
            "id": "eff-new",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-02T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-new",
                "source_spell_name": "New Spell",
            },
        }
        participant = {"kind": "player", "ref_id": "player-1", "active_effects": []}
        db = MagicMock()
        session_state = _make_session_state({"active_spell_effects": [older, newer]})
        db.exec.return_value.first.return_value = session_state

        restore_persisted_effects(db, "session-1", participant)

        self.assertEqual(len(participant["active_effects"]), 1)
        self.assertEqual(participant["active_effects"][0]["id"], "eff-new")

    def test_restore_syncs_back_to_state_json(self):
        older = {
            "id": "eff-old",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-01T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-old",
                "source_spell_name": "Old Spell",
            },
        }
        newer = {
            "id": "eff-new",
            "kind": "spell_effect",
            "duration_type": "manual",
            "created_at": "2026-01-02T00:00:00+00:00",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-new",
                "source_spell_name": "New Spell",
            },
        }
        participant = {"kind": "player", "ref_id": "player-1", "active_effects": []}
        db = MagicMock()
        session_state = _make_session_state({"active_spell_effects": [older, newer]})
        db.exec.return_value.first.return_value = session_state

        restore_persisted_effects(db, "session-1", participant)

        # state_json should be normalized too
        persisted = session_state.state_json["active_spell_effects"]
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["id"], "eff-new")


if __name__ == "__main__":
    unittest.main()
