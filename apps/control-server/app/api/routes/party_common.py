from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.user import User
from app.schemas.party import PartyMemberRead, PartyRead
from app.schemas.session import ActiveSessionRead
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version
from app.models.campaign import RoleMode

logger = logging.getLogger("app.parties")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def require_identifier(value: str | None, detail: str) -> str:
    if value is None:
        raise HTTPException(status_code=500, detail=detail)
    return value


def user_id(user: User) -> str:
    return require_identifier(user.id, "Authenticated user is missing an id")


def party_id(party: Party) -> str:
    return require_identifier(party.id, "Party is missing an id")


def party_to_read(party: Party) -> PartyRead:
    return PartyRead(
        id=party_id(party),
        campaignId=party.campaign_id,
        gmUserId=party.gm_user_id,
        name=party.name,
        createdAt=party.created_at,
    )


def party_member_to_read(
    member: PartyMember,
    *,
    display_name: str | None = None,
    username: str | None = None,
) -> PartyMemberRead:
    return PartyMemberRead(
        userId=member.user_id,
        role=member.role,
        status=member.status,
        createdAt=member.created_at,
        displayName=display_name,
        username=username,
    )


def to_active_session_read(entry: CampaignSession) -> ActiveSessionRead:
    number = entry.sequence_number if entry.sequence_number is not None else entry.number
    return ActiveSessionRead(
        id=require_identifier(entry.id, "Session is missing an id"),
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        number=number,
        title=entry.title,
        status=entry.status,
        isActive=entry.status == SessionStatus.ACTIVE,
        startedAt=entry.started_at,
        endedAt=entry.ended_at,
        durationSeconds=entry.duration_seconds,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


async def broadcast_party_member_updated(
    campaign_id: str,
    party_id_value: str,
    member_user_id: str,
    role: RoleMode,
    status: PartyMemberStatus,
) -> None:
    await centrifugo.publish(
        campaign_channel(campaign_id),
        build_event(
            "party_member_updated",
            {
                "campaignId": campaign_id,
                "partyId": party_id_value,
                "userId": member_user_id,
                "role": role.value,
                "status": status.value,
            },
            version=event_version(),
        ),
    )


async def broadcast_party_member_updated_safe(
    campaign_id: str,
    party_id_value: str,
    member_user_id: str,
    role: RoleMode,
    status: PartyMemberStatus,
) -> None:
    try:
        await broadcast_party_member_updated(
            campaign_id,
            party_id_value,
            member_user_id,
            role,
            status,
        )
    except Exception:
        logger.exception(
            "Failed to publish party_member_updated",
            extra={
                "campaign_id": campaign_id,
                "party_id": party_id_value,
                "user_id": member_user_id,
                "role": role.value,
                "status": status.value,
            },
        )


def ensure_campaign_player_member(
    campaign_id: str,
    player_user_id: str,
    session: Session,
) -> None:
    user = session.get(User, player_user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == player_user_id,
        )
    ).first()
    if member is not None:
        if not member.display_name:
            member.display_name = user.display_name or user.username
            session.add(member)
        return

    session.add(
        CampaignMember(
            id=str(uuid4()),
            campaign_id=campaign_id,
            user_id=player_user_id,
            display_name=user.display_name or user.username,
            role_mode=RoleMode.PLAYER,
            created_at=utcnow(),
            updated_at=None,
        )
    )


def get_party_or_404(party_id_value: str, session: Session) -> Party:
    party = session.get(Party, party_id_value)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")
    return party


def get_party_member(
    party_id_value: str,
    member_user_id: str,
    session: Session,
) -> PartyMember | None:
    return session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id_value,
            PartyMember.user_id == member_user_id,
        )
    ).first()


def get_party_member_or_404(
    party_id_value: str,
    member_user_id: str,
    session: Session,
) -> PartyMember:
    member = get_party_member(party_id_value, member_user_id, session)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


def list_member_party_ids(member_user_id: str, session: Session) -> list[str]:
    party_ids = session.exec(
        select(PartyMember.party_id).where(
            PartyMember.user_id == member_user_id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).all()
    return list(party_ids)


def list_parties_for_user(member_user_id: str, session: Session) -> list[Party]:
    parties_as_gm = list(
        session.exec(select(Party).where(Party.gm_user_id == member_user_id)).all()
    )
    parties_by_id: dict[str, Party] = {party_id(party): party for party in parties_as_gm}
    for member_party_id in list_member_party_ids(member_user_id, session):
        party = session.get(Party, member_party_id)
        if party is not None:
            parties_by_id[party_id(party)] = party
    return list(parties_by_id.values())


def find_active_party_session(
    party_id_value: str,
    session: Session,
) -> CampaignSession | None:
    return session.exec(
        select(CampaignSession).where(
            CampaignSession.party_id == party_id_value,
            (
                (CampaignSession.status == SessionStatus.ACTIVE)
                | (CampaignSession.status == SessionStatus.LOBBY)
            ),
        )
    ).first()
