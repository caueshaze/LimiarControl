from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

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
        select(  # type: ignore[call-overload]  # sqlmodel select() typed overloads cap at 4 columns
            Campaign.id,
            Campaign.name,
            Campaign.system,
            Campaign.created_at,
            Campaign.updated_at,
            CampaignMember.role_mode,
        )
        .join(CampaignMember, col(CampaignMember.campaign_id) == Campaign.id)
        .where(CampaignMember.user_id == user.id)
        .order_by(col(Campaign.created_at).desc())
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
