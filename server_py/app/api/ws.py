import asyncio
import json
import random
import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.core.auth import decode_jwt
from app.db.session import engine
from app.models.campaign import Campaign
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.party_member import PartyMember, PartyMemberStatus
from app.models.roll_event import RollEvent
from app.models.session import Session as CampaignSession, SessionStatus
from app.schemas.roll_event import RollDice, RollEventRead

router = APIRouter()

DICE_RE = re.compile(
    r"^\s*(?:(\d*)d(\d+))\s*(?:([+-])\s*(\d+))?\s*$", re.IGNORECASE
)


class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def add(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(session_id, set()).add(websocket)

    async def remove(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._rooms.get(session_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._rooms.pop(session_id, None)

    async def broadcast(self, session_id: str, message: dict) -> None:
        async with self._lock:
            connections = list(self._rooms.get(session_id, set()))
        if not connections:
            return
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                await self.remove(session_id, connection)


room_registry = RoomRegistry()


class CampaignRoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}
        # campaign_id -> {user_id: display_name}
        self._presence: dict[str, dict[str, str]] = {}
        self._lock = asyncio.Lock()

    async def add(self, campaign_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(campaign_id, set()).add(websocket)

    async def add_with_user(
        self, campaign_id: str, websocket: WebSocket, user_id: str, display_name: str
    ) -> None:
        async with self._lock:
            self._rooms.setdefault(campaign_id, set()).add(websocket)
            self._presence.setdefault(campaign_id, {})[user_id] = display_name

    async def remove(self, campaign_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._rooms.get(campaign_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._rooms.pop(campaign_id, None)

    async def remove_with_user(
        self, campaign_id: str, websocket: WebSocket, user_id: str | None
    ) -> None:
        async with self._lock:
            connections = self._rooms.get(campaign_id)
            if connections:
                connections.discard(websocket)
                if not connections:
                    self._rooms.pop(campaign_id, None)
            if user_id:
                self._presence.get(campaign_id, {}).pop(user_id, None)
                if not self._presence.get(campaign_id):
                    self._presence.pop(campaign_id, None)

    def get_online_users(self, campaign_id: str) -> dict[str, str]:
        return dict(self._presence.get(campaign_id, {}))

    async def broadcast(self, campaign_id: str, message: dict) -> None:
        async with self._lock:
            connections = list(self._rooms.get(campaign_id, set()))
        if not connections:
            return
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                await self.remove(campaign_id, connection)


campaign_room_registry = CampaignRoomRegistry()


def parse_expression(expression: str) -> tuple[int, int, int] | None:
    match = DICE_RE.match(expression or "")
    if not match:
        return None
    count_raw, sides_raw, sign, modifier_raw = match.groups()
    count = int(count_raw) if count_raw else 1
    sides = int(sides_raw)
    modifier = int(modifier_raw) if modifier_raw else 0
    if sign == "-":
        modifier = -modifier
    if count < 1 or count > 50:
        return None
    if sides < 1 or sides > 1000:
        return None
    if modifier < -1000 or modifier > 1000:
        return None
    return count, sides, modifier


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


@router.websocket("/sessions/{session_id}")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    token = websocket.query_params.get("token")
    await websocket.accept()
    await room_registry.add(session_id, websocket)
    print(f"WS connect session={session_id}")
    member_info: CampaignMember | None = None
    session_info: CampaignSession | None = None
    if not token:
        await websocket.send_json(
            {"type": "error", "payload": {"requestId": None, "message": "Missing token"}}
        )
        await websocket.close(code=1008)
        return
    payload = decode_jwt(token)
    if not payload or not payload.get("sub"):
        await websocket.send_json(
            {"type": "error", "payload": {"requestId": None, "message": "Invalid token"}}
        )
        await websocket.close(code=1008)
        return
    user_id = payload.get("sub")
    with Session(engine) as session:
        session_entry = session.exec(
            select(CampaignSession).where(CampaignSession.id == session_id)
        ).first()
        if not session_entry:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Session not found"}}
            )
            await websocket.close(code=1008)
            return
        if session_entry.status not in (SessionStatus.ACTIVE, SessionStatus.LOBBY):
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Session is not active"}}
            )
            await websocket.close(code=1008)
            return
        session_info = session_entry
        if session_entry.party_id:
            party = session.exec(
                select(Party).where(Party.id == session_entry.party_id)
            ).first()
            if not party:
                await websocket.send_json(
                    {"type": "error", "payload": {"requestId": None, "message": "Party not found"}}
                )
                await websocket.close(code=1008)
                return
            if party.gm_user_id != user_id:
                party_member = session.exec(
                    select(PartyMember).where(
                        PartyMember.party_id == party.id,
                        PartyMember.user_id == user_id,
                    )
                ).first()
                if not party_member or party_member.status != PartyMemberStatus.JOINED:
                    await websocket.send_json(
                        {"type": "error", "payload": {"requestId": None, "message": "Party join required"}}
                    )
                    await websocket.close(code=1008)
                    return
        member = session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.user_id == user_id,
            )
        ).first()
        if not member:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Join required"}}
            )
            await websocket.close(code=1008)
            return
        member_info = member
    await websocket.send_json(
        {"type": "connected", "payload": {"serverTime": datetime.now(timezone.utc).isoformat()}}
    )
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "payload": {"requestId": None, "message": "Invalid JSON"}}
                )
                continue

            message_type = data.get("type")
            payload = data.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {}

            if message_type == "join":
                continue

            if message_type != "roll":
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {
                            "requestId": payload.get("requestId"),
                            "message": "Unknown message type",
                        },
                    }
                )
                continue

            if member_info is None or session_info is None:
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {"requestId": payload.get("requestId"), "message": "Join required"},
                    }
                )
                continue

            request_id = payload.get("requestId")
            expression = payload.get("expression", "")
            label = payload.get("label")
            advantage = payload.get("advantage")  # "advantage" | "disadvantage" | None

            parsed = parse_expression(expression)
            if not parsed:
                print(f"DEBUG roll parse error session={session_id} expr={expression!r}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "payload": {"requestId": request_id, "message": "Invalid dice expression"},
                    }
                )
                continue

            role_mode_value = member_info.role_mode
            author_name = member_info.display_name

            count, sides, modifier = parsed
            if advantage in ("advantage", "disadvantage"):
                set_a = [random.randint(1, sides) for _ in range(count)]
                set_b = [random.randint(1, sides) for _ in range(count)]
                sum_a = sum(set_a)
                sum_b = sum(set_b)
                if advantage == "advantage":
                    chosen, other = (set_a, set_b) if sum_a >= sum_b else (set_b, set_a)
                else:
                    chosen, other = (set_a, set_b) if sum_a <= sum_b else (set_b, set_a)
                results = chosen + other  # store all dice: chosen first, discarded after
                total = sum(chosen) + modifier
                suffix = " (Advantage)" if advantage == "advantage" else " (Disadvantage)"
                label = (label + suffix) if label else suffix.strip()
            else:
                results = [random.randint(1, sides) for _ in range(count)]
                total = sum(results) + modifier

            with Session(engine) as session:
                campaign = session.exec(
                    select(Campaign).where(Campaign.id == session_info.campaign_id)
                ).first()
                if not campaign:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "payload": {"requestId": request_id, "message": "Campaign not found"},
                        }
                    )
                    continue
                event = RollEvent(
                    id=str(uuid4()),
                    campaign_id=campaign.id,
                    session_id=session_info.id,
                    user_id=user_id,
                    author_name=author_name,
                    role_mode=role_mode_value,
                    label=label,
                    expression=expression.strip(),
                    count=count,
                    sides=sides,
                    modifier=modifier,
                    results=results,
                    total=total,
                )
                session.add(event)
                session.commit()
                session.refresh(event)

            payload_out = to_roll_read(event).model_dump(mode="json")
            await room_registry.broadcast(
                session_id, {"type": "roll_created", "payload": payload_out}
            )
    except WebSocketDisconnect:
        pass
    finally:
        await room_registry.remove(session_id, websocket)
        print(f"WS disconnect session={session_id}")


@router.websocket("/campaigns/{campaign_id}")
async def campaign_ws(websocket: WebSocket, campaign_id: str) -> None:
    token = websocket.query_params.get("token")
    await websocket.accept()
    await campaign_room_registry.add(campaign_id, websocket)
    print(f"WS connect campaign={campaign_id}")
    connected_user_id: str | None = None
    connected_display_name: str = "Unknown"
    if not token:
        await websocket.send_json(
            {"type": "error", "payload": {"requestId": None, "message": "Missing token"}}
        )
        await websocket.close(code=1008)
        return
    payload = decode_jwt(token)
    if not payload or not payload.get("sub"):
        await websocket.send_json(
            {"type": "error", "payload": {"requestId": None, "message": "Invalid token"}}
        )
        await websocket.close(code=1008)
        return
    user_id = payload.get("sub")
    with Session(engine) as session:
        campaign = session.exec(
            select(Campaign).where(Campaign.id == campaign_id)
        ).first()
        if not campaign:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Campaign not found"}}
            )
            await websocket.close(code=1008)
            return
        member = session.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == campaign_id,
                CampaignMember.user_id == user_id,
            )
        ).first()
        if not member:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Join required"}}
            )
            await websocket.close(code=1008)
            return
        connected_user_id = user_id
        connected_display_name = member.display_name or user_id

    await campaign_room_registry.add_with_user(
        campaign_id, websocket, connected_user_id, connected_display_name
    )
    await campaign_room_registry.broadcast(
        campaign_id,
        {
            "type": "user_online",
            "payload": {
                "userId": connected_user_id,
                "displayName": connected_display_name,
            },
        },
    )
    await websocket.send_json(
        {
            "type": "connected",
            "payload": {
                "serverTime": datetime.now(timezone.utc).isoformat(),
                "onlineUsers": campaign_room_registry.get_online_users(campaign_id),
            },
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await campaign_room_registry.remove_with_user(campaign_id, websocket, connected_user_id)
        if connected_user_id:
            await campaign_room_registry.broadcast(
                campaign_id,
                {
                    "type": "user_offline",
                    "payload": {
                        "userId": connected_user_id,
                        "displayName": connected_display_name,
                    },
                },
            )
        print(f"WS disconnect campaign={campaign_id}")
