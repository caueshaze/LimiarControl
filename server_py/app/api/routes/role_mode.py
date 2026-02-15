from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.models.user import User
from app.schemas.campaign import RoleModeRead, RoleModeUpdate

router = APIRouter()


@router.get("/{campaign_id}/role-mode", response_model=RoleModeRead)
def get_role_mode(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_campaign_member(campaign_id, user, session)
    return {"roleMode": campaign.role_mode}


@router.put("/{campaign_id}/role-mode", response_model=RoleModeRead)
def update_role_mode(
    campaign_id: str,
    payload: RoleModeUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_gm(campaign_id, user, session)
    campaign.role_mode = payload.roleMode
    session.add(campaign)
    session.commit()
    return {"roleMode": campaign.role_mode}
