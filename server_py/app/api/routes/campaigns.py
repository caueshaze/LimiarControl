import random
import string
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignJoinRequest,
    CampaignJoinResponse,
    CampaignOverview,
    CampaignRead,
    CampaignUpdate,
)

router = APIRouter()
JOIN_CODE_CHARS = string.ascii_uppercase + string.digits


def generate_join_code() -> str:
    length = random.randint(6, 8)
    return "".join(random.choice(JOIN_CODE_CHARS) for _ in range(length))


def ensure_unique_join_code(session: Session) -> str:
    for _ in range(20):
        code = generate_join_code()
        existing = session.exec(select(Campaign).where(Campaign.join_code == code)).first()
        if not existing:
            return code
    return f"{uuid4().hex[:8].upper()}"


@router.get("", response_model=List[CampaignRead])
def list_campaigns(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    statement = (
        select(Campaign, CampaignMember)
        .join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .where(CampaignMember.user_id == user.id)
        .order_by(Campaign.created_at.desc())
    )
    entries = session.exec(statement).all()
    return [
        CampaignRead(
            id=campaign.id,
            name=campaign.name,
            joinCode=campaign.join_code if member.role_mode == RoleMode.GM else None,
            systemType=campaign.system,
            roleMode=member.role_mode,
            createdAt=campaign.created_at,
            updatedAt=campaign.updated_at,
        )
        for campaign, member in entries
    ]


@router.get("/{campaign_id}/overview", response_model=CampaignOverview)
def campaign_overview(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    gm_member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.role_mode == RoleMode.GM,
        )
    ).first()
    return CampaignOverview(
        id=campaign.id,
        name=campaign.name,
        joinCode=campaign.join_code if member.role_mode == RoleMode.GM else None,
        systemType=campaign.system,
        roleMode=campaign.role_mode,
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at,
        gmName=gm_member.display_name if gm_member else None,
    )


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Invalid payload")
    campaign = Campaign(
        id=str(uuid4()),
        name=payload.name.strip(),
        system=payload.system,
        join_code=ensure_unique_join_code(session),
    )
    member = CampaignMember(
        id=str(uuid4()),
        campaign_id=campaign.id,
        user_id=user.id,
        display_name=user.display_name or user.username,
        role_mode=campaign.role_mode,
    )
    session.add(campaign)
    session.add(member)
    session.commit()
    session.refresh(campaign)
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
        joinCode=campaign.join_code,
        systemType=campaign.system,
        roleMode=campaign.role_mode,
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at,
    )


@router.put("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_gm(campaign_id, user, session)
    if payload.name is not None:
        if not payload.name.strip():
            raise HTTPException(status_code=400, detail="Invalid payload")
        campaign.name = payload.name.strip()
    if payload.system is not None:
        campaign.system = payload.system
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
        joinCode=campaign.join_code if _member.role_mode == RoleMode.GM else None,
        systemType=campaign.system,
        roleMode=campaign.role_mode,
        createdAt=campaign.created_at,
        updatedAt=campaign.updated_at,
    )


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_gm(campaign_id, user, session)
    session.delete(campaign)
    session.commit()
    return None


@router.post("/join-by-code", response_model=CampaignJoinResponse)
def join_campaign_by_code(
    payload: CampaignJoinRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    join_code = payload.joinCode.strip().upper()
    if not join_code:
        raise HTTPException(status_code=400, detail="Invalid payload")
    campaign = session.exec(select(Campaign).where(Campaign.join_code == join_code)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Join code not found")
    gm_member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.role_mode == RoleMode.GM,
        )
    ).first()
    gm_name = gm_member.display_name if gm_member else None
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign.id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if member:
        if user.display_name:
            member.display_name = user.display_name
        session.add(member)
        session.commit()
        session.refresh(member)
        return CampaignJoinResponse(
            campaignId=campaign.id,
            campaignName=campaign.name,
            gmName=gm_name,
            memberId=member.id,
            displayName=member.display_name,
            roleMode=member.role_mode,
        )
    member = CampaignMember(
        id=str(uuid4()),
        campaign_id=campaign.id,
        user_id=user.id,
        display_name=user.display_name or user.username,
        role_mode=RoleMode.PLAYER,
    )
    session.add(member)
    session.commit()
    session.refresh(member)
    return CampaignJoinResponse(
        campaignId=campaign.id,
        campaignName=campaign.name,
        gmName=gm_name,
        memberId=member.id,
        displayName=member.display_name,
        roleMode=member.role_mode,
    )
