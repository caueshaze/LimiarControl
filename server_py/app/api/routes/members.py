from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_gm
from app.api.deprecation import log_deprecated_route
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.user import User
from app.schemas.join import MemberRead, MemberRoleUpdate, MemberSummary, MemberUpdate

router = APIRouter()
DEPRECATION_REMOVAL_DATE = date(2026, 6, 1)


@router.get("/{campaign_id}/members/me", response_model=MemberRead)
def get_member_me(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return MemberRead(
        campaignId=campaign_id,
        displayName=member.display_name,
        roleMode=member.role_mode,
    )


@router.patch("/{campaign_id}/members/me", response_model=MemberRead)
def update_member(
    campaign_id: str,
    payload: MemberUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role_mode = payload.role
    session.add(member)
    session.commit()
    session.refresh(member)
    return MemberRead(
        campaignId=campaign_id,
        displayName=member.display_name,
        roleMode=member.role_mode,
    )


@router.put(
    "/{campaign_id}/members/me/role",
    response_model=MemberRead,
    deprecated=True,
)
def update_member_role_deprecated(
    campaign_id: str,
    payload: MemberRoleUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use PATCH /api/campaigns/{campaign_id}/members/me."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/members/me/role",
        new_path="/api/campaigns/{campaign_id}/members/me",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    return update_member(
        campaign_id,
        MemberUpdate(role=payload.roleMode),
        user,
        session,
    )


@router.get("/{campaign_id}/members", response_model=list[MemberSummary])
def list_members(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entries = session.exec(
        select(CampaignMember).where(CampaignMember.campaign_id == campaign_id)
    ).all()
    return [
        MemberSummary(
            id=entry.id,
            displayName=entry.display_name,
            roleMode=entry.role_mode,
        )
        for entry in entries
    ]
