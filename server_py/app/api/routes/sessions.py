import random
import string
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlmodel import Session as DbSession, select, func

from app.api.deps import get_current_user
from app.api.deprecation import log_deprecated_route
from app.api.ws import campaign_room_registry, room_registry
from app.db.session import get_session
from app.models.campaign import Campaign, RoleMode
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.roll_event import RollEvent
from app.models.session import Session, SessionStatus
from app.models.session_state import SessionState
from app.schemas.inventory import InventoryBuy, InventoryRead
from app.schemas.item import ItemRead
from app.schemas.roll_event import RollDice, RollEventRead
from app.schemas.session import (
    ActiveSessionRead,
    SessionActivateRequest,
    SessionCommandRequest,
    SessionJoinRequest,
    SessionJoinResponse,
    SessionRead,
)
from app.schemas.session_state import SessionStateRead, SessionStateUpdate

router = APIRouter()

JOIN_CODE_CHARS = string.ascii_uppercase + string.digits
DEPRECATION_REMOVAL_DATE = date(2026, 6, 1)


def generate_join_code() -> str:
    length = random.randint(6, 8)
    return "".join(random.choice(JOIN_CODE_CHARS) for _ in range(length))


def ensure_unique_join_code(session: DbSession) -> str:
    for _ in range(20):
        code = generate_join_code()
        existing = session.exec(select(Session).where(Session.join_code == code)).first()
        if not existing:
            return code
    return f"{uuid4().hex[:8].upper()}"


def to_session_read(entry: Session, join_code: str | None) -> SessionRead:
    return SessionRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        number=entry.number,
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


def to_roll_read(entry: RollEvent) -> RollEventRead:
    return RollEventRead(
        id=entry.id,
        campaignId=entry.campaign_id or "",
        sessionId=entry.session_id,
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


def to_state_read(entry: SessionState) -> SessionStateRead:
    return SessionStateRead(
        id=entry.id,
        sessionId=entry.session_id,
        playerUserId=entry.player_user_id,
        state=entry.state_json,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
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
    active = session.exec(
        select(Session).where(
            Session.campaign_id == campaign_id,
            Session.status == SessionStatus.ACTIVE,
        )
    ).first()
    if not active:
        raise HTTPException(status_code=404, detail="No active session")
    join_code = active.join_code if member.role_mode == RoleMode.GM else None
    return ActiveSessionRead(**to_session_read(active, join_code).model_dump())


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
    statement = (
        select(Session)
        .where(Session.campaign_id == campaign_id)
        .order_by(Session.number.desc())
    )
    entries = session.exec(statement).all()
    return [
        to_session_read(
            entry,
            entry.join_code if member.role_mode == RoleMode.GM else None,
        )
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

    existing_active = session.exec(
        select(Session).where(
            Session.campaign_id == campaign_id,
            Session.status == SessionStatus.ACTIVE,
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
        last_closed_source = session.exec(
            select(Session)
            .where(
                Session.campaign_id == campaign_id,
                Session.status == SessionStatus.CLOSED,
            )
            .order_by(Session.ended_at.desc(), Session.number.desc())
        ).first()

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
        campaign_id=campaign_id,
        number=number,
        title=title,
        join_code=ensure_unique_join_code(session),
        status=SessionStatus.ACTIVE,
        started_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
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
        payload = previous_state.state_json if previous_state else {}
        cloned_state = dict(payload) if isinstance(payload, dict) else payload
        session.add(
            SessionState(
                id=str(uuid4()),
                session_id=entry.id,
                player_user_id=member_entry.user_id,
                state_json=cloned_state,
            )
        )
    session.commit()
    await room_registry.broadcast(
        entry.id,
        {
            "type": "session_started",
            "payload": {
                "sessionId": entry.id,
                "campaignId": campaign_id,
                "joinCode": entry.join_code,
                "title": entry.title,
                "startedAt": entry.started_at.isoformat() if entry.started_at else None,
            },
        },
    )
    await campaign_room_registry.broadcast(
        campaign_id,
        {
            "type": "session_started",
            "payload": {
                "sessionId": entry.id,
                "campaignId": campaign_id,
                "title": entry.title,
                "startedAt": entry.started_at.isoformat() if entry.started_at else None,
            },
        },
    )
    return ActiveSessionRead(**to_session_read(entry, entry.join_code).model_dump())


@router.post("/campaigns/{campaign_id}/sessions", response_model=ActiveSessionRead)
async def create_session(
    campaign_id: str,
    payload: SessionActivateRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    return await _start_session(campaign_id, payload, user, session)


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

    existing = session.exec(
        select(InventoryItem).where(
            InventoryItem.campaign_id == entry.campaign_id,
            InventoryItem.member_id == member.id,
            InventoryItem.item_id == payload.itemId,
        )
    ).first()
    if existing:
        existing.quantity += payload.quantity
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return _to_inventory_read(existing)

    new_entry = InventoryItem(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
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
    return ActiveSessionRead(**to_session_read(entry, None).model_dump())


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
    return ActiveSessionRead(**to_session_read(entry, entry.join_code).model_dump())


@router.post("/sessions/join", response_model=SessionJoinResponse)
def join_session(
    payload: SessionJoinRequest,
    user=Depends(get_current_user),
    session: DbSession = Depends(get_session),
):
    join_code = payload.joinCode.strip().upper()
    if not join_code:
        raise HTTPException(status_code=400, detail="Invalid payload")

    entry = session.exec(select(Session).where(Session.join_code == join_code)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Join code not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    campaign = session.exec(select(Campaign).where(Campaign.id == entry.campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    gm_member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.role_mode == RoleMode.GM,
        )
    ).first()
    gm_name = gm_member.display_name if gm_member else None

    member = session.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()

    if member:
        if user.display_name:
            member.display_name = user.display_name
        session.add(member)
        session.commit()
        session.refresh(member)
        return SessionJoinResponse(
            campaignId=entry.campaign_id,
            campaignName=campaign.name,
            gmName=gm_name,
            sessionId=entry.id,
            memberId=member.id,
            displayName=member.display_name,
            roleMode=member.role_mode,
        )

    member = CampaignMember(
        id=str(uuid4()),
        campaign_id=entry.campaign_id,
        user_id=user.id,
        display_name=user.display_name or user.username,
        role_mode=RoleMode.PLAYER,
    )
    session.add(member)
    session.commit()
    session.refresh(member)
    return SessionJoinResponse(
        campaignId=entry.campaign_id,
        campaignName=campaign.name,
        gmName=gm_name,
        sessionId=entry.id,
        memberId=member.id,
        displayName=member.display_name,
        roleMode=member.role_mode,
    )


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


@router.get("/sessions/{session_id}/state", response_model=list[SessionStateRead])
def get_session_state(
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
    states = session.exec(
        select(SessionState).where(SessionState.session_id == session_id)
    ).all()
    return [to_state_read(state) for state in states]


@router.put("/sessions/{session_id}/players/{player_id}/state", response_model=SessionStateRead)
def upsert_session_state(
    session_id: str,
    player_id: str,
    payload: SessionStateUpdate,
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
    if member.role_mode != RoleMode.GM and user.id != player_id:
        raise HTTPException(status_code=403, detail="Not allowed")
    state = session.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == player_id,
        )
    ).first()
    if state:
        state.state_json = payload.state
    else:
        state = SessionState(
            id=str(uuid4()),
            session_id=session_id,
            player_user_id=player_id,
            state_json=payload.state,
        )
    session.add(state)
    session.commit()
    session.refresh(state)
    return to_state_read(state)
