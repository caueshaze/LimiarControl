from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.deps import require_system_admin
from app.db.session import get_session
from app.models.campaign import RoleMode, SystemType
from app.models.user import User
from app.schemas.admin_system import (
    AdminCampaignRead,
    AdminDiagnosticsRead,
    AdminOverviewRead,
    AdminUserRead,
    AdminUserUpdate,
)
from app.services.admin_system import (
    delete_admin_user,
    delete_admin_campaign,
    get_admin_diagnostics,
    get_admin_overview,
    list_admin_campaigns,
    list_admin_users,
    update_admin_user,
)

router = APIRouter()


@router.get("/overview", response_model=AdminOverviewRead)
def admin_overview(
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    return get_admin_overview(db=session)


@router.get("/users", response_model=list[AdminUserRead])
def admin_list_users(
    search: str | None = None,
    role: RoleMode | None = None,
    is_system_admin: bool | None = Query(None, alias="is_system_admin"),
    limit: int = Query(100, ge=1, le=500),
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    return list_admin_users(
        db=session,
        search=search,
        role=role,
        is_system_admin=is_system_admin,
        limit=limit,
    )


@router.patch("/users/{user_id}", response_model=AdminUserRead)
def admin_update_user(
    user_id: str,
    payload: AdminUserUpdate,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    return update_admin_user(db=session, user_id=user_id, payload=payload)


@router.delete("/users/{user_id}", status_code=204)
def admin_delete_user(
    user_id: str,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    delete_admin_user(db=session, user_id=user_id)
    return None


@router.get("/campaigns", response_model=list[AdminCampaignRead])
def admin_list_campaigns(
    search: str | None = None,
    system: SystemType | None = None,
    limit: int = Query(100, ge=1, le=500),
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    return list_admin_campaigns(
        db=session,
        search=search,
        system=system,
        limit=limit,
    )


@router.delete("/campaigns/{campaign_id}", status_code=204)
def admin_delete_campaign(
    campaign_id: str,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    delete_admin_campaign(db=session, campaign_id=campaign_id)
    return None


@router.get("/diagnostics", response_model=AdminDiagnosticsRead)
def admin_diagnostics(
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    return get_admin_diagnostics(db=session)
