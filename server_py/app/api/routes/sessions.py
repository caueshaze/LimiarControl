import random
import string
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session as DbSession, select, func
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_current_user
from app.api.deprecation import log_deprecated_route
from app.api.ws import campaign_room_registry, parse_expression, room_registry, to_roll_read
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.purchase_event import PurchaseEvent
from app.models.roll_event import RollEvent
from app.models.session import Session, SessionStatus
from app.models.session_state import SessionState
from app.models.user import User
from app.schemas.inventory import InventoryBuy, InventoryRead
from app.schemas.item import ItemRead
from app.schemas.roll_event import RollDice, RollEventRead
from app.schemas.session import (
    ActiveSessionRead,
    ActivityEvent,
    ManualRollRequest,
    PurchaseActivityEvent,
    RollActivityEvent,
    SessionActivateRequest,
    SessionCommandRequest,
    SessionCreateByParty,
    SessionRead,
)

router = APIRouter()

# In-memory lobby: session_id -> set of user_ids that clicked "Join"
_lobby_ready: dict[str, set[str]] = {}
# session_id -> {user_id: display_name} for expected players
_lobby_expected: dict[str, dict[str, str]] = {}


def to_session_read(entry: Session) -> SessionRead:
    number = entry.sequence_number if entry.sequence_number is not None else entry.number
    return SessionRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        number=number,
        title=entry.title,
        status=entry.status,
        isActive=entry.status in (SessionStatus.ACTIVE, SessionStatus.LOBBY),
        startedAt=entry.started_at,
        endedAt=entry.ended_at,
        durationSeconds=entry.duration_seconds,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def resolve_party_id_for_campaign(
    campaign_id: str,
    session: DbSession,
) -> str | None:
    parties = session.exec(
        select(Party).where(Party.campaign_id == campaign_id)
    ).all()
    if len(parties) == 1:
        return parties[0].id
    if len(parties) > 1:
        raise HTTPException(
            status_code=409,
            detail="Multiple parties found for campaign; specify party explicitly",
        )
    return None


def require_party_member_or_gm(
    party_id: str,
    user,
    session: DbSession,
) -> Party:
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id == user.id:
        return party
    member = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party_id,
            PartyMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a party member")
    return party


def require_party_gm(
    party_id: str,
    user,
    session: DbSession,
) -> Party:
    party = session.exec(select(Party).where(Party.id == party_id)).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    if party.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="GM required")
    return party


def to_roll_read(entry: RollEvent) -> RollEventRead:
    return RollEventRead(
        id=entry.id,
        campaignId=entry.campaign_id or "",
        sessionId=entry.session_id,
        userId=entry.user_id,
        authorName=entry.author_name,
        roleMode=entry.role_mode,
        label=entry.label,
        expression=entry.expression,
        dice=RollDice(count=entry.count, sides=entry.sides, modifier=entry.modifier),
        results=entry.results,
        total=entry.total,
        createdAt=entry.created_at,
    )


def to_item_read(item: Item) -> ItemRead:
    return ItemRead(
        id=item.id,
        campaignId=item.campaign_id,
        name=item.name,
        type=item.type,
        description=item.description,
        price=item.price,
        weight=item.weight,
        damageDice=item.damage_dice,
        rangeMeters=item.range_meters,
        properties=item.properties,
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )


def _get_active_session(
    campaign_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
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
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        active = session.exec(
            select(Session).where(
                Session.party_id == party_id,
                Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
            )
        ).first()
    else:
        active = session.exec(
            select(Session).where(
                Session.campaign_id == campaign_id,
                Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
            )
        ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    return ActiveSessionRead(**to_session_read(active).model_dump())


@router.get("/campaigns/{campaign_id}/sessions/active", response_model=ActiveSessionRead)
def get_active_session(
    campaign_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return _get_active_session(campaign_id, user, session)


@router.get(
    "/campaigns/{campaign_id}/session/active",
    response_model=ActiveSessionRead,
    deprecated=True,
)
def get_active_session_deprecated(
    campaign_id: str,
    request: Request,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/campaigns/{campaign_id}/sessions/active."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/active",
        new_path="/api/campaigns/{campaign_id}/sessions/active",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    return _get_active_session(campaign_id, user, session)


@router.get("/campaigns/{campaign_id}/sessions", response_model=list[SessionRead])
def list_sessions(
    campaign_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
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
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        statement = (
            select(Session)
            .where(Session.party_id == party_id)
            .order_by(Session.sequence_number.desc())
        )
    else:
        statement = (
            select(Session)
            .where(Session.campaign_id == campaign_id)
            .order_by(Session.number.desc())
        )
    entries = session.exec(statement).all()
    return [
        to_session_read(entry)
        for entry in entries
    ]


async def _start_session(
    campaign_id: str,
    payload: SessionActivateRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
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
    if member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")

    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if not party_id:
        raise HTTPException(
            status_code=400,
            detail="No party found for campaign; create a party before starting sessions",
        )
    if party_id:
        existing_active = session.exec(
            select(Session).where(
                Session.party_id == party_id,
                Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
            )
        ).first()
    else:
        existing_active = session.exec(
            select(Session).where(
                Session.campaign_id == campaign_id,
                Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
            )
        ).first()
    last_closed_source: Session | None = None
    if existing_active:
        now = datetime.now(timezone.utc)
        existing_active.status = SessionStatus.CLOSED
        existing_active.ended_at = now
        if existing_active.started_at:
            existing_active.duration_seconds = max(
                0,
                existing_active.duration_seconds
                + int((now - existing_active.started_at).total_seconds()),
            )
        session.add(existing_active)
        session.commit()
        last_closed_source = existing_active
        await room_registry.broadcast(
            existing_active.id,
            {
                "type": "session_closed",
                "payload": {
                    "sessionId": existing_active.id,
                    "campaignId": campaign_id,
                    "endedAt": now.isoformat(),
                },
            },
        )
        await campaign_room_registry.broadcast(
            campaign_id,
            {
                "type": "session_closed",
                "payload": {
                    "sessionId": existing_active.id,
                    "campaignId": campaign_id,
                    "endedAt": now.isoformat(),
                },
            },
        )

    if not last_closed_source:
        if party_id:
            last_closed_source = session.exec(
                select(Session)
                .where(
                    Session.party_id == party_id,
                    Session.status == SessionStatus.CLOSED,
                )
                .order_by(Session.ended_at.desc(), Session.sequence_number.desc())
            ).first()
        else:
            last_closed_source = session.exec(
                select(Session)
                .where(
                    Session.campaign_id == campaign_id,
                    Session.status == SessionStatus.CLOSED,
                )
                .order_by(Session.ended_at.desc(), Session.number.desc())
            ).first()

    max_retries = 5
    for attempt in range(max_retries):
        if party_id:
            next_number = session.exec(
                select(func.coalesce(func.max(Session.sequence_number), 0)).where(
                    Session.party_id == party_id
                )
            ).one()
        else:
            next_number = session.exec(
                select(func.coalesce(func.max(Session.number), 0)).where(
                    Session.campaign_id == campaign_id
                )
            ).one()
        number = int(next_number) + 1
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Invalid title")

        entry = Session(
            id=str(uuid4()),
            party_id=party_id,
            campaign_id=campaign_id,
            number=number,
            sequence_number=number if party_id else None,
            title=title,
            status=SessionStatus.LOBBY,
            started_at=None,
        )
        session.add(entry)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            if party_id and attempt < max_retries - 1:
                continue
            raise
        session.refresh(entry)
        break
    else:
        raise HTTPException(status_code=409, detail="Failed to allocate session number")
    player_members = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == campaign_id,
            CampaignMember.role_mode == RoleMode.PLAYER,
        )
    ).all()
    previous_states = []
    if last_closed_source:
        previous_states = session.exec(
            select(SessionState).where(SessionState.session_id == last_closed_source.id)
        ).all()
    previous_by_user = {state.player_user_id: state for state in previous_states}
    for member_entry in player_members:
        previous_state = previous_by_user.get(member_entry.user_id)
        state_payload = previous_state.state_json if previous_state else {}
        cloned_state = dict(state_payload) if isinstance(state_payload, dict) else state_payload
        session.add(
            SessionState(
                id=str(uuid4()),
                session_id=entry.id,
                player_user_id=member_entry.user_id,
                state_json=cloned_state,
            )
        )
    session.commit()

    # Build lobby: get party players as expected participants
    if party_id:
        party_players = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == party_id,
                PartyMember.role == RoleMode.PLAYER,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).all()
        # Get display names from users
        from app.models.user import User as UserModel
        expected: dict[str, str] = {}
        for pm in party_players:
            u = session.exec(select(UserModel).where(UserModel.id == pm.user_id)).first()
            expected[pm.user_id] = (u.display_name or u.username or pm.user_id) if u else pm.user_id
    else:
        expected = {}

    if not expected:
        # No players to wait for — activate immediately
        now = datetime.now(timezone.utc)
        entry.status = SessionStatus.ACTIVE
        entry.started_at = now
        session.add(entry)
        session.commit()
        session.refresh(entry)
        await campaign_room_registry.broadcast(
            campaign_id,
            {
                "type": "session_started",
                "payload": {
                    "sessionId": entry.id,
                    "campaignId": campaign_id,
                    "title": entry.title,
                    "startedAt": now.isoformat(),
                },
            },
        )
    else:
        _lobby_ready[entry.id] = set()
        _lobby_expected[entry.id] = expected
        expected_list = [{"userId": uid, "displayName": name} for uid, name in expected.items()]
        await campaign_room_registry.broadcast(
            campaign_id,
            {
                "type": "session_lobby",
                "payload": {
                    "sessionId": entry.id,
                    "campaignId": campaign_id,
                    "title": entry.title,
                    "expectedPlayers": expected_list,
                },
            },
        )
    return ActiveSessionRead(**to_session_read(entry).model_dump())


async def _start_session_for_party(
    party: Party,
    payload: SessionCreateByParty,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    if party.gm_user_id != user.id:
        raise HTTPException(status_code=403, detail="GM required")
    existing_active = session.exec(
        select(Session).where(
            Session.party_id == party.id,
            Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
        )
    ).first()
    if existing_active:
        raise HTTPException(status_code=409, detail="Active session already exists")

    last_closed_source = session.exec(
            select(Session)
            .where(
                Session.party_id == party.id,
                Session.status == SessionStatus.CLOSED,
            )
            .order_by(Session.ended_at.desc(), Session.sequence_number.desc())
        ).first()

    max_retries = 5
    for attempt in range(max_retries):
        next_number = session.exec(
            select(func.coalesce(func.max(Session.sequence_number), 0)).where(
                Session.party_id == party.id
            )
        ).one()
        number = int(next_number) + 1
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Invalid title")

        entry = Session(
            id=str(uuid4()),
            party_id=party.id,
            campaign_id=party.campaign_id,
            number=number,
            sequence_number=number,
            title=title,
            status=SessionStatus.LOBBY,
            started_at=None,
        )
        session.add(entry)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            if attempt < max_retries - 1:
                continue
            raise
        session.refresh(entry)
        break
    else:
        raise HTTPException(status_code=409, detail="Failed to allocate session number")

    player_members = session.exec(
        select(PartyMember).where(
            PartyMember.party_id == party.id,
            PartyMember.role == RoleMode.PLAYER,
            PartyMember.status == PartyMemberStatus.JOINED,
        )
    ).all()
    previous_states = []
    if last_closed_source:
        previous_states = session.exec(
            select(SessionState).where(SessionState.session_id == last_closed_source.id)
        ).all()
    previous_by_user = {state.player_user_id: state for state in previous_states}
    for member_entry in player_members:
        previous_state = previous_by_user.get(member_entry.user_id)
        state_payload = previous_state.state_json if previous_state else {}
        cloned_state = dict(state_payload) if isinstance(state_payload, dict) else state_payload
        session.add(
            SessionState(
                id=str(uuid4()),
                session_id=entry.id,
                player_user_id=member_entry.user_id,
                state_json=cloned_state,
            )
        )
    session.commit()

    # Build lobby expected players
    from app.models.user import User as UserModel
    expected: dict[str, str] = {}
    for pm in player_members:
        u = session.exec(select(UserModel).where(UserModel.id == pm.user_id)).first()
        expected[pm.user_id] = (u.display_name or u.username or pm.user_id) if u else pm.user_id

    if not expected:
        now = datetime.now(timezone.utc)
        entry.status = SessionStatus.ACTIVE
        entry.started_at = now
        session.add(entry)
        session.commit()
        session.refresh(entry)
        await campaign_room_registry.broadcast(
            party.campaign_id,
            {
                "type": "session_started",
                "payload": {
                    "sessionId": entry.id,
                    "campaignId": party.campaign_id,
                    "title": entry.title,
                    "startedAt": now.isoformat(),
                },
            },
        )
    else:
        _lobby_ready[entry.id] = set()
        _lobby_expected[entry.id] = expected
        expected_list = [{"userId": uid, "displayName": name} for uid, name in expected.items()]
        await campaign_room_registry.broadcast(
            party.campaign_id,
            {
                "type": "session_lobby",
                "payload": {
                    "sessionId": entry.id,
                    "campaignId": party.campaign_id,
                    "title": entry.title,
                    "expectedPlayers": expected_list,
                },
            },
        )
    return ActiveSessionRead(**to_session_read(entry).model_dump())


@router.post("/campaigns/{campaign_id}/sessions", response_model=ActiveSessionRead)
async def create_session(
    campaign_id: str,
    payload: SessionActivateRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await _start_session(campaign_id, payload, user, session)


@router.post("/parties/{party_id}/sessions", response_model=ActiveSessionRead)
async def create_party_session(
    party_id: str,
    payload: SessionCreateByParty,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    party = require_party_gm(party_id, user, session)
    return await _start_session_for_party(party, payload, user, session)


@router.get("/parties/{party_id}/sessions", response_model=list[SessionRead])
def list_party_sessions(
    party_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    party = require_party_member_or_gm(party_id, user, session)
    entries = session.exec(
        select(Session)
        .where(Session.party_id == party_id)
        .order_by(Session.sequence_number.desc())
    ).all()
    return [
        to_session_read(entry)
        for entry in entries
    ]


@router.get("/parties/{party_id}/sessions/active", response_model=ActiveSessionRead)
def get_party_active_session(
    party_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    party = require_party_member_or_gm(party_id, user, session)
    active = session.exec(
        select(Session).where(
            Session.party_id == party_id,
            Session.status.in_([SessionStatus.ACTIVE, SessionStatus.LOBBY]),
        )
    ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    return ActiveSessionRead(**to_session_read(active).model_dump())


@router.get("/sessions/{session_id}/lobby")
def get_lobby_status(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    expected = _lobby_expected.get(session_id, {})
    ready = list(_lobby_ready.get(session_id, set()))
    return LobbyStatusRead(
        sessionId=session_id,
        expected=[{"userId": uid, "displayName": name} for uid, name in expected.items()],
        ready=ready,
    )


@router.post("/sessions/{session_id}/lobby/join")
async def join_lobby(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.LOBBY:
        raise HTTPException(status_code=400, detail="Session is not in lobby state")

    # Validate party membership
    if entry.party_id:
        member = session.exec(
            select(PartyMember).where(
                PartyMember.party_id == entry.party_id,
                PartyMember.user_id == user.id,
                PartyMember.status == PartyMemberStatus.JOINED,
            )
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a party member")

    expected = _lobby_expected.get(session_id, {})
    if session_id not in _lobby_ready:
        _lobby_ready[session_id] = set()
    _lobby_ready[session_id].add(user.id)

    display_name = expected.get(user.id, user.display_name or user.username or user.id)
    ready_count = len(_lobby_ready[session_id])
    total_count = len(expected)

    await campaign_room_registry.broadcast(
        entry.campaign_id,
        {
            "type": "player_joined_lobby",
            "payload": {
                "sessionId": session_id,
                "userId": user.id,
                "displayName": display_name,
                "readyCount": ready_count,
                "totalCount": total_count,
            },
        },
    )

    # Check if everyone is ready
    if expected and _lobby_ready[session_id] >= set(expected.keys()):
        now = datetime.now(timezone.utc)
        entry.status = SessionStatus.ACTIVE
        entry.started_at = now
        session.add(entry)
        session.commit()
        session.refresh(entry)
        _lobby_ready.pop(session_id, None)
        _lobby_expected.pop(session_id, None)
        await campaign_room_registry.broadcast(
            entry.campaign_id,
            {
                "type": "session_started",
                "payload": {
                    "sessionId": entry.id,
                    "campaignId": entry.campaign_id,
                    "title": entry.title,
                    "startedAt": now.isoformat(),
                },
            },
        )

    return {"ok": True}


@router.post("/sessions/{session_id}/lobby/force-start")
async def force_start_lobby(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.LOBBY:
        raise HTTPException(status_code=400, detail="Session is not in lobby state")

    # Only GM can force start
    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party or party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
    else:
        member = session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == entry.campaign_id,
                CampaignMember.user_id == user.id,
            )
        ).first()
        if not member or member.role_mode != RoleMode.GM:
            raise HTTPException(status_code=403, detail="GM required")

    now = datetime.now(timezone.utc)
    entry.status = SessionStatus.ACTIVE
    entry.started_at = now
    session.add(entry)
    session.commit()
    session.refresh(entry)
    _lobby_ready.pop(session_id, None)
    _lobby_expected.pop(session_id, None)

    await campaign_room_registry.broadcast(
        entry.campaign_id,
        {
            "type": "session_started",
            "payload": {
                "sessionId": entry.id,
                "campaignId": entry.campaign_id,
                "title": entry.title,
                "startedAt": now.isoformat(),
            },
        },
    )
    return ActiveSessionRead(**to_session_read(entry).model_dump())


@router.post("/parties/{party_id}/sessions/{session_id}/close", response_model=ActiveSessionRead)
async def close_party_session(
    party_id: str,
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    party = require_party_gm(party_id, user, session)
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry or entry.party_id != party.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status not in (SessionStatus.ACTIVE, SessionStatus.LOBBY):
        raise HTTPException(status_code=400, detail="Session is not active")
    now = datetime.now(timezone.utc)
    entry.status = SessionStatus.CLOSED
    entry.ended_at = now
    if entry.started_at:
        entry.duration_seconds = max(
            0,
            entry.duration_seconds + int((now - entry.started_at).total_seconds()),
        )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    _lobby_ready.pop(entry.id, None)
    _lobby_expected.pop(entry.id, None)
    await room_registry.broadcast(
        entry.id,
        {
            "type": "session_closed",
            "payload": {
                "sessionId": entry.id,
                "campaignId": party.campaign_id,
                "endedAt": now.isoformat(),
            },
        },
    )
    await campaign_room_registry.broadcast(
        party.campaign_id,
        {
            "type": "session_closed",
            "payload": {
                "sessionId": entry.id,
                "campaignId": party.campaign_id,
                "endedAt": now.isoformat(),
            },
        },
    )
    return ActiveSessionRead(**to_session_read(entry).model_dump())


@router.post(
    "/campaigns/{campaign_id}/session/activate",
    response_model=ActiveSessionRead,
    deprecated=True,
)
async def activate_session_deprecated(
    campaign_id: str,
    payload: SessionActivateRequest,
    request: Request,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/campaigns/{campaign_id}/sessions."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/activate",
        new_path="/api/campaigns/{campaign_id}/sessions",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    return await _start_session(campaign_id, payload, user, session)


@router.get("/sessions/{session_id}/shop/items", response_model=list[ItemRead])
def list_session_shop_items(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    items = session.exec(
        select(Item)
        .where(Item.campaign_id == entry.campaign_id)
        .order_by(Item.created_at.desc())
    ).all()
    return [to_item_read(item) for item in items]

def _to_inventory_read(entry: InventoryItem) -> InventoryRead:
    return InventoryRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        partyId=entry.party_id,
        memberId=entry.member_id,
        itemId=entry.item_id,
        quantity=entry.quantity,
        isEquipped=entry.is_equipped,
        notes=entry.notes,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


@router.post("/sessions/{session_id}/shop/buy", response_model=InventoryRead, status_code=201)
def buy_session_shop_item(
    session_id: str,
    payload: InventoryBuy,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    item = session.exec(select(Item).where(Item.id == payload.itemId)).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.campaign_id != entry.campaign_id:
        raise HTTPException(status_code=400, detail="Item does not belong to campaign")
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid quantity")

    party_id = entry.party_id

    existing = session.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.party_id == party_id,
            InventoryItem.member_id == member.id,
            InventoryItem.item_id == payload.itemId,
        )
    ).first()
    purchase_log = PurchaseEvent(
        id=str(uuid4()),
        session_id=session_id,
        user_id=user.id,
        member_id=member.id,
        item_id=payload.itemId,
        item_name=item.name,
        quantity=payload.quantity,
    )
    session.add(purchase_log)

    if existing:
        existing.quantity += payload.quantity
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return _to_inventory_read(existing)

    new_entry = InventoryItem(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        party_id=party_id,
        member_id=member.id,
        item_id=payload.itemId,
        quantity=payload.quantity,
        is_equipped=False,
        notes=None,
    )
    session.add(new_entry)
    session.commit()
    session.refresh(new_entry)
    return _to_inventory_read(new_entry)


@router.post("/sessions/{session_id}/close", response_model=ActiveSessionRead)
async def close_session(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")
    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        if party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    now = datetime.now(timezone.utc)
    entry.status = SessionStatus.CLOSED
    entry.ended_at = now
    if entry.started_at:
        entry.duration_seconds = max(
            0,
            entry.duration_seconds + int((now - entry.started_at).total_seconds()),
        )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    await room_registry.broadcast(
        entry.id,
        {
            "type": "session_closed",
            "payload": {
                "sessionId": entry.id,
                "campaignId": entry.campaign_id,
                "endedAt": now.isoformat(),
            },
        },
    )
    await campaign_room_registry.broadcast(
        entry.campaign_id,
        {
            "type": "session_closed",
            "payload": {
                "sessionId": entry.id,
                "campaignId": entry.campaign_id,
                "endedAt": now.isoformat(),
            },
        },
    )
    return ActiveSessionRead(**to_session_read(entry).model_dump())


@router.post(
    "/campaigns/{campaign_id}/session/end",
    response_model=ActiveSessionRead,
    deprecated=True,
)
async def end_session_deprecated(
    campaign_id: str,
    request: Request,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/sessions/{session_id}/close."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/end",
        new_path="/api/sessions/{session_id}/close",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        active = session.exec(
            select(Session).where(
                Session.party_id == party_id,
                Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    else:
        active = session.exec(
            select(Session).where(
                Session.campaign_id == campaign_id,
                Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session to end")
    return await close_session(active.id, user, session)


@router.post("/sessions/{session_id}/resume", response_model=ActiveSessionRead)
async def resume_session(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    if member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")
    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        if party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")

    active = session.exec(
        select(Session).where(
            Session.campaign_id == entry.campaign_id,
            Session.status == SessionStatus.ACTIVE,
        )
    ).first()
    if active and active.id != entry.id:
        now = datetime.now(timezone.utc)
        active.status = SessionStatus.CLOSED
        active.ended_at = now
        if active.started_at:
            active.duration_seconds = max(
                0,
                active.duration_seconds + int((now - active.started_at).total_seconds()),
            )
        session.add(active)
        session.commit()
        await room_registry.broadcast(
            active.id,
            {"type": "session_closed", "payload": {"endedAt": now.isoformat()}},
        )

    now = datetime.now(timezone.utc)
    entry.status = SessionStatus.ACTIVE
    entry.started_at = now
    entry.ended_at = None
    session.add(entry)
    session.commit()
    session.refresh(entry)
    await room_registry.broadcast(
        entry.id,
        {
            "type": "session_resumed",
            "payload": {
                "sessionId": entry.id,
                "campaignId": entry.campaign_id,
                "joinCode": entry.join_code,
                "startedAt": entry.started_at.isoformat() if entry.started_at else None,
            },
        },
    )
    await campaign_room_registry.broadcast(
        entry.campaign_id,
        {
            "type": "session_resumed",
            "payload": {
                "sessionId": entry.id,
                "campaignId": entry.campaign_id,
                "startedAt": entry.started_at.isoformat() if entry.started_at else None,
            },
        },
    )
    return ActiveSessionRead(**to_session_read(entry).model_dump())





async def _send_session_command(
    session_id: str,
    payload: SessionCommandRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member or member.role_mode != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")
    if entry.party_id:
        party = session.exec(select(Party).where(Party.id == entry.party_id)).first()
        if not party:
            raise HTTPException(status_code=404, detail="Party not found")
        if party.gm_user_id != user.id:
            raise HTTPException(status_code=403, detail="GM required")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    if payload.type not in {"open_shop", "close_shop", "request_roll"}:
        raise HTTPException(status_code=400, detail="Invalid command")
    if payload.type == "request_roll":
        expression = (payload.payload or {}).get("expression")
        if not expression or not isinstance(expression, str):
            raise HTTPException(status_code=400, detail="Missing dice expression")

    message = {
        "type": "gm_command",
        "payload": {
            "command": payload.type,
            "data": payload.payload or {},
            "issuedBy": member.display_name,
            "issuedAt": datetime.now(timezone.utc).isoformat(),
        },
    }
    await room_registry.broadcast(entry.id, message)
    return {"ok": True}


@router.post("/sessions/{session_id}/commands")
async def send_session_command(
    session_id: str,
    payload: SessionCommandRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await _send_session_command(session_id, payload, user, session)


@router.post("/campaigns/{campaign_id}/session/command", deprecated=True)
async def send_session_command_deprecated(
    campaign_id: str,
    payload: SessionCommandRequest,
    request: Request,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    """Deprecated. Remove after 2026-06-01. Use /api/sessions/{session_id}/commands."""
    log_deprecated_route(
        request,
        old_path="/api/campaigns/{campaign_id}/session/command",
        new_path="/api/sessions/{session_id}/commands",
        removal_date=DEPRECATION_REMOVAL_DATE,
        extra={"campaign_id": campaign_id, "user_id": getattr(user, "id", None)},
    )
    party_id = resolve_party_id_for_campaign(campaign_id, session)
    if party_id:
        active = session.exec(
            select(Session).where(
                Session.party_id == party_id,
                Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    else:
        active = session.exec(
            select(Session).where(
                Session.campaign_id == campaign_id,
                Session.status == SessionStatus.ACTIVE,
            )
        ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    return await _send_session_command(active.id, payload, user, session)
@router.get("/sessions/{session_id}/rolls", response_model=list[RollEventRead])
def list_rolls(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    statement = (
        select(RollEvent)
        .where(RollEvent.session_id == session_id)
        .order_by(RollEvent.created_at.desc())
        .limit(limit)
    )
    entries = session.exec(statement).all()
    return [to_roll_read(item) for item in entries]


@router.post("/sessions/{session_id}/rolls/manual", response_model=dict)
async def submit_manual_roll(
    session_id: str,
    payload: ManualRollRequest,
    user: User = Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")
    parsed = parse_expression(payload.expression)
    count, sides, modifier = parsed if parsed else (1, 20, 0)
    event = RollEvent(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        session_id=session_id,
        user_id=user.id,
        author_name=member.display_name,
        role_mode=member.role_mode,
        label=payload.label,
        expression=payload.expression,
        count=count,
        sides=sides,
        modifier=modifier,
        results=[payload.result],
        total=payload.result,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    payload_out = to_roll_read(event).model_dump(mode="json")
    await room_registry.broadcast(session_id, {"type": "roll_created", "payload": payload_out})
    return payload_out


@router.get("/sessions/{session_id}/activity", response_model=list[ActivityEvent])
def get_session_activity(
    session_id: str,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    entry = session.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Session not found")
    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a campaign member")

    started_at = entry.started_at or entry.created_at

    def offset(ts: datetime) -> int:
        if not started_at or not ts:
            return 0
        delta = (ts.replace(tzinfo=None) - started_at.replace(tzinfo=None)).total_seconds()
        return max(0, int(delta))

    events: list[ActivityEvent] = []

    # Rolls
    rolls = session.exec(
        select(RollEvent, User)
        .outerjoin(User, RollEvent.user_id == User.id)
        .where(RollEvent.session_id == session_id)
        .order_by(RollEvent.created_at)
    ).all()
    for roll, roll_user in rolls:
        events.append(RollActivityEvent(
            userId=roll.user_id,
            username=roll_user.username if roll_user else None,
            displayName=(roll_user.display_name if roll_user else None) or roll.author_name,
            expression=roll.expression,
            results=roll.results,
            total=roll.total,
            label=roll.label,
            timestamp=roll.created_at,
            sessionOffsetSeconds=offset(roll.created_at),
        ))

    # Purchases
    purchases = session.exec(
        select(PurchaseEvent, User)
        .outerjoin(User, PurchaseEvent.user_id == User.id)
        .where(PurchaseEvent.session_id == session_id)
        .order_by(PurchaseEvent.created_at)
    ).all()
    for purchase, purchase_user in purchases:
        events.append(PurchaseActivityEvent(
            userId=purchase.user_id,
            username=purchase_user.username if purchase_user else None,
            displayName=purchase_user.display_name if purchase_user else None,
            itemName=purchase.item_name,
            quantity=purchase.quantity,
            timestamp=purchase.created_at,
            sessionOffsetSeconds=offset(purchase.created_at),
        ))

    events.sort(key=lambda e: e.timestamp)
    return events
