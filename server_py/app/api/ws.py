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
        self._lock = asyncio.Lock()

    async def add(self, campaign_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(campaign_id, set()).add(websocket)

    async def remove(self, campaign_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._rooms.get(campaign_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._rooms.pop(campaign_id, None)

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
        if session_entry.status != SessionStatus.ACTIVE:
            await websocket.send_json(
                {"type": "error", "payload": {"requestId": None, "message": "Session is not active"}}
            )
            await websocket.close(code=1008)
            return
        session_info = session_entry
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
    await websocket.send_json(
        {"type": "connected", "payload": {"serverTime": datetime.now(timezone.utc).isoformat()}}
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await campaign_room_registry.remove(campaign_id, websocket)
        print(f"WS disconnect campaign={campaign_id}")
