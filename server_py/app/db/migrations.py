from __future__ import annotations

import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from app.core.config import settings
from app.db.session import engine

SERVER_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = SERVER_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_PATH = SERVER_ROOT / "alembic"


def _build_alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(ALEMBIC_SCRIPT_PATH))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def _wait_for_database() -> None:
    for attempt in range(1, settings.db_startup_retries + 1):
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
            return
        except Exception as exc:
            if attempt >= settings.db_startup_retries:
                raise RuntimeError(
                    "Database is unavailable during startup. "
                    "Check DATABASE_URL and make sure Postgres is running."
                ) from exc
            print(
                "Database not ready during startup "
                f"(attempt {attempt}/{settings.db_startup_retries}); retrying..."
            )
            time.sleep(settings.db_startup_retry_delay_seconds)


def _get_revision_state(config: Config) -> tuple[set[str], set[str]]:
    script = ScriptDirectory.from_config(config)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_heads = set(context.get_current_heads())
    return current_heads, set(script.get_heads())


def ensure_database_schema() -> None:
    _wait_for_database()
    config = _build_alembic_config()

    if settings.auto_migrate:
        command.upgrade(config, "head")
        current_heads, target_heads = _get_revision_state(config)
        print(
            "Database schema ready. "
            f"Current revisions: {sorted(current_heads)} / target: {sorted(target_heads)}"
        )
        return

    current_heads, target_heads = _get_revision_state(config)
    if current_heads != target_heads:
        raise RuntimeError(
            "Database schema is behind the application code. "
            f"Current revisions: {sorted(current_heads)}. "
            f"Target revisions: {sorted(target_heads)}. "
            "Run `cd server_py && . .venv/bin/activate && alembic upgrade head` "
            "or enable AUTO_MIGRATE=true."
        )
