from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.auth import encode_jwt
from app.core.config import settings
from app.db.session import get_session
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.user import User

import time

router = APIRouter()


class ConnectionTokenResponse(BaseModel):
    token: str


class SubscribeRequest(BaseModel):
    channel: str


class SubscribeResponse(BaseModel):
    token: str


@router.post("/centrifugo/connection-token", response_model=ConnectionTokenResponse)
def connection_token(user: User = Depends(get_current_user)):
    payload = {
        "sub": user.id,
        "exp": int(time.time()) + 60 * 60 * 24,
        "info": {
            "displayName": user.display_name or user.username,
            "username": user.username,
        },
    }
    token = encode_jwt(payload, settings.centrifugo_token_secret)
    return ConnectionTokenResponse(token=token)


@router.post("/centrifugo/subscribe", response_model=SubscribeResponse)
def subscribe_token(
    body: SubscribeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    channel = body.channel
    parts = channel.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid channel format")

    namespace, resource_id = parts

    if namespace == "campaign":
        member = _validate_campaign_access(session, resource_id, user.id)
    elif namespace == "session":
        member = _validate_session_access(session, resource_id, user.id)
    else:
        raise HTTPException(status_code=400, detail="Unknown channel namespace")

    display_name = member.display_name if member else (user.display_name or user.username)

    token = encode_jwt(
        {
            "sub": user.id,
            "channel": channel,
            "exp": int(time.time()) + 60 * 60 * 24,
            "info": {
                "displayName": display_name,
                "username": user.username,
            },
        },
        settings.centrifugo_token_secret,
    )
    return SubscribeResponse(token=token)


def _validate_campaign_access(
    session: Session,
    campaign_id: str,
    user_id: str,
) -> CampaignMember:
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    return member


def _validate_session_access(
    session: Session,
    session_id: str,
    user_id: str,
) -> CampaignMember:
    entry = session.exec(
        select(CampaignSession).where(CampaignSession.id == session_id)
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status not in (SessionStatus.ACTIVE, SessionStatus.LOBBY):
        raise HTTPException(status_code=403, detail="Session is not active")

    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        if party.gm_user_id != user_id:
            party_member = session.exec(
                select(PartyMember).where(
                    PartyMember.party_id == party.id,
                    PartyMember.user_id == user_id,
                )
            ).first()
            if not party_member or party_member.status != PartyMemberStatus.JOINED:
                raise HTTPException(status_code=403, detail="Party join required")

    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user_id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    return member
