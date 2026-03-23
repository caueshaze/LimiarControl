from pathlib import Path
import subprocess
import sys

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, text

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User

router = APIRouter()
REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
SYNC_SCRIPTS = ("import_dnd_base_items.py", "import_dnd_base_spells.py")
SCRIPT_TIMEOUT_SECONDS = 180


def _list_resettable_tables(session: Session) -> list[str]:
    rows = session.exec(
        text(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename <> 'alembic_version'
            ORDER BY tablename
            """
        )
    ).all()
    tables: list[str] = []
    for row in rows:
        if isinstance(row, str):
            tables.append(row)
            continue

        try:
            tables.append(row[0])
        except (TypeError, IndexError, KeyError):
            tables.append(str(row))
    return tables


def truncate_all_application_tables(session: Session) -> list[str]:
    tables = _list_resettable_tables(session)
    if not tables:
        return []

    quoted_tables = ", ".join(f'"{table}"' for table in tables)
    session.exec(text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))
    return tables


def _tail_output(raw: str, max_chars: int = 3000) -> str | None:
    normalized = raw.strip()
    if not normalized:
        return None
    if len(normalized) <= max_chars:
        return normalized
    return f"...{normalized[-max_chars:]}"


def _run_python_script(script_name: str) -> dict[str, object]:
    script_path = SCRIPTS_ROOT / script_name
    if not script_path.is_file():
        return {
            "script": script_name,
            "ok": False,
            "exitCode": -1,
            "stdoutTail": None,
            "stderrTail": f"Script not found: {script_path}",
        }

    try:
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "script": script_name,
            "ok": False,
            "exitCode": -1,
            "stdoutTail": _tail_output(exc.stdout or ""),
            "stderrTail": f"Timed out after {SCRIPT_TIMEOUT_SECONDS}s",
        }

    return {
        "script": script_name,
        "ok": completed.returncode == 0,
        "exitCode": completed.returncode,
        "stdoutTail": _tail_output(completed.stdout),
        "stderrTail": _tail_output(completed.stderr),
    }


@router.post("/reset")
def reset_database(session: Session = Depends(get_session)):
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Forbidden")
    tables = truncate_all_application_tables(session)
    session.commit()
    return {"ok": True, "tables": tables, "count": len(tables)}


@router.post("/sync-base-csvs")
def sync_base_csvs(_user: User = Depends(get_current_user)):
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Forbidden")

    results = [_run_python_script(script_name) for script_name in SYNC_SCRIPTS]
    failed = [result for result in results if not result["ok"]]
    if failed:
        failed_script = str(failed[0]["script"])
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"CSV sync failed while running {failed_script}.",
                "scripts": results,
            },
        )

    return {
        "ok": True,
        "message": "Base CSV catalogs synchronized successfully.",
        "scripts": results,
    }
