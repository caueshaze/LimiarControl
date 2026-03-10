from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version
from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
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
from app.schemas.session import ActiveSessionRead

router = APIRouter()
logger = logging.getLogger("app.parties")


async def _broadcast_party_member_updated(
    campaign_id: str,
    party_id: str,
    user_id: str,
    role: RoleMode,
    status: PartyMemberStatus,
) -> None:
    await centrifugo.publish(
        campaign_channel(campaign_id),
        build_event(
            "party_member_updated",
            {
                "campaignId": campaign_id,
                "partyId": party_id,
                "userId": user_id,
                "role": role.value if hasattr(role, "value") else str(role),
                "status": status.value if hasattr(status, "value") else str(status),
            },
            version=event_version(),
        ),
    )


def to_active_session_read(
    entry: CampaignSession
) -> ActiveSessionRead:
    number = entry.sequence_number if entry.sequence_number is not None else entry.number
    return ActiveSessionRead(
        id=entry.id,
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


def ensure_campaign_player_member(
    campaign_id: str,
    user_id: str,
    session: Session,
):
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.user_id == user_id,
        )
    ).first()
    if member:
        if not member.display_name:
            member.display_name = user.display_name or user.username
            session.add(member)
        return

    session.add(
        CampaignMember(
            id=str(uuid4()),
            campaign_id=campaign_id,
            user_id=user_id,
            display_name=user.display_name or user.username,
            role_mode=RoleMode.PLAYER,
        )
    )


@router.post("/parties", response_model=PartyRead)
def create_party(
    payload: PartyCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign = session.exec(
        select(Campaign).where(Campaign.id == payload.campaignId)
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    require_gm(payload.campaignId, user, session)
    existing_party = session.exec(
        select(Party).where(Party.campaign_id == payload.campaignId)
    ).first()
    if existing_party:
        if existing_party.gm_user_id != user.id:
            raise HTTPException(status_code=409, detail="Party already exists for campaign")

        gm_member = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == existing_party.id,
                PartyMember.user_id == user.id,
            )
        ).first()
        if not gm_member:
            session.add(
                PartyMember(
                    party_id=existing_party.id,
                    user_id=user.id,
                    role=RoleMode.GM,
                    status=PartyMemberStatus.JOINED,
                    created_at=datetime.now(timezone.utc),
                )
            )

        player_ids = {
            player_id for player_id in (payload.playerIds or []) if player_id != user.id
        }
        for player_id in player_ids:
            ensure_campaign_player_member(payload.campaignId, player_id, session)
            entry = session.exec(
                select(PartyMember).where(
                    PartyMember.party_id == existing_party.id,
                    PartyMember.user_id == player_id,
                )
            ).first()
            if entry:
                if entry.role != RoleMode.GM:
                    entry.role = RoleMode.PLAYER
                    entry.status = PartyMemberStatus.INVITED
                    session.add(entry)
                continue
            session.add(
                PartyMember(
                    party_id=existing_party.id,
                    user_id=player_id,
                    role=RoleMode.PLAYER,
                    status=PartyMemberStatus.INVITED,
                    created_at=datetime.now(timezone.utc),
                )
            )

        session.commit()
        session.refresh(existing_party)
        return PartyRead.model_validate(existing_party)

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Invalid name")

    party = Party(
        id=str(uuid4()),
        campaign_id=payload.campaignId,
        gm_user_id=user.id,
        name=name,
        created_at=datetime.now(timezone.utc),
    )
    session.add(party)

    gm_member = PartyMember(
        party_id=party.id,
        user_id=user.id,
        role=RoleMode.GM,
        status=PartyMemberStatus.JOINED,
        created_at=datetime.now(timezone.utc),
    )
    session.add(gm_member)

    player_ids = {
        player_id for player_id in (payload.playerIds or []) if player_id != user.id
    }
    for player_id in player_ids:
        ensure_campaign_player_member(payload.campaignId, player_id, session)
        entry = PartyMember(
            party_id=party.id,
            user_id=player_id,
            role=RoleMode.PLAYER,
            status=PartyMemberStatus.INVITED,
            created_at=datetime.now(timezone.utc),
        )
        session.add(entry)

    session.commit()
    session.refresh(party)
    return PartyRead.model_validate(party)


@router.get("/me/parties", response_model=list[PartyRead])
def list_my_parties(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    parties_as_gm = session.exec(
        select(Party).where(Party.gm_user_id == user.id)
    ).all()
    parties_as_member = session.exec(
        select(Party)
        .join(PartyMember, PartyMember.party_id == Party.id)
        .where(
            PartyMember.user_id == user.id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).all()
    by_id = {party.id: party for party in parties_as_gm + parties_as_member}
    return [PartyRead.model_validate(party) for party in by_id.values()]


@router.get("/me/parties/active-sessions", response_model=list[PartyActiveSession])
def list_my_parties_active_sessions(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    parties_as_gm = session.exec(
        select(Party).where(Party.gm_user_id == user.id)
    ).all()
    parties_as_member = session.exec(
        select(Party)
        .join(PartyMember, PartyMember.party_id == Party.id)
        .where(
            PartyMember.user_id == user.id,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).all()
    by_id = {party.id: party for party in parties_as_gm + parties_as_member}
    results: list[PartyActiveSession] = []
    for party in by_id.values():
        active = session.exec(
            select(CampaignSession).where(
                CampaignSession.party_id == party.id,
                CampaignSession.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
            )
        ).first()
        results.append(
            PartyActiveSession(
                party=PartyRead.model_validate(party),
                activeSession=to_active_session_read(active) if active else None,
            )
        )
    return results


@router.get("/me/party-invites", response_model=list[PartyInviteRead])
def list_my_party_invites(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    invited_entries = session.exec(
        select(PartyMember, Party, Campaign)
        .join(Party, PartyMember.party_id == Party.id)
        .join(Campaign, Party.campaign_id == Campaign.id)
        .where(
            PartyMember.user_id == user.id,
            PartyMember.role == RoleMode.PLAYER,
            PartyMember.status == PartyMemberStatus.INVITED,
        )
    ).all()

    output: list[PartyInviteRead] = []
    for party_member, party, campaign in invited_entries:
        active = session.exec(
            select(CampaignSession).where(
                CampaignSession.party_id == party.id,
                CampaignSession.status == SessionStatus.ACTIVE,
            )
        ).first()
        output.append(
            PartyInviteRead(
                party=PartyRead.model_validate(party),
                campaignName=campaign.name,
                status=party_member.status,
                activeSession=to_active_session_read(active) if active else None,
            )
        )
    return output


@router.post("/parties/{party_id}/members", response_model=PartyMemberRead)
async def add_party_member(
    party_id: str,
    payload: PartyMemberAdd,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="GM required")

    if payload.userId != user.id:
        ensure_campaign_player_member(party.campaign_id, payload.userId, session)

    existing = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == payload.userId,
        )
    ).first()
    if existing:
        existing.role = payload.role
        existing.status = payload.status
        session.add(existing)
        session.commit()
        session.refresh(existing)
        await _broadcast_party_member_updated(
            party.campaign_id,
            party_id,
            existing.user_id,
            existing.role,
            existing.status,
        )
        return PartyMemberRead.model_validate(existing)

    entry = PartyMember(
        party_id=party_id,
        user_id=payload.userId,
        role=payload.role,
        status=payload.status,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    await _broadcast_party_member_updated(
        party.campaign_id,
        party_id,
        entry.user_id,
        entry.role,
        entry.status,
    )
    return PartyMemberRead.model_validate(entry)


@router.get("/parties/{party_id}", response_model=PartyDetail)
def get_party_details(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    is_member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
        )
    ).first()
    if party.gm_user_id != user.id and not is_member:
        raise HTTPException(status_code=403, detail="Not a party member")
    members_query = (
        select(PartyMember, User)
        .join(User, PartyMember.user_id == User.id)
        .where(PartyMember.party_id == party_id)
    )
    results = session.exec(members_query).all()
    
    formatted_members = []
    for member, member_user in results:
        data = member.model_dump()
        data["displayName"] = member_user.display_name
        data["username"] = member_user.username
        formatted_members.append(PartyMemberRead(**data))

    return PartyDetail(
        **PartyRead.model_validate(party).model_dump(),
        members=formatted_members,
    )


@router.get("/parties/{party_id}/members/me", response_model=PartyMemberRead)
def get_my_party_member(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return PartyMemberRead.model_validate(member)


@router.post("/parties/{party_id}/members/me/join", response_model=PartyMemberRead)
async def join_party_invite(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    previous_status = member.status
    if member.role == RoleMode.GM:
        logger.info(
            "Party join ignored for GM",
            extra={
                "party_id": party_id,
                "user_id": user.id,
                "status_from": previous_status,
                "status_to": previous_status,
            },
        )
        return PartyMemberRead.model_validate(member)

    if member.status == PartyMemberStatus.JOINED:
        logger.info(
            "Party join idempotent",
            extra={
                "party_id": party_id,
                "user_id": user.id,
                "status_from": previous_status,
                "status_to": previous_status,
            },
        )
        return PartyMemberRead.model_validate(member)

    if member.status != PartyMemberStatus.INVITED:
        raise HTTPException(status_code=400, detail="Invalid member status transition")

    member.status = PartyMemberStatus.JOINED
    session.add(member)
    session.commit()
    session.refresh(member)
    await _broadcast_party_member_updated(
        party.campaign_id,
        party_id,
        member.user_id,
        member.role,
        member.status,
    )
    logger.info(
        "Party invite accepted",
        extra={
            "party_id": party_id,
            "user_id": user.id,
            "status_from": previous_status,
            "status_to": member.status,
        },
    )
    return PartyMemberRead.model_validate(member)


@router.post("/parties/{party_id}/members/me/decline", response_model=PartyMemberRead)
async def decline_party_invite(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    previous_status = member.status
    if member.role == RoleMode.GM:
        logger.info(
            "Party decline ignored for GM",
            extra={
                "party_id": party_id,
                "user_id": user.id,
                "status_from": previous_status,
                "status_to": previous_status,
            },
        )
        return PartyMemberRead.model_validate(member)

    if member.status == PartyMemberStatus.DECLINED:
        logger.info(
            "Party decline idempotent",
            extra={
                "party_id": party_id,
                "user_id": user.id,
                "status_from": previous_status,
                "status_to": previous_status,
            },
        )
        return PartyMemberRead.model_validate(member)

    if member.status == PartyMemberStatus.JOINED:
        raise HTTPException(status_code=400, detail="Cannot decline after joining")

    if member.status != PartyMemberStatus.INVITED:
        raise HTTPException(status_code=400, detail="Invalid member status transition")

    member.status = PartyMemberStatus.DECLINED
    session.add(member)
    session.commit()
    session.refresh(member)
    await _broadcast_party_member_updated(
        party.campaign_id,
        party_id,
        member.user_id,
        member.role,
        member.status,
    )
    logger.info(
        "Party invite declined",
        extra={
            "party_id": party_id,
            "user_id": user.id,
            "status_from": previous_status,
            "status_to": member.status,
        },
    )
    return PartyMemberRead.model_validate(member)


@router.post("/parties/{party_id}/members/me/leave", response_model=PartyMemberRead)
async def leave_party(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    previous_status = member.status
    if member.role == RoleMode.GM:
        logger.info(
            "Party leave ignored for GM",
            extra={
                "party_id": party_id,
                "user_id": user.id,
                "status_from": previous_status,
                "status_to": previous_status,
            },
        )
        return PartyMemberRead.model_validate(member)

    if member.status == PartyMemberStatus.LEFT:
        logger.info(
            "Party leave idempotent",
            extra={
                "party_id": party_id,
                "user_id": user.id,
                "status_from": previous_status,
                "status_to": previous_status,
            },
        )
        return PartyMemberRead.model_validate(member)

    if member.status == PartyMemberStatus.INVITED:
        raise HTTPException(status_code=400, detail="Cannot leave before joining")

    if member.status == PartyMemberStatus.DECLINED:
        raise HTTPException(status_code=400, detail="Cannot leave after declining")

    if member.status != PartyMemberStatus.JOINED:
        raise HTTPException(status_code=400, detail="Invalid member status transition")

    member.status = PartyMemberStatus.LEFT
    session.add(member)
    session.commit()
    session.refresh(member)
    await _broadcast_party_member_updated(
        party.campaign_id,
        party_id,
        member.user_id,
        member.role,
        member.status,
    )
    logger.info(
        "Party left",
        extra={
            "party_id": party_id,
            "user_id": user.id,
            "status_from": previous_status,
            "status_to": member.status,
        },
    )
    return PartyMemberRead.model_validate(member)
