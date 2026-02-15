from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
from app.models.user import User
from app.schemas.campaign import CampaignRead

router = APIRouter()


@router.get("/campaigns", response_model=List[CampaignRead])
def list_my_campaigns(
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
