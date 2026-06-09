from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, text

from app.api.deps import get_current_user, require_system_admin
from app.core.config import settings
from app.db.session import get_session
from app.models.user import User

router = APIRouter()


def _dev_or_admin(
    request: Request, session: Session = Depends(get_session)
) -> Optional[User]:
    if settings.app_env == "development":
        return None
    return require_system_admin(get_current_user(request, session))


def _list_resettable_tables(session: Session) -> list[str]:
    query = text(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename <> 'alembic_version'
        ORDER BY tablename
        """
    )
    # sqlmodel's exec() stub only types SELECT statements, not raw text() clauses.
    rows = session.exec(query).all()  # type: ignore[call-overload]
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
    session.exec(text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))  # type: ignore[call-overload]
    return tables

@router.post("/reset")
def reset_database(
    session: Session = Depends(get_session),
    _auth: Optional[User] = Depends(_dev_or_admin),
):
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Forbidden")
    tables = truncate_all_application_tables(session)
    session.commit()
    return {"ok": True, "tables": tables, "count": len(tables)}
