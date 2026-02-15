from datetime import datetime, timezone
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.user import User
from app.schemas.party import (
    PartyActiveSession,
    PartyCreate,
    PartyDetail,
    PartyMemberAdd,
    PartyMemberRead,
    PartyRead,
)
from app.schemas.session import ActiveSessionRead

router = APIRouter()
logger = logging.getLogger("app.parties")


def to_active_session_read(
    entry: CampaignSession, join_code: str | None
) -> ActiveSessionRead:
    number = entry.sequence_number if entry.sequence_number is not None else entry.number
    return ActiveSessionRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        number=number,
        title=entry.title,
        joinCode=join_code,
        status=entry.status,
        isActive=entry.status == SessionStatus.ACTIVE,
        startedAt=entry.started_at,
        endedAt=entry.ended_at,
        durationSeconds=entry.duration_seconds,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
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
    session.commit()
    session.refresh(party)

    gm_member = PartyMember(
        party_id=party.id,
        user_id=user.id,
        role=RoleMode.GM,
        status=PartyMemberStatus.JOINED,
        created_at=datetime.now(timezone.utc),
    )
    session.add(gm_member)

    player_ids = payload.playerIds or []
    for player_id in player_ids:
        if player_id == user.id:
            continue
        entry = PartyMember(
            party_id=party.id,
            user_id=player_id,
            role=RoleMode.PLAYER,
            status=PartyMemberStatus.INVITED,
            created_at=datetime.now(timezone.utc),
        )
        session.add(entry)

    session.commit()
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
        .where(PartyMember.user_id == user.id)
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
                CampaignSession.status == SessionStatus.ACTIVE,
            )
        ).first()
        join_code = active.join_code if active and party.gm_user_id == user.id else None
        results.append(
            PartyActiveSession(
                party=PartyRead.model_validate(party),
                activeSession=to_active_session_read(active, join_code) if active else None,
            )
        )
    return results


@router.post("/parties/{party_id}/members", response_model=PartyMemberRead)
def add_party_member(
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
    members = session.exec(
        select(PartyMember).where(PartyMember.party_id == party_id)
    ).all()
    return PartyDetail(
        **PartyRead.model_validate(party).model_dump(),
        members=[PartyMemberRead.model_validate(entry) for entry in members],
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
def join_party_invite(
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
def decline_party_invite(
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
def leave_party(
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
