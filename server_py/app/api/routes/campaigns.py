import random
import string
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode, SystemType
from app.models.campaign_member import CampaignMember
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignOverview,
    CampaignRead,
    CampaignUpdate,
)
from app.services.campaign_catalog import snapshot_campaign_catalog
from app.services.campaign_cleanup import delete_campaign_tree
from app.services.campaign_spells import snapshot_campaign_spells

router = APIRouter()
ENABLED_CAMPAIGN_SYSTEMS = {SystemType.DND5E}


def _ensure_supported_system(system: SystemType) -> None:
    if system not in ENABLED_CAMPAIGN_SYSTEMS:
        raise HTTPException(status_code=400, detail="Campaign system is not enabled")


def _ensure_unique_campaign_name_for_gm(
    name: str,
    gm_user_id: str,
    session: Session,
    *,
    exclude_campaign_id: str | None = None,
) -> None:
    normalized_name = name.strip()
    if not normalized_name:
        return

    statement = (
        select(Campaign.id)
        .join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .where(
            CampaignMember.user_id == gm_user_id,
            CampaignMember.role_mode == RoleMode.GM,
            func.lower(Campaign.name) == normalized_name.lower(),
        )
    )
    if exclude_campaign_id is not None:
        statement = statement.where(Campaign.id != exclude_campaign_id)

    existing_campaign_id = session.exec(statement).first()
    if existing_campaign_id:
        raise HTTPException(
            status_code=409,
            detail="You already have a campaign with this name",
        )


@router.get("", response_model=List[CampaignRead])
def list_campaigns(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    statement = (
        select(
            Campaign.id,
            Campaign.name,
            Campaign.system,
            Campaign.created_at,
            Campaign.updated_at,
            CampaignMember.role_mode,
        )
        .join(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .where(CampaignMember.user_id == user.id)
        .order_by(Campaign.created_at.desc())
    )
    entries = session.exec(statement).all()
    return [
        CampaignRead(
            id=campaign_id,
            name=name,
            systemType=system,
            roleMode=role_mode,
            createdAt=created_at,
            updatedAt=updated_at,
        )
        for campaign_id, name, system, created_at, updated_at, role_mode in entries
    ]


@router.get("/{campaign_id}/overview", response_model=CampaignOverview)
def campaign_overview(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign_entry = session.exec(
        select(
            Campaign.id,
            Campaign.name,
            Campaign.system,
            Campaign.role_mode,
            Campaign.created_at,
            Campaign.updated_at,
        ).where(Campaign.id == campaign_id)
    ).first()
    if not campaign_entry:
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
    (
        campaign_entry_id,
        campaign_name,
        campaign_system,
        campaign_role_mode,
        campaign_created_at,
        campaign_updated_at,
    ) = campaign_entry
    return CampaignOverview(
        id=campaign_entry_id,
        name=campaign_name,
        systemType=campaign_system,
        roleMode=campaign_role_mode,
        createdAt=campaign_created_at,
        updatedAt=campaign_updated_at,
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
    campaign_name = payload.name.strip()
    _ensure_supported_system(payload.system)
    _ensure_unique_campaign_name_for_gm(campaign_name, user.id, session)
    campaign = Campaign(
        id=str(uuid4()),
        name=campaign_name,
        system=payload.system,
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
    session.flush()
    snapshot_campaign_catalog(campaign=campaign, db=session, commit=False)
    snapshot_campaign_spells(campaign=campaign, db=session, commit=False)
    session.commit()
    session.refresh(campaign)
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
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
        campaign_name = payload.name.strip()
        _ensure_unique_campaign_name_for_gm(
            campaign_name,
            user.id,
            session,
            exclude_campaign_id=campaign.id,
        )
        campaign.name = campaign_name
    if payload.system is not None:
        _ensure_supported_system(payload.system)
        campaign.system = payload.system
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
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
    delete_campaign_tree(session, campaign)
    session.commit()
    return None
