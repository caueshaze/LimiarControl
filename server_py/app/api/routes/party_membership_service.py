from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlmodel import Session

from app.api.routes.party_common import (
    broadcast_party_member_updated,
    get_party_member_or_404,
    get_party_or_404,
    party_member_to_read,
    user_id,
)
from app.models.campaign import RoleMode
from app.models.party_member import PartyMemberStatus
from app.models.user import User
from app.schemas.party import PartyMemberRead

logger = logging.getLogger("app.parties")


def _log_noop(
    *,
    action: str,
    party_id: str,
    current_user_id: str,
    status: PartyMemberStatus,
) -> None:
    logger.info(
        action,
        extra={
            "party_id": party_id,
            "user_id": current_user_id,
            "status_from": status,
            "status_to": status,
        },
    )


async def join_party_invite_service(
    party_id: str,
    user: User,
    session: Session,
) -> PartyMemberRead:
    party = get_party_or_404(party_id, session)
    current_user_id = user_id(user)
    member = get_party_member_or_404(party_id, current_user_id, session)
    previous_status = member.status

    if member.role == RoleMode.GM:
        _log_noop(
            action="Party join ignored for GM",
            party_id=party_id,
            current_user_id=current_user_id,
            status=previous_status,
        )
        return party_member_to_read(member)

    if member.status == PartyMemberStatus.JOINED:
        _log_noop(
            action="Party join idempotent",
            party_id=party_id,
            current_user_id=current_user_id,
            status=previous_status,
        )
        return party_member_to_read(member)

    if member.status != PartyMemberStatus.INVITED:
        raise HTTPException(status_code=400, detail="Invalid member status transition")

    member.status = PartyMemberStatus.JOINED
    session.add(member)
    session.commit()
    session.refresh(member)
    await broadcast_party_member_updated(
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
            "user_id": current_user_id,
            "status_from": previous_status,
            "status_to": member.status,
        },
    )
    return party_member_to_read(member)


async def decline_party_invite_service(
    party_id: str,
    user: User,
    session: Session,
) -> PartyMemberRead:
    party = get_party_or_404(party_id, session)
    current_user_id = user_id(user)
    member = get_party_member_or_404(party_id, current_user_id, session)
    previous_status = member.status

    if member.role == RoleMode.GM:
        _log_noop(
            action="Party decline ignored for GM",
            party_id=party_id,
            current_user_id=current_user_id,
            status=previous_status,
        )
        return party_member_to_read(member)

    if member.status == PartyMemberStatus.DECLINED:
        _log_noop(
            action="Party decline idempotent",
            party_id=party_id,
            current_user_id=current_user_id,
            status=previous_status,
        )
        return party_member_to_read(member)

    if member.status == PartyMemberStatus.JOINED:
        raise HTTPException(status_code=400, detail="Cannot decline after joining")

    if member.status != PartyMemberStatus.INVITED:
        raise HTTPException(status_code=400, detail="Invalid member status transition")

    member.status = PartyMemberStatus.DECLINED
    session.add(member)
    session.commit()
    session.refresh(member)
    await broadcast_party_member_updated(
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
            "user_id": current_user_id,
            "status_from": previous_status,
            "status_to": member.status,
        },
    )
    return party_member_to_read(member)


async def leave_party_service(
    party_id: str,
    user: User,
    session: Session,
) -> PartyMemberRead:
    party = get_party_or_404(party_id, session)
    current_user_id = user_id(user)
    member = get_party_member_or_404(party_id, current_user_id, session)
    previous_status = member.status

    if member.role == RoleMode.GM:
        _log_noop(
            action="Party leave ignored for GM",
            party_id=party_id,
            current_user_id=current_user_id,
            status=previous_status,
        )
        return party_member_to_read(member)

    if member.status == PartyMemberStatus.LEFT:
        _log_noop(
            action="Party leave idempotent",
            party_id=party_id,
            current_user_id=current_user_id,
            status=previous_status,
        )
        return party_member_to_read(member)

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
    await broadcast_party_member_updated(
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
            "user_id": current_user_id,
            "status_from": previous_status,
            "status_to": member.status,
        },
    )
    return party_member_to_read(member)
