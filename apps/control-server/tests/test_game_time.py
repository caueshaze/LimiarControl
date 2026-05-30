import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.campaign_member import RoleMode
from app.models.combat import CombatPhase, CombatState
from app.models.session import SessionStatus
from app.models.session_runtime import SessionRuntime
from app.schemas.session import (
    GameTimeActivityEvent,
    RestActivityEvent,
    SessionRuntimeRead,
)
from app.services.game_time import (
    LONG_REST_GAME_TIME_SECONDS,
    SHORT_REST_GAME_TIME_SECONDS,
    advance_game_time_seconds,
    get_game_time_seconds,
    set_game_time_seconds,
)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _mock_db(runtime=None):
    db = MagicMock()
    db.exec.return_value.first.return_value = runtime
    return db


class GameTimeServiceTests(unittest.TestCase):
    def test_default_game_time_seconds_is_zero(self):
        runtime = SessionRuntime(session_id="s1")
        self.assertEqual(runtime.game_time_seconds, 0)

    def test_get_returns_zero_when_runtime_missing(self):
        db = _mock_db(runtime=None)
        self.assertEqual(get_game_time_seconds("s1", db), 0)

    def test_get_returns_stored_value(self):
        runtime = SessionRuntime(session_id="s1")
        runtime.game_time_seconds = 3600
        db = _mock_db(runtime=runtime)
        self.assertEqual(get_game_time_seconds("s1", db), 3600)

    def test_set_persists_value(self):
        runtime = SessionRuntime(session_id="s1")
        db = _mock_db(runtime=runtime)
        set_game_time_seconds("s1", 7200, db)
        self.assertEqual(runtime.game_time_seconds, 7200)

    def test_set_rejects_negative(self):
        runtime = SessionRuntime(session_id="s1")
        db = _mock_db(runtime=runtime)
        with self.assertRaises(ValueError):
            set_game_time_seconds("s1", -1, db)

    def test_set_raises_when_runtime_missing(self):
        db = _mock_db(runtime=None)
        with self.assertRaises(ValueError):
            set_game_time_seconds("s1", 100, db)

    def test_advance_accumulates(self):
        runtime = SessionRuntime(session_id="s1")
        runtime.game_time_seconds = 100
        db = _mock_db(runtime=runtime)
        advance_game_time_seconds("s1", 50, db)
        self.assertEqual(runtime.game_time_seconds, 150)

    def test_advance_rejects_negative_delta(self):
        runtime = SessionRuntime(session_id="s1")
        db = _mock_db(runtime=runtime)
        with self.assertRaises(ValueError):
            advance_game_time_seconds("s1", -10, db)

    def test_advance_raises_when_runtime_missing(self):
        db = _mock_db(runtime=None)
        with self.assertRaises(ValueError):
            advance_game_time_seconds("s1", 10, db)


class GameTimeSchemaTests(unittest.TestCase):
    def test_runtime_read_includes_game_time_seconds(self):
        read = SessionRuntimeRead(
            sessionId="s1",
            campaignId="c1",
            status=SessionStatus.ACTIVE,
            shopOpen=False,
            combatActive=False,
            gameTimeSeconds=3600,
        )
        self.assertEqual(read.gameTimeSeconds, 3600)

    def test_runtime_read_defaults_to_zero(self):
        read = SessionRuntimeRead(
            sessionId="s1",
            campaignId="c1",
            status=SessionStatus.ACTIVE,
            shopOpen=False,
            combatActive=False,
        )
        self.assertEqual(read.gameTimeSeconds, 0)


class ResetRuntimeTests(unittest.TestCase):
    def test_reset_runtime_resets_game_time(self):
        from app.api.routes.sessions.campaign_sessions.start_service import reset_runtime

        runtime = SessionRuntime(session_id="s1")
        runtime.game_time_seconds = 9999
        reset_runtime(runtime)
        self.assertEqual(runtime.game_time_seconds, 0)


class GameTimeConstantsTests(unittest.TestCase):
    def test_short_rest_constant_is_3600(self):
        self.assertEqual(SHORT_REST_GAME_TIME_SECONDS, 3600)

    def test_long_rest_constant_is_28800(self):
        self.assertEqual(LONG_REST_GAME_TIME_SECONDS, 28800)


class AdvanceValidationTests(unittest.TestCase):
    def test_advance_accepts_zero_as_no_op(self):
        runtime = SessionRuntime(session_id="s1")
        runtime.game_time_seconds = 100
        db = _mock_db(runtime=runtime)
        advance_game_time_seconds("s1", 0, db)
        self.assertEqual(runtime.game_time_seconds, 100)


class AdvanceGameTimeCommandTests(unittest.TestCase):
    def _make_payload(self, seconds=None):
        payload = MagicMock()
        payload.type = "advance_game_time"
        payload.payload = {"seconds": seconds} if seconds is not None else {}
        return payload

    def _make_runtime(self, game_time=0):
        runtime = SessionRuntime(session_id="s1")
        runtime.game_time_seconds = game_time
        runtime.combat_active = False
        return runtime

    def _make_entry(self):
        entry = MagicMock()
        entry.id = "s1"
        entry.campaign_id = "c1"
        entry.party_id = None
        entry.status = SessionStatus.ACTIVE
        return entry

    def _make_member(self):
        member = MagicMock()
        member.id = "member-1"
        member.display_name = "GM"
        member.role_mode = RoleMode.GM
        return member

    def _make_user(self):
        user = MagicMock()
        user.id = "gm-1"
        return user

    @patch("app.api.routes.sessions.commands_service.publish_state_updates", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.advance_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_valid_seconds_advances_game_time(
        self, mock_require, mock_runtime, mock_rest_state, mock_advance, mock_publish, mock_publish_state,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service

        runtime = self._make_runtime(game_time=100)
        mock_require.return_value = (self._make_entry(), self._make_member())
        mock_runtime.return_value = runtime
        mock_advance.side_effect = lambda sid, delta, db: setattr(runtime, "game_time_seconds", runtime.game_time_seconds + delta)

        db = MagicMock()

        result = _run_async(
            send_session_command_service("s1", self._make_payload(seconds=3600), self._make_user(), db)
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(runtime.game_time_seconds, 3700)
        mock_publish.assert_awaited_once()
        published_entry, event_type, event_payload, issued_at = mock_publish.await_args.args
        self.assertEqual(published_entry.id, "s1")
        self.assertEqual(event_type, "game_time_advanced")
        self.assertEqual(event_payload["seconds"], 3600)
        self.assertEqual(event_payload["gameTimeSeconds"], 3700)
        self.assertIsNotNone(issued_at)

    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_rejects_zero_seconds(
        self, mock_require, mock_runtime, mock_rest_state, mock_publish,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service
        import asyncio

        mock_require.return_value = (self._make_entry(), self._make_member())
        mock_runtime.return_value = self._make_runtime()

        db = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            _run_async(
                send_session_command_service("s1", self._make_payload(seconds=0), self._make_user(), db)
            )
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_rejects_negative_seconds(
        self, mock_require, mock_runtime, mock_rest_state, mock_publish,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service
        import asyncio

        mock_require.return_value = (self._make_entry(), self._make_member())
        mock_runtime.return_value = self._make_runtime()

        db = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            _run_async(
                send_session_command_service("s1", self._make_payload(seconds=-100), self._make_user(), db)
            )
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_rejects_missing_seconds(
        self, mock_require, mock_runtime, mock_rest_state, mock_publish,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service
        import asyncio

        mock_require.return_value = (self._make_entry(), self._make_member())
        mock_runtime.return_value = self._make_runtime()

        payload = MagicMock()
        payload.type = "advance_game_time"
        payload.payload = {}

        db = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            _run_async(
                send_session_command_service("s1", payload, self._make_user(), db)
            )
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_rejects_non_integer_seconds(
        self, mock_require, mock_runtime, mock_rest_state, mock_publish,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service
        import asyncio

        mock_require.return_value = (self._make_entry(), self._make_member())
        mock_runtime.return_value = self._make_runtime()

        db = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            _run_async(
                send_session_command_service("s1", self._make_payload(seconds=3.5), self._make_user(), db)
            )
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.api.routes.sessions.commands_service.publish_state_updates", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.advance_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_records_activity_with_reason_and_game_time(
        self, mock_require, mock_runtime, mock_rest_state, mock_advance, mock_publish, mock_publish_state,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service
        import asyncio

        runtime = self._make_runtime(game_time=0)
        mock_require.return_value = (self._make_entry(), self._make_member())
        mock_runtime.return_value = runtime
        mock_advance.side_effect = lambda sid, delta, db: setattr(runtime, "game_time_seconds", runtime.game_time_seconds + delta)

        db = MagicMock()

        _run_async(
            send_session_command_service("s1", self._make_payload(seconds=3600), self._make_user(), db)
        )

        activity_adds = [c.args[0] for c in db.add.call_args_list]
        cmd_events = [a for a in activity_adds if hasattr(a, "command_type")]
        self.assertTrue(any(e.command_type == "advance_game_time" for e in cmd_events))
        cmd = next(e for e in cmd_events if e.command_type == "advance_game_time")
        self.assertEqual(cmd.payload_json["seconds"], 3600)
        self.assertEqual(cmd.payload_json["gameTimeSeconds"], 3600)
        self.assertEqual(cmd.payload_json["reason"], "manual")

    @patch("app.api.routes.sessions.commands_service.publish_state_updates", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.advance_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_manual_advancement_prunes_expired_timed_effects(
        self, mock_require, mock_runtime, mock_rest_state, mock_advance, mock_publish, mock_publish_state,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service

        runtime = self._make_runtime(game_time=3500)
        state = MagicMock()
        state.session_id = "s1"
        state.player_user_id = "player-1"
        state.state_json = {
            "active_spell_effects": [
                {
                    "id": "eff-expired",
                    "kind": "spell_effect",
                    "duration_type": "timed",
                    "expires_at_game_time_seconds": 3600,
                    "created_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        }
        mock_require.return_value = (self._make_entry(), self._make_member())
        mock_runtime.return_value = runtime
        mock_advance.side_effect = lambda sid, delta, db: setattr(runtime, "game_time_seconds", runtime.game_time_seconds + delta)

        db = MagicMock()
        db.exec.return_value.all.return_value = [state]

        _run_async(
            send_session_command_service("s1", self._make_payload(seconds=200), self._make_user(), db)
        )

        self.assertNotIn("active_spell_effects", state.state_json)
        mock_publish_state.assert_awaited_once()
        published_entry, published_states, issued_at = mock_publish_state.await_args.args
        self.assertEqual(published_entry.id, "s1")
        self.assertEqual(len(published_states), 1)
        self.assertIs(published_states[0], state)

    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._prune_expired_timed_combat_effects")
    @patch("app.api.routes.sessions.commands_service.publish_state_updates", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.advance_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_manual_advancement_during_active_combat_publishes_updated_combat_state(
        self,
        mock_require,
        mock_runtime,
        mock_rest_state,
        mock_get_game_time_seconds,
        mock_advance,
        mock_publish_cmd,
        mock_publish_state,
        mock_prune,
        mock_emit_combat_state,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service

        runtime = self._make_runtime(game_time=100)
        runtime.combat_active = True
        session_state = MagicMock()
        session_state.session_id = "s1"
        session_state.player_user_id = "player-1"
        session_state.state_json = {}
        combat_state = CombatState(
            id="combat-1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Hero",
                    "status": "active",
                    "team": "players",
                    "active_effects": [],
                }
            ],
        )
        mock_require.return_value = (self._make_entry(), self._make_member())
        mock_runtime.return_value = runtime
        mock_get_game_time_seconds.return_value = 106
        mock_advance.side_effect = lambda sid, delta, db: setattr(runtime, "game_time_seconds", runtime.game_time_seconds + delta)
        mock_prune.return_value = {
            "changed": True,
            "removed_effects": [{"id": "eff-expired"}],
            "removed_area_effects": [],
            "modified_states": [session_state],
        }

        states_result = MagicMock()
        states_result.all.return_value = [session_state]
        combat_result = MagicMock()
        combat_result.first.return_value = combat_state
        db = MagicMock()
        db.exec.side_effect = [states_result, combat_result]

        _run_async(
            send_session_command_service("s1", self._make_payload(seconds=6), self._make_user(), db)
        )

        mock_prune.assert_called_once()
        mock_emit_combat_state.assert_awaited_once_with("s1", combat_state)
        mock_publish_state.assert_awaited_once()
        published_entry, published_states, issued_at = mock_publish_state.await_args.args
        self.assertEqual(published_entry.id, "s1")
        self.assertEqual(published_states, [session_state])
        mock_publish_cmd.assert_awaited_once()

    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="exploration")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_requires_gm_authorization_for_manual_advancement(
        self, mock_require, mock_runtime, mock_rest_state, mock_publish,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service

        mock_require.side_effect = HTTPException(status_code=403, detail="GM required")
        db = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            _run_async(
                send_session_command_service("s1", self._make_payload(seconds=3600), self._make_user(), db)
            )

        self.assertEqual(ctx.exception.status_code, 403)
        mock_runtime.assert_not_called()
        mock_publish.assert_not_awaited()


class RestGameTimeAdvanceTests(unittest.TestCase):
    def _make_runtime(self, game_time=0):
        runtime = SessionRuntime(session_id="s1")
        runtime.game_time_seconds = game_time
        return runtime

    def _make_entry(self):
        entry = MagicMock()
        entry.id = "s1"
        entry.campaign_id = "c1"
        entry.party_id = None
        entry.status = SessionStatus.ACTIVE
        return entry

    def _make_member(self):
        member = MagicMock()
        member.id = "member-1"
        member.display_name = "GM"
        member.role_mode = RoleMode.GM
        return member

    def _make_user(self):
        user = MagicMock()
        user.id = "gm-1"
        return user

    def _make_state(self, rest_state="exploration"):
        state = MagicMock()
        state.session_id = "s1"
        state.player_user_id = "player-1"
        state.state_json = {"restState": rest_state}
        return state

    def _make_end_rest_payload(self):
        payload = MagicMock()
        payload.type = "end_rest"
        payload.payload = {}
        return payload

    @patch("app.api.routes.sessions.commands_service.publish_state_updates", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.advance_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="short_rest")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_short_rest_end_advances_by_3600(
        self, mock_require, mock_runtime, mock_rest_state, mock_advance, mock_publish_cmd, mock_publish_state,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service
        import asyncio

        runtime = self._make_runtime(game_time=0)
        entry = self._make_entry()
        member = self._make_member()
        user = self._make_user()
        state = self._make_state(rest_state="short_rest")

        mock_require.return_value = (entry, member)
        mock_runtime.return_value = runtime

        def advance_side_effect(session_id, delta, db):
            runtime.game_time_seconds += delta

        mock_advance.side_effect = advance_side_effect

        db = MagicMock()
        db.exec.return_value.all.return_value = [state]
        db.exec.return_value.first.return_value = None

        result = _run_async(
            send_session_command_service("s1", self._make_end_rest_payload(), user, db)
        )
        self.assertEqual(result, {"ok": True})
        mock_advance.assert_called_once_with("s1", SHORT_REST_GAME_TIME_SECONDS, db)
        self.assertEqual(runtime.game_time_seconds, SHORT_REST_GAME_TIME_SECONDS)
        self.assertEqual(state.state_json["restState"], "exploration")
        mock_publish_state.assert_awaited_once()
        published_entry, published_states, issued_at = mock_publish_state.await_args.args
        self.assertEqual(published_entry.id, "s1")
        self.assertEqual(len(published_states), 1)
        self.assertIs(published_states[0], state)
        self.assertIsNotNone(issued_at)
        mock_publish_cmd.assert_awaited_once()
        cmd_entry, event_type, event_payload, cmd_issued_at = mock_publish_cmd.await_args.args
        self.assertEqual(cmd_entry.id, "s1")
        self.assertEqual(event_type, "rest_ended")
        self.assertEqual(event_payload["restType"], "short_rest")
        self.assertEqual(event_payload["secondsAdvanced"], SHORT_REST_GAME_TIME_SECONDS)
        self.assertEqual(event_payload["gameTimeSeconds"], SHORT_REST_GAME_TIME_SECONDS)
        self.assertEqual(event_payload["issuedAt"], cmd_issued_at.isoformat())

    @patch("app.api.routes.sessions.commands_service.publish_state_updates", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.advance_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="long_rest")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_long_rest_end_advances_by_28800(
        self, mock_require, mock_runtime, mock_rest_state, mock_advance, mock_publish_cmd, mock_publish_state,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service
        import asyncio

        runtime = self._make_runtime(game_time=1000)
        entry = self._make_entry()
        member = self._make_member()
        user = self._make_user()
        state = self._make_state(rest_state="long_rest")

        mock_require.return_value = (entry, member)
        mock_runtime.return_value = runtime

        def advance_side_effect(session_id, delta, db):
            runtime.game_time_seconds += delta

        mock_advance.side_effect = advance_side_effect

        db = MagicMock()
        db.exec.return_value.all.return_value = [state]
        db.exec.return_value.first.return_value = None

        result = _run_async(
            send_session_command_service("s1", self._make_end_rest_payload(), user, db)
        )
        self.assertEqual(result, {"ok": True})
        mock_advance.assert_called_once_with("s1", LONG_REST_GAME_TIME_SECONDS, db)
        self.assertEqual(runtime.game_time_seconds, 1000 + LONG_REST_GAME_TIME_SECONDS)
        self.assertEqual(state.state_json["restState"], "exploration")
        mock_publish_cmd.assert_awaited_once()
        published_entry, event_type, event_payload, issued_at = mock_publish_cmd.await_args.args
        self.assertEqual(published_entry.id, "s1")
        self.assertEqual(event_type, "rest_ended")
        self.assertEqual(event_payload["restType"], "long_rest")
        self.assertEqual(event_payload["secondsAdvanced"], LONG_REST_GAME_TIME_SECONDS)
        self.assertEqual(event_payload["gameTimeSeconds"], 1000 + LONG_REST_GAME_TIME_SECONDS)
        self.assertEqual(event_payload["issuedAt"], issued_at.isoformat())

    @patch("app.api.routes.sessions.commands_service.publish_state_updates", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.advance_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="short_rest")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_rest_end_activity_payload_includes_game_time(
        self, mock_require, mock_runtime, mock_rest_state, mock_advance, mock_publish_cmd, mock_publish_state,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service
        import asyncio

        runtime = self._make_runtime(game_time=500)
        entry = self._make_entry()
        member = self._make_member()
        user = self._make_user()
        state = self._make_state(rest_state="short_rest")

        mock_require.return_value = (entry, member)
        mock_runtime.return_value = runtime

        def advance_side_effect(session_id, delta, db):
            runtime.game_time_seconds += delta

        mock_advance.side_effect = advance_side_effect

        db = MagicMock()
        db.exec.return_value.all.return_value = [state]
        db.exec.return_value.first.return_value = None

        _run_async(
            send_session_command_service("s1", self._make_end_rest_payload(), user, db)
        )

        activity_adds = [c.args[0] for c in db.add.call_args_list]
        cmd_events = [a for a in activity_adds if hasattr(a, "command_type")]
        end_rest_cmd = next(e for e in cmd_events if e.command_type == "end_rest")
        self.assertEqual(end_rest_cmd.payload_json["secondsAdvanced"], SHORT_REST_GAME_TIME_SECONDS)
        self.assertEqual(end_rest_cmd.payload_json["gameTimeSeconds"], 500 + SHORT_REST_GAME_TIME_SECONDS)

    @patch("app.api.routes.sessions.commands_service.publish_state_updates", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.publish_command_event", new_callable=AsyncMock)
    @patch("app.api.routes.sessions.commands_service.advance_game_time_seconds")
    @patch("app.api.routes.sessions.commands_service.get_session_rest_state", return_value="short_rest")
    @patch("app.api.routes.sessions.commands_service.get_or_create_session_runtime")
    @patch("app.api.routes.sessions.commands_service.require_active_gm_session")
    def test_rest_end_prunes_expired_timed_effects_after_advancing_time(
        self, mock_require, mock_runtime, mock_rest_state, mock_advance, mock_publish_cmd, mock_publish_state,
    ):
        from app.api.routes.sessions.commands_service import send_session_command_service

        runtime = self._make_runtime(game_time=0)
        entry = self._make_entry()
        member = self._make_member()
        user = self._make_user()
        state = self._make_state(rest_state="short_rest")
        state.state_json["active_spell_effects"] = [
            {
                "id": "eff-expired",
                "kind": "spell_effect",
                "duration_type": "timed",
                "expires_at_game_time_seconds": SHORT_REST_GAME_TIME_SECONDS,
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ]

        mock_require.return_value = (entry, member)
        mock_runtime.return_value = runtime

        def advance_side_effect(session_id, delta, db):
            runtime.game_time_seconds += delta

        mock_advance.side_effect = advance_side_effect

        db = MagicMock()
        db.exec.return_value.all.return_value = [state]
        db.exec.return_value.first.return_value = None

        _run_async(
            send_session_command_service("s1", self._make_end_rest_payload(), user, db)
        )

        self.assertNotIn("active_spell_effects", state.state_json)
        mock_publish_state.assert_awaited_once()
        published_entry, published_states, issued_at = mock_publish_state.await_args.args
        self.assertEqual(published_entry.id, "s1")
        self.assertEqual(len(published_states), 1)
        self.assertIs(published_states[0], state)


class GameTimeActivityMappingTests(unittest.TestCase):
    def test_advance_game_time_maps_to_game_time_event(self):
        from app.api.routes.sessions.activity import get_session_activity

        entry = MagicMock()
        entry.id = "session-1"
        entry.campaign_id = "camp-1"
        entry.started_at = None
        entry.created_at = None

        member = MagicMock()
        member.id = "member-1"

        cmd = MagicMock()
        cmd.user_id = "gm-1"
        cmd.actor_name = "GM"
        cmd.command_type = "advance_game_time"
        cmd.created_at = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
        cmd.payload_json = {
            "seconds": 3600,
            "gameTimeSeconds": 3600,
            "reason": "manual",
        }

        gm_user = MagicMock()
        gm_user.username = "gm"
        gm_user.display_name = "GM"

        db = MagicMock()
        call_count = [0]

        def exec_side(query):
            result = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                result.first.return_value = entry
            elif idx == 1:
                result.first.return_value = member
            elif idx in (2, 3):
                result.all.return_value = []
            else:
                result.all.return_value = [(cmd, gm_user)]
            return result

        db.exec.side_effect = exec_side

        user = MagicMock()
        user.id = "gm-1"
        events = get_session_activity("session-1", user=user, session=db)

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, GameTimeActivityEvent)
        self.assertEqual(event.seconds, 3600)
        self.assertEqual(event.gameTimeSeconds, 3600)
        self.assertEqual(event.reason, "manual")

    def test_rest_end_maps_with_game_time_fields(self):
        from app.api.routes.sessions.activity import get_session_activity

        entry = MagicMock()
        entry.id = "session-1"
        entry.campaign_id = "camp-1"
        entry.started_at = None
        entry.created_at = None

        member = MagicMock()
        member.id = "member-1"

        cmd = MagicMock()
        cmd.user_id = "gm-1"
        cmd.actor_name = "GM"
        cmd.command_type = "end_rest"
        cmd.created_at = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
        cmd.payload_json = {
            "restType": "short_rest",
            "secondsAdvanced": 3600,
            "gameTimeSeconds": 3600,
        }

        gm_user = MagicMock()
        gm_user.username = "gm"
        gm_user.display_name = "GM"

        db = MagicMock()
        call_count = [0]

        def exec_side(query):
            result = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                result.first.return_value = entry
            elif idx == 1:
                result.first.return_value = member
            elif idx in (2, 3):
                result.all.return_value = []
            else:
                result.all.return_value = [(cmd, gm_user)]
            return result

        db.exec.side_effect = exec_side

        user = MagicMock()
        user.id = "gm-1"
        events = get_session_activity("session-1", user=user, session=db)

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, RestActivityEvent)
        self.assertEqual(event.action, "short_ended")
        self.assertEqual(event.secondsAdvanced, 3600)
        self.assertEqual(event.gameTimeSeconds, 3600)
