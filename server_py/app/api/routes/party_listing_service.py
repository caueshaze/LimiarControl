from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.routes.party_common import (
    ensure_campaign_player_member,
    find_active_party_session,
    get_party_member,
    get_party_member_or_404,
    get_party_or_404,
    list_parties_for_user,
    party_id,
    party_member_to_read,
    party_to_read,
    to_active_session_read,
    user_id,
    utcnow,
    broadcast_party_member_updated_safe,
)
from app.models.campaign import Campaign, RoleMode
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.user import User
from app.schemas.party import (
    PartyActiveSession,
    PartyCreate,
    PartyDetail,
    PartyInviteRead,
    PartyMemberAdd,
    PartyMemberRead,
    PartyRead,
)


def ensure_unique_party_name_for_gm(
    name: str,
    gm_user_id: str,
    session: Session,
    *,
    exclude_party_id: str | None = None,
) -> None:
    normalized_name = name.strip()
    if not normalized_name:
        return

    statement = select(Party.id).where(
        Party.gm_user_id == gm_user_id,
        func.lower(Party.name) == normalized_name.lower(),
    )
    if exclude_party_id is not None:
        statement = statement.where(Party.id != exclude_party_id)

    existing_party_id = session.exec(statement).first()
    if existing_party_id:
        raise HTTPException(
            status_code=409,
            detail="You already have a party with this name",
        )


def create_party_service(payload: PartyCreate, user: User, session: Session) -> PartyRead:
    current_user_id = user_id(user)
    campaign = session.get(Campaign, payload.campaignId)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Invalid name")
    ensure_unique_party_name_for_gm(name, current_user_id, session)

    now = utcnow()
    party = Party(
        id=str(uuid4()),
        campaign_id=payload.campaignId,
        gm_user_id=current_user_id,
        name=name,
        created_at=now,
    )
    current_party_id = party_id(party)
    session.add(party)
    session.add(
        PartyMember(
            party_id=current_party_id,
            user_id=current_user_id,
            role=RoleMode.GM,
            status=PartyMemberStatus.JOINED,
            created_at=now,
        )
    )

    player_ids = {player_id for player_id in payload.playerIds if player_id != current_user_id}
    for player_id in player_ids:
        ensure_campaign_player_member(payload.campaignId, player_id, session)
        session.add(
            PartyMember(
                party_id=current_party_id,
                user_id=player_id,
                role=RoleMode.PLAYER,
                status=PartyMemberStatus.INVITED,
                created_at=now,
            )
        )

    session.commit()
    session.refresh(party)
    return party_to_read(party)


def list_my_parties_service(user: User, session: Session) -> list[PartyRead]:
    return [party_to_read(party) for party in list_parties_for_user(user_id(user), session)]


def list_my_parties_active_sessions_service(
    user: User,
    session: Session,
) -> list[PartyActiveSession]:
    results: list[PartyActiveSession] = []
    for party in list_parties_for_user(user_id(user), session):
        active = find_active_party_session(party_id(party), session)
        results.append(
            PartyActiveSession(
                party=party_to_read(party),
                activeSession=to_active_session_read(active) if active else None,
            )
        )
    return results


def list_my_party_invites_service(user: User, session: Session) -> list[PartyInviteRead]:
    invited_entries = list(
        session.exec(
            select(PartyMember).where(
                PartyMember.user_id == user_id(user),
                PartyMember.role == RoleMode.PLAYER,
                PartyMember.status == PartyMemberStatus.INVITED,
            )
        ).all()
    )

    output: list[PartyInviteRead] = []
    for party_member in invited_entries:
        party = session.get(Party, party_member.party_id)
        if party is None:
            continue
        campaign = session.get(Campaign, party.campaign_id)
        if campaign is None:
            continue
        active = session.exec(
            select(CampaignSession).where(
                CampaignSession.party_id == party_id(party),
                CampaignSession.status == SessionStatus.ACTIVE,
            )
        ).first()
        output.append(
            PartyInviteRead(
                party=party_to_read(party),
                campaignName=campaign.name,
                status=party_member.status,
                activeSession=to_active_session_read(active) if active else None,
            )
        )
    return output


async def add_party_member_service(
    party_id_value: str,
    payload: PartyMemberAdd,
    user: User,
    session: Session,
) -> PartyMemberRead:
    current_user_id = user_id(user)
    party = get_party_or_404(party_id_value, session)
    if party.gm_user_id != current_user_id:
        raise HTTPException(status_code=403, detail="GM required")

    if payload.userId != current_user_id:
        ensure_campaign_player_member(party.campaign_id, payload.userId, session)

    existing = get_party_member(party_id_value, payload.userId, session)
    if existing is not None:
        existing.role = payload.role
        existing.status = payload.status
        session.add(existing)
        session.commit()
        session.refresh(existing)
        await broadcast_party_member_updated_safe(
            party.campaign_id,
            party_id_value,
            existing.user_id,
            existing.role,
            existing.status,
        )
        return party_member_to_read(existing)

    entry = PartyMember(
        party_id=party_id_value,
        user_id=payload.userId,
        role=payload.role,
        status=payload.status,
        created_at=utcnow(),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    await broadcast_party_member_updated_safe(
        party.campaign_id,
        party_id_value,
        entry.user_id,
        entry.role,
        entry.status,
    )
    return party_member_to_read(entry)


def get_party_details_service(
    party_id_value: str,
    user: User,
    session: Session,
) -> PartyDetail:
    party = get_party_or_404(party_id_value, session)
    current_user_id = user_id(user)
    is_member = get_party_member(party_id_value, current_user_id, session)
    if party.gm_user_id != current_user_id and is_member is None:
        raise HTTPException(status_code=403, detail="Not a party member")

    members = list(
        session.exec(select(PartyMember).where(PartyMember.party_id == party_id_value)).all()
    )
    formatted_members = [
        party_member_to_read(
            member,
            display_name=member_user.display_name if member_user else None,
            username=member_user.username if member_user else None,
        )
        for member in members
        for member_user in [session.get(User, member.user_id)]
    ]

    return PartyDetail(
        **party_to_read(party).model_dump(),
        members=formatted_members,
    )


def get_my_party_member_service(
    party_id_value: str,
    user: User,
    session: Session,
) -> PartyMemberRead:
    get_party_or_404(party_id_value, session)
    member = get_party_member_or_404(party_id_value, user_id(user), session)
    return party_member_to_read(member)
