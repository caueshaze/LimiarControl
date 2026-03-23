from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
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
from app.api.routes.party_listing_service import (
    add_party_member_service,
    create_party_service,
    get_my_party_member_service,
    get_party_details_service,
    list_my_parties_active_sessions_service,
    list_my_parties_service,
    list_my_party_invites_service,
)
from app.api.routes.party_membership_service import (
    decline_party_invite_service,
    join_party_invite_service,
    leave_party_service,
)

router = APIRouter()


@router.post("/parties", response_model=PartyRead)
def create_party(
    payload: PartyCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(payload.campaignId, user, session)
    return create_party_service(payload, user, session)


@router.get("/me/parties", response_model=list[PartyRead])
def list_my_parties(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return list_my_parties_service(user, session)


@router.get("/me/parties/active-sessions", response_model=list[PartyActiveSession])
def list_my_parties_active_sessions(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return list_my_parties_active_sessions_service(user, session)


@router.get("/me/party-invites", response_model=list[PartyInviteRead])
def list_my_party_invites(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return list_my_party_invites_service(user, session)


@router.post("/parties/{party_id}/members", response_model=PartyMemberRead)
async def add_party_member(
    party_id: str,
    payload: PartyMemberAdd,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return await add_party_member_service(party_id, payload, user, session)


@router.get("/parties/{party_id}", response_model=PartyDetail)
def get_party_details(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return get_party_details_service(party_id, user, session)


@router.get("/parties/{party_id}/members/me", response_model=PartyMemberRead)
def get_my_party_member(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return get_my_party_member_service(party_id, user, session)


@router.post("/parties/{party_id}/members/me/join", response_model=PartyMemberRead)
async def join_party_invite(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return await join_party_invite_service(party_id, user, session)


@router.post("/parties/{party_id}/members/me/decline", response_model=PartyMemberRead)
async def decline_party_invite(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return await decline_party_invite_service(party_id, user, session)


@router.post("/parties/{party_id}/members/me/leave", response_model=PartyMemberRead)
async def leave_party(
    party_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return await leave_party_service(party_id, user, session)
