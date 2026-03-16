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


ActivityEvent = Union[RollActivityEvent, PurchaseActivityEvent, ShopActivityEvent]


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
