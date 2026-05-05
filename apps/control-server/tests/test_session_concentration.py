"""Tests for the concentration clear HTTP route.

Covers route-level behavior of POST /sessions/{id}/state/me/concentration/clear.
"""

import unittest
from unittest.mock import MagicMock, patch

from app.api.routes.sessions.state import clear_my_concentration, remove_my_persisted_effect
from app.schemas.session_state import ClearConcentrationRequest, SessionStateRead


def _make_user(user_id: str = "user-1"):
    user = MagicMock()
    user.id = user_id
    return user


def _make_db_session(state_json: dict | None = None):
    db = MagicMock()
    state = MagicMock()
    state.state_json = state_json or {}
    state.id = "ss-1"
    state.session_id = "session-1"
    state.player_user_id = "user-1"
    state.created_at = "2026-01-01T00:00:00+00:00"
    state.updated_at = None
    db.exec.return_value.first.return_value = state
    return db, state


def _concentration_effect(effect_id: str = "eff-conc", group: str = "grp-1") -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "duration_type": "manual",
        "metadata": {
            "concentration": True,
            "concentration_group": group,
            "source_spell_name": "Bless",
        },
    }


def _non_concentration_effect(effect_id: str = "eff-other") -> dict:
    return {
        "id": effect_id,
        "kind": "spell_effect",
        "duration_type": "manual",
        "metadata": {
            "source_spell_name": "Owl's Wisdom",
            "declarative_effect": {
                "type": "passive_skill_bonus",
                "params": {"skill": "perception", "bonus": 5},
            },
        },
    }


class TestClearMyConcentration(unittest.IsolatedAsyncioTestCase):
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_clears_concentration_and_preserves_non_concentration(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session(
            {"active_spell_effects": [_concentration_effect(), _non_concentration_effect()]}
        )
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[_non_concentration_effect()],
            activeConcentration=None,
        )

        result = await clear_my_concentration(
            session_id="session-1",
            payload=ClearConcentrationRequest(),
            user=_make_user(),
            session=db,
        )

        self.assertIsNone(result.activeConcentration)
        self.assertEqual(len(result.activeSpellEffects), 1)
        self.assertEqual(result.activeSpellEffects[0]["id"], "eff-other")
        mock_publish.assert_awaited_once()

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_clear_with_empty_body_works_identically_to_no_body(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session({"active_spell_effects": [_concentration_effect()]})
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=None,
            activeConcentration=None,
        )

        result = await clear_my_concentration(
            session_id="session-1",
            payload=ClearConcentrationRequest(),
            user=_make_user(),
            session=db,
        )

        self.assertIsNone(result.activeConcentration)
        mock_publish.assert_awaited_once()

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_clear_targeted_group_removes_only_matching_group(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        eff_a = _concentration_effect("eff-a", "grp-a")
        eff_b = _concentration_effect("eff-b", "grp-b")
        db, state = _make_db_session({"active_spell_effects": [eff_a, eff_b]})
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[eff_b],
            activeConcentration={"spellName": "Bless", "effectIds": ["eff-b"], "concentrationGroup": "grp-b"},
        )

        result = await clear_my_concentration(
            session_id="session-1",
            payload=ClearConcentrationRequest(concentrationGroup="grp-a"),
            user=_make_user(),
            session=db,
        )

        self.assertIsNotNone(result.activeConcentration)
        self.assertEqual(result.activeConcentration["concentrationGroup"], "grp-b")
        self.assertEqual(len(result.activeSpellEffects), 1)
        self.assertEqual(result.activeSpellEffects[0]["id"], "eff-b")

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_clear_with_no_active_effects_is_safe(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session({"currentHP": 10})
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={"currentHP": 10},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=None,
            activeConcentration=None,
        )

        result = await clear_my_concentration(
            session_id="session-1",
            payload=ClearConcentrationRequest(),
            user=_make_user(),
            session=db,
        )

        self.assertIsNone(result.activeConcentration)
        self.assertEqual(result.state["currentHP"], 10)
        mock_publish.assert_awaited_once()

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_response_includes_null_active_concentration_after_clearing(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session({"active_spell_effects": [_concentration_effect()]})
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=None,
            activeConcentration=None,
        )

        result = await clear_my_concentration(
            session_id="session-1",
            payload=ClearConcentrationRequest(),
            user=_make_user(),
            session=db,
        )

        self.assertIsNone(result.activeConcentration)

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_non_owner_player_cannot_clear_another_players_concentration(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session({"active_spell_effects": [_concentration_effect()]})
        state.player_user_id = "user-2"
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-2",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=None,
            activeConcentration=None,
        )

        user = _make_user("user-1")
        result = await clear_my_concentration(
            session_id="session-1",
            payload=ClearConcentrationRequest(),
            user=user,
            session=db,
        )

        # The DB query filters by session_id + user.id. Verify the query params
        # contain the requesting user's id so the DB enforces ownership.
        query_call = db.exec.call_args_list[0]
        built_query = query_call[0][0]
        self.assertEqual(
            built_query.compile().params.get("player_user_id_1"),
            "user-1",
        )


class TestRemoveMyPersistedEffect(unittest.IsolatedAsyncioTestCase):
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_removes_effect_and_returns_updated_state(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session(
            {"active_spell_effects": [_non_concentration_effect("eff-a"), _non_concentration_effect("eff-b")]}
        )
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[_non_concentration_effect("eff-b")],
            activeConcentration=None,
        )

        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-a",
            user=_make_user(),
            session=db,
        )

        self.assertEqual(len(result.activeSpellEffects), 1)
        self.assertEqual(result.activeSpellEffects[0]["id"], "eff-b")
        mock_publish.assert_awaited_once()

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_concentration_effect_clears_group(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        eff_a = _concentration_effect("eff-a", "grp-1")
        eff_b = _concentration_effect("eff-b", "grp-1")
        eff_c = _non_concentration_effect("eff-c")
        db, state = _make_db_session({"active_spell_effects": [eff_a, eff_b, eff_c]})
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[eff_c],
            activeConcentration=None,
        )

        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-a",
            user=_make_user(),
            session=db,
        )

        self.assertEqual(len(result.activeSpellEffects), 1)
        self.assertEqual(result.activeSpellEffects[0]["id"], "eff-c")
        self.assertIsNone(result.activeConcentration)
        mock_publish.assert_awaited_once()

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_unknown_effect_is_idempotent(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session(
            {"active_spell_effects": [_non_concentration_effect("eff-a")]}
        )
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[_non_concentration_effect("eff-a")],
            activeConcentration=None,
        )

        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-unknown",
            user=_make_user(),
            session=db,
        )

        self.assertEqual(len(result.activeSpellEffects), 1)
        self.assertEqual(result.activeSpellEffects[0]["id"], "eff-a")
        mock_publish.assert_awaited_once()

    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_non_owner_cannot_remove_another_players_effect(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session(
            {"active_spell_effects": [_non_concentration_effect("eff-a")]}
        )
        state.player_user_id = "user-2"
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-2",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[_non_concentration_effect("eff-a")],
            activeConcentration=None,
        )

        user = _make_user("user-1")
        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-a",
            user=user,
            session=db,
        )

        query_call = db.exec.call_args_list[0]
        built_query = query_call[0][0]
        self.assertEqual(
            built_query.compile().params.get("player_user_id_1"),
            "user-1",
        )


if __name__ == "__main__":
    unittest.main()
