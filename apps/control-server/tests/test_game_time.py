import unittest
from unittest.mock import MagicMock

from app.models.session import SessionStatus
from app.models.session_runtime import SessionRuntime
from app.schemas.session import SessionRuntimeRead
from app.services.game_time import (
    advance_game_time_seconds,
    get_game_time_seconds,
    set_game_time_seconds,
)


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
        from app.api.routes.sessions.campaign_sessions_start_service import reset_runtime

        runtime = SessionRuntime(session_id="s1")
        runtime.game_time_seconds = 9999
        reset_runtime(runtime)
        self.assertEqual(runtime.game_time_seconds, 0)
