from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select

from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
from app.models.party_member import PartyMember
from app.models.session import Session, SessionStatus
from app.models.user import User
from app.schemas.session import ActiveSessionRead, SessionRead
from app.services.centrifugo import centrifugo
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)
from ._shared import (
    resolve_party_id_for_campaign,
    to_session_read,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def require_identifier(value: str | None, detail: str) -> str:
    if value is None:
        raise HTTPException(status_code=500, detail=detail)
    return value


def require_campaign_member_role(
    campaign_id: str,
    user: User,
    session: DbSession,
) -> tuple[Campaign, CampaignMember]:
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if member is None:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    return campaign, member


def get_open_campaign_session(
    *,
    campaign_id: str,
    party_id: str | None,
    session: DbSession,
) -> Session | None:
    if party_id is not None:
        return session.exec(
            select(Session).where(
                Session.party_id == party_id,
                (
                    (Session.status == SessionStatus.ACTIVE)
                    | (Session.status == SessionStatus.LOBBY)
                ),
            )
        ).first()
    return session.exec(
        select(Session).where(
            Session.campaign_id == campaign_id,
            (
                (Session.status == SessionStatus.ACTIVE)
                | (Session.status == SessionStatus.LOBBY)
            ),
        )
    ).first()


def get_active_session_service(
    campaign_id: str,
    user: User,
    session: DbSession,
) -> ActiveSessionRead:
    _campaign, _member = require_campaign_member_role(campaign_id, user, session)
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    active = get_open_campaign_session(
        campaign_id=campaign_id,
        party_id=party_id,
        session=session,
    )
    if active is None:
        raise HTTPException(status_code=404, detail="No active session")
    return ActiveSessionRead(**to_session_read(active).model_dump())


def list_sessions_service(
    campaign_id: str,
    user: User,
    session: DbSession,
) -> list[SessionRead]:
    _campaign, _member = require_campaign_member_role(campaign_id, user, session)
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        entries = list(
            session.exec(select(Session).where(Session.party_id == party_id)).all()
        )
        entries.sort(
            key=lambda entry: entry.sequence_number if entry.sequence_number is not None else 0,
            reverse=True,
        )
    else:
        entries = list(
            session.exec(select(Session).where(Session.campaign_id == campaign_id)).all()
        )
        entries.sort(key=lambda entry: entry.number, reverse=True)
    return [to_session_read(entry) for entry in entries]


async def publish_session_closed(
    *,
    existing_active: Session,
    campaign_id: str,
    ended_at: datetime,
) -> None:
    payload = {
        "sessionId": require_identifier(existing_active.id, "Session is missing an id"),
        "campaignId": campaign_id,
        "partyId": existing_active.party_id,
        "endedAt": ended_at.isoformat(),
    }
    version = event_version(ended_at)
    event = build_event("session_closed", payload, version=version)
    await centrifugo.publish(
        session_channel(require_identifier(existing_active.id, "Session is missing an id")),
        event,
    )
    await centrifugo.publish(campaign_channel(campaign_id), event)


async def publish_session_started(
    *,
    entry: Session,
    campaign_id: str,
    party_id: str,
    started_at: datetime,
) -> None:
    payload = {
        "sessionId": require_identifier(entry.id, "Session is missing an id"),
        "campaignId": campaign_id,
        "partyId": party_id,
        "title": entry.title,
        "startedAt": started_at.isoformat(),
    }
    version = event_version(entry.started_at or started_at)
    event = build_event("session_started", payload, version=version)
    await centrifugo.publish(
        session_channel(require_identifier(entry.id, "Session is missing an id")),
        event,
    )
    await centrifugo.publish(campaign_channel(campaign_id), event)


async def publish_session_lobby(
    *,
    entry: Session,
    campaign_id: str,
    party_id: str,
    expected_list: list[dict[str, str]],
) -> None:
    await centrifugo.publish(
        campaign_channel(campaign_id),
        build_event(
            "session_lobby",
            {
                "sessionId": require_identifier(entry.id, "Session is missing an id"),
                "campaignId": campaign_id,
                "partyId": party_id,
                "title": entry.title,
                "expectedPlayers": expected_list,
                "readyUserIds": [],
                "readyCount": 0,
                "totalCount": len(expected_list),
            },
            version=event_version(entry.created_at),
        ),
    )


def build_expected_players(
    player_members: Sequence[PartyMember],
    session: DbSession,
) -> dict[str, str]:
    expected: dict[str, str] = {}
    for player_member in player_members:
        user = session.get(User, player_member.user_id)
        expected[player_member.user_id] = (
            (user.display_name or user.username or player_member.user_id)
            if user
            else player_member.user_id
        )
    return expected
