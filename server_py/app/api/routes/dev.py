from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, text

from app.core.config import settings
from app.db.session import get_session

router = APIRouter()


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

@router.post("/reset")
def reset_database(session: Session = Depends(get_session)):
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Forbidden")
    tables = truncate_all_application_tables(session)
    session.commit()
    return {"ok": True, "tables": tables, "count": len(tables)}
