import asyncio
import re

from fastapi import WebSocket

from app.models.roll_event import RollEvent
from app.schemas.roll_event import RollDice, RollEventRead


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
        id=entry.id or "",
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
