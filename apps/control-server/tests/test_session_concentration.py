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


class TestAllyTargetConcentrationRemoval(unittest.IsolatedAsyncioTestCase):
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session")
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    async def test_removing_ally_target_concentration_effect_breaks_entire_group(
        self,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_clear_cross_session,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        group_effect = {
            "id": "eff-ally",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-1",
                "source_spell_name": "Bless",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "target-1",
            },
        }
        target_unrelated = _non_concentration_effect("target-unrelated")
        db, state = _make_db_session(
            {"active_spell_effects": [group_effect, target_unrelated]}
        )
        state.player_user_id = "target-1"
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x

        caster_unrelated = _non_concentration_effect("caster-unrelated")
        ally_unrelated = _non_concentration_effect("ally-unrelated")
        caster_state = MagicMock()
        caster_state.player_user_id = "caster-1"
        caster_state.updated_at = None
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.state_json = {"active_spell_effects": [caster_unrelated]}

        ally_state = MagicMock()
        ally_state.player_user_id = "ally-b"
        ally_state.updated_at = None
        ally_state.created_at = "2026-01-01T00:00:00+00:00"
        ally_state.state_json = {"active_spell_effects": [ally_unrelated]}

        duplicate_target_state = MagicMock()
        duplicate_target_state.player_user_id = "target-1"
        duplicate_target_state.updated_at = None
        duplicate_target_state.created_at = "2026-01-01T00:00:00+00:00"
        duplicate_target_state.state_json = {"active_spell_effects": [target_unrelated]}

        mock_clear_cross_session.return_value = [
            caster_state,
            ally_state,
            duplicate_target_state,
        ]

        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-ally",
            user=_make_user("target-1"),
            session=db,
        )

        mock_clear_cross_session.assert_called_once_with(
            db, "session-1", "grp-1", exclude_user_id="target-1"
        )
        self.assertIsNone(result.activeConcentration)
        self.assertEqual(result.activeSpellEffects, [target_unrelated])
        self.assertEqual(state.state_json["active_spell_effects"], [target_unrelated])
        self.assertEqual(mock_publish.await_count, 3)

        published_payloads = {
            call.args[1]: call.args[3]["active_spell_effects"]
            for call in mock_publish.await_args_list
        }
        self.assertEqual(set(published_payloads), {"target-1", "caster-1", "ally-b"})
        self.assertEqual(
            [effect["id"] for effect in published_payloads["target-1"]],
            ["target-unrelated"],
        )
        self.assertEqual(
            [effect["id"] for effect in published_payloads["caster-1"]],
            ["caster-unrelated"],
        )
        self.assertEqual(
            [effect["id"] for effect in published_payloads["ally-b"]],
            ["ally-unrelated"],
        )
        for effects in published_payloads.values():
            self.assertTrue(
                all((effect.get("metadata") or {}).get("concentration_group") != "grp-1" for effect in effects)
            )

    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session")
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_ally_target_removal_clears_other_ally_effects(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_clear_cross_session,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        eff = {
            "id": "eff-ally-a",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-1",
                "source_spell_name": "Bless",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
            },
        }
        db, state = _make_db_session({"active_spell_effects": [eff]})
        state.player_user_id = "ally-a"
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x

        caster_state = MagicMock()
        caster_state.player_user_id = "caster-1"
        caster_state.updated_at = None
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.state_json = {}

        ally_b_state = MagicMock()
        ally_b_state.player_user_id = "ally-b"
        ally_b_state.updated_at = None
        ally_b_state.created_at = "2026-01-01T00:00:00+00:00"
        ally_b_state.state_json = {}

        mock_clear_cross_session.return_value = [caster_state, ally_b_state]
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="ally-a",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[],
            activeConcentration=None,
        )

        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-ally-a",
            user=_make_user("ally-a"),
            session=db,
        )

        mock_clear_cross_session.assert_called_once_with(
            db, "session-1", "grp-1", exclude_user_id="ally-a"
        )
        self.assertEqual(mock_publish.await_count, 3)

    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session")
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_self_target_removal_skips_cross_clear(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_clear_cross_session,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        eff = {
            "id": "eff-self",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-1",
                "source_spell_name": "Bless",
                "caster_player_user_id": "user-1",
                "target_player_user_id": "user-1",
            },
        }
        db, state = _make_db_session({"active_spell_effects": [eff]})
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_clear_cross_session.return_value = []
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[],
            activeConcentration=None,
        )

        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-self",
            user=_make_user("user-1"),
            session=db,
        )

        mock_clear_cross_session.assert_not_called()
        self.assertEqual(mock_publish.await_count, 1)

    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session")
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_non_concentration_removal_skips_cross_clear(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_clear_cross_session,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session(
            {"active_spell_effects": [_non_concentration_effect("eff-other")]}
        )
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_clear_cross_session.return_value = []
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="user-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[],
            activeConcentration=None,
        )

        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-other",
            user=_make_user(),
            session=db,
        )

        mock_clear_cross_session.assert_not_called()
        self.assertEqual(mock_publish.await_count, 1)

    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session")
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_unknown_effect_removal_is_idempotent_no_cross_clear(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_clear_cross_session,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session(
            {"active_spell_effects": [_non_concentration_effect("eff-a")]}
        )
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_clear_cross_session.return_value = []
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

        mock_clear_cross_session.assert_not_called()
        self.assertEqual(mock_publish.await_count, 1)

    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session")
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.publish_state_update")
    @patch("app.api.routes.sessions.state.to_state_read")
    async def test_ally_target_removal_publishes_all_modified_states(
        self,
        mock_to_state_read,
        mock_publish,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_clear_cross_session,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        eff = {
            "id": "eff-ally",
            "kind": "spell_effect",
            "duration_type": "manual",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-1",
                "source_spell_name": "Bless",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "target-1",
            },
        }
        db, state = _make_db_session({"active_spell_effects": [eff]})
        state.player_user_id = "target-1"
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x

        caster_state = MagicMock()
        caster_state.player_user_id = "caster-1"
        caster_state.updated_at = None
        caster_state.created_at = "2026-01-01T00:00:00+00:00"
        caster_state.state_json = {}

        caller_dup = MagicMock()
        caller_dup.player_user_id = "target-1"
        caller_dup.updated_at = None
        caller_dup.created_at = "2026-01-01T00:00:00+00:00"
        caller_dup.state_json = {}

        mock_clear_cross_session.return_value = [caster_state, caller_dup]
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="target-1",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[],
            activeConcentration=None,
        )

        result = await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-ally",
            user=_make_user("target-1"),
            session=db,
        )

        self.assertEqual(mock_publish.await_count, 2)
        published_ids = [
            mock_publish.await_args_list[i].args[1] for i in range(mock_publish.await_count)
        ]
        self.assertIn("target-1", published_ids)
        self.assertIn("caster-1", published_ids)


class TestOutOfCombatRemovalActivityLogging(unittest.IsolatedAsyncioTestCase):
    @patch("app.api.routes.sessions.state._prune_out_of_combat_session_activity")
    @patch("app.api.routes.sessions.state.record_session_activity")
    @patch("app.api.routes.sessions.state._resolve_ooc_activity_actor", return_value=("member-1", "Ally A"))
    @patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[])
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.publish_state_update")
    async def test_removing_existing_effect_records_out_of_combat_effect_removed(
        self,
        mock_publish,
        mock_to_state_read,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_clear_cross,
        mock_resolve_actor,
        mock_record_activity,
        mock_prune_activity,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        effect = {
            "id": "eff-ally",
            "kind": "spell_effect",
            "duration_type": "manual",
            "display_label": "Melhorar Habilidade — Sabedoria da Coruja",
            "metadata": {
                "concentration": True,
                "concentration_group": "grp-1",
                "source_spell_name": "Melhorar Habilidade",
                "selected_variant_label": "Sabedoria da Coruja",
                "caster_player_user_id": "caster-1",
                "target_player_user_id": "ally-a",
            },
        }
        db, state = _make_db_session({"active_spell_effects": [effect]})
        state.player_user_id = "ally-a"
        mock_ensure.return_value = state
        mock_finalize.side_effect = lambda x: x
        mock_to_state_read.return_value = SessionStateRead(
            id="ss-1",
            sessionId="session-1",
            playerUserId="ally-a",
            state={},
            createdAt="2026-01-01T00:00:00+00:00",
            updatedAt=None,
            activeSpellEffects=[],
            activeConcentration=None,
        )

        await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-ally",
            user=_make_user("ally-a"),
            session=db,
        )

        mock_record_activity.assert_called_once()
        activity_call = mock_record_activity.call_args
        self.assertEqual(activity_call.args[1], "out_of_combat_effect_removed")
        payload = activity_call.kwargs["payload"]
        self.assertEqual(payload["actor_player_user_id"], "ally-a")
        self.assertEqual(payload["actor_display_name"], "Ally A")
        self.assertEqual(payload["removed_effect_id"], "eff-ally")
        self.assertEqual(payload["effect_label"], "Melhorar Habilidade — Sabedoria da Coruja")
        self.assertEqual(payload["source_spell_name"], "Melhorar Habilidade")
        self.assertEqual(payload["variant_label"], "Sabedoria da Coruja")
        self.assertEqual(payload["concentration_group"], "grp-1")
        self.assertTrue(payload["broke_concentration_group"])
        mock_prune_activity.assert_called_once_with(db, "session-1")

    @patch("app.api.routes.sessions.state._prune_out_of_combat_session_activity")
    @patch("app.api.routes.sessions.state.record_session_activity")
    @patch("app.api.routes.sessions.state.get_session_entry")
    @patch("app.api.routes.sessions.state.require_session_view_access")
    @patch("app.api.routes.sessions.state.ensure_session_state")
    @patch("app.api.routes.sessions.state.finalize_session_state_data")
    @patch("app.api.routes.sessions.state.to_state_read")
    @patch("app.api.routes.sessions.state.publish_state_update")
    async def test_unknown_effect_removal_does_not_record_activity(
        self,
        mock_publish,
        mock_to_state_read,
        mock_finalize,
        mock_ensure,
        mock_require_view,
        mock_get_entry,
        mock_record_activity,
        mock_prune_activity,
    ):
        mock_get_entry.return_value = MagicMock(party_id="party-1")
        db, state = _make_db_session({"active_spell_effects": [_non_concentration_effect("eff-a")]})
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

        await remove_my_persisted_effect(
            session_id="session-1",
            effect_id="eff-unknown",
            user=_make_user("user-1"),
            session=db,
        )

        mock_record_activity.assert_not_called()
        mock_prune_activity.assert_not_called()


if __name__ == "__main__":
    unittest.main()
