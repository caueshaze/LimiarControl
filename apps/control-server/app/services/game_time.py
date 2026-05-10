from sqlmodel import Session as DbSession, select

from app.models.session_runtime import SessionRuntime

SHORT_REST_GAME_TIME_SECONDS = 60 * 60
LONG_REST_GAME_TIME_SECONDS = 8 * 60 * 60


def _require_runtime(session_id: str, db: DbSession) -> SessionRuntime:
    runtime = db.exec(
        select(SessionRuntime).where(SessionRuntime.session_id == session_id)
    ).first()
    if runtime is None:
        raise ValueError(f"SessionRuntime not found for session {session_id}")
    return runtime


def get_game_time_seconds(session_id: str, db: DbSession) -> int:
    runtime = db.exec(
        select(SessionRuntime).where(SessionRuntime.session_id == session_id)
    ).first()
    value = getattr(runtime, "game_time_seconds", None) if runtime else None
    return value if isinstance(value, int) else 0


def set_game_time_seconds(session_id: str, value: int, db: DbSession) -> None:
    if value < 0:
        raise ValueError("game_time_seconds cannot be negative")
    runtime = _require_runtime(session_id, db)
    runtime.game_time_seconds = value


def advance_game_time_seconds(session_id: str, delta_seconds: int, db: DbSession) -> None:
    if delta_seconds < 0:
        raise ValueError("delta_seconds cannot be negative")
    runtime = _require_runtime(session_id, db)
    runtime.game_time_seconds += delta_seconds
