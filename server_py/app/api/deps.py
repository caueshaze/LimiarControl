from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select

from app.core.auth import decode_jwt
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
from app.models.user import User


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth.split(" ", 1)[1].strip()
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_campaign_member(
    campaign_id: str, user: User, session: Session
) -> tuple[Campaign, CampaignMember]:
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
    return campaign, member


def require_gm(
    campaign_id: str, user: User, session: Session
) -> tuple[Campaign, CampaignMember]:
    campaign, member = require_campaign_member(campaign_id, user, session)
    if member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")
    return campaign, member
