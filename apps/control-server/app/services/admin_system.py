from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.config import settings
from app.models.campaign import Campaign
from app.models.party import Party
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.session_runtime import SessionRuntime
from app.models.user import User
from app.schemas.admin_system import AdminDiagnosticsRead
from app.services.admin_users import (
    _count_rows,
    delete_admin_user,
    get_admin_overview,
    get_admin_user_by_id,
    list_admin_users,
    update_admin_user,
)
from app.services.admin_campaigns import (
    delete_admin_campaign,
    list_admin_campaigns,
)


def get_admin_diagnostics(*, db: Session) -> AdminDiagnosticsRead:
    database_ok = True
    database_message = "ok"

    try:
        db.exec(select(1)).one()
    except Exception as exc:  # pragma: no cover - defensive branch
        database_ok = False
        database_message = str(exc)

    users_total = campaigns_total = parties_total = sessions_total = 0
    active_sessions_total = active_combats_total = 0

    try:
        users_total = _count_rows(db, User)
        campaigns_total = _count_rows(db, Campaign)
        parties_total = _count_rows(db, Party)
        sessions_total = _count_rows(db, CampaignSession)
        active_sessions_total = _count_rows(
            db,
            CampaignSession,
            CampaignSession.status == SessionStatus.ACTIVE,
        )
        active_combats_total = _count_rows(
            db,
            SessionRuntime,
            SessionRuntime.combat_active == True,  # noqa: E712
        )
    except Exception as exc:  # pragma: no cover - defensive branch
        database_ok = False
        database_message = str(exc)

    return AdminDiagnosticsRead(
        appEnv=settings.app_env,
        autoMigrate=settings.auto_migrate,
        utcNow=datetime.now(timezone.utc),
        databaseOk=database_ok,
        databaseMessage=database_message,
        usersTotal=users_total,
        campaignsTotal=campaigns_total,
        partiesTotal=parties_total,
        sessionsTotal=sessions_total,
        activeSessionsTotal=active_sessions_total,
        activeCombatsTotal=active_combats_total,
    )
