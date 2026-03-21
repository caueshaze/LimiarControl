from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel

from app.models.campaign import RoleMode
from app.models.session import SessionStatus


class SessionRead(BaseModel):
    id: str
    campaignId: str
    partyId: Optional[str] = None
    number: int
    title: str
    status: SessionStatus
    isActive: bool
    startedAt: Optional[datetime] = None
    endedAt: Optional[datetime] = None
    durationSeconds: int
    createdAt: datetime
    updatedAt: Optional[datetime]



class SessionActivateRequest(BaseModel):
    title: str


class SessionCreateByParty(BaseModel):
    title: str


class SessionCommandRequest(BaseModel):
    type: str
    payload: Optional[dict] = None


class RollRequest(BaseModel):
    expression: str
    label: Optional[str] = None
    advantage: Optional[Literal["advantage", "disadvantage"]] = None


class ManualRollRequest(BaseModel):
    expression: str
    result: int
    label: Optional[str] = None


class RollActivityEvent(BaseModel):
    type: Literal["roll"] = "roll"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    expression: str
    results: List[int]
    total: int
    label: Optional[str] = None
    timestamp: datetime
    sessionOffsetSeconds: int


class PurchaseActivityEvent(BaseModel):
    type: Literal["purchase"] = "purchase"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    itemName: str
    quantity: int
    timestamp: datetime
    sessionOffsetSeconds: int


class ShopActivityEvent(BaseModel):
    type: Literal["shop"] = "shop"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    action: Literal["opened", "closed"]
    timestamp: datetime
    sessionOffsetSeconds: int


class RollRequestActivityEvent(BaseModel):
    type: Literal["roll_request"] = "roll_request"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    expression: str
    reason: Optional[str] = None
    mode: Optional[Literal["advantage", "disadvantage"]] = None
    targetUserId: Optional[str] = None
    targetDisplayName: Optional[str] = None
    timestamp: datetime
    sessionOffsetSeconds: int


class CombatActivityEvent(BaseModel):
    type: Literal["combat"] = "combat"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    action: Literal["started", "ended"]
    note: Optional[str] = None
    timestamp: datetime
    sessionOffsetSeconds: int


class EntityActivityEvent(BaseModel):
    type: Literal["entity"] = "entity"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    action: Literal["added", "removed", "revealed", "hidden", "damaged", "healed", "hp_set"]
    entityName: str
    entityCategory: Optional[str] = None
    label: Optional[str] = None
    currentHp: Optional[int] = None
    previousHp: Optional[int] = None
    delta: Optional[int] = None
    maxHp: Optional[int] = None
    timestamp: datetime
    sessionOffsetSeconds: int


ActivityEvent = Union[
    RollActivityEvent,
    PurchaseActivityEvent,
    ShopActivityEvent,
    RollRequestActivityEvent,
    CombatActivityEvent,
    EntityActivityEvent,
]


class LobbyPlayer(BaseModel):
    userId: str
    displayName: str


class LobbyStatusRead(BaseModel):
    sessionId: str
    campaignId: Optional[str] = None
    partyId: Optional[str] = None
    expected: List[LobbyPlayer]
    ready: List[str]
    readyCount: int = 0
    totalCount: int = 0


class SessionRuntimeRead(BaseModel):
    sessionId: str
    campaignId: str
    partyId: Optional[str] = None
    status: SessionStatus
    shopOpen: bool
    combatActive: bool


class ActiveSessionRead(BaseModel):
    id: str
    campaignId: str
    partyId: Optional[str] = None
    number: int
    title: str
    status: SessionStatus
    isActive: bool
    startedAt: Optional[datetime] = None
    endedAt: Optional[datetime] = None
    durationSeconds: int
    createdAt: datetime
    updatedAt: Optional[datetime]
