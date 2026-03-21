from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel

from app.models.campaign import RoleMode
from app.models.session import SessionStatus

RestState = Literal["exploration", "short_rest", "long_rest"]


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


class RestActivityEvent(BaseModel):
    type: Literal["rest"] = "rest"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    action: Literal["short_started", "short_ended", "long_started", "long_ended"]
    timestamp: datetime
    sessionOffsetSeconds: int


class RewardActivityEvent(BaseModel):
    type: Literal["reward"] = "reward"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    action: Literal["currency", "item", "xp"]
    targetUserId: Optional[str] = None
    targetDisplayName: Optional[str] = None
    amountLabel: Optional[str] = None
    itemName: Optional[str] = None
    quantity: Optional[int] = None
    currentXp: Optional[int] = None
    nextLevelThreshold: Optional[int] = None
    timestamp: datetime
    sessionOffsetSeconds: int


class LevelUpActivityEvent(BaseModel):
    type: Literal["level_up"] = "level_up"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    action: Literal["requested", "approved", "denied"]
    targetUserId: Optional[str] = None
    targetDisplayName: Optional[str] = None
    level: int
    experiencePoints: int
    pendingLevelUp: bool
    timestamp: datetime
    sessionOffsetSeconds: int


class HitDiceActivityEvent(BaseModel):
    type: Literal["hit_dice"] = "hit_dice"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    roll: int
    healingApplied: int
    currentHp: int
    maxHp: Optional[int] = None
    hitDiceRemaining: int
    hitDiceTotal: int
    hitDieType: str
    timestamp: datetime
    sessionOffsetSeconds: int


class PlayerHpActivityEvent(BaseModel):
    type: Literal["player_hp"] = "player_hp"
    userId: Optional[str] = None
    username: Optional[str] = None
    displayName: Optional[str] = None
    action: Literal["damaged", "healed", "hp_set"]
    targetUserId: Optional[str] = None
    targetDisplayName: Optional[str] = None
    currentHp: Optional[int] = None
    previousHp: Optional[int] = None
    delta: Optional[int] = None
    maxHp: Optional[int] = None
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
    RestActivityEvent,
    RewardActivityEvent,
    LevelUpActivityEvent,
    HitDiceActivityEvent,
    PlayerHpActivityEvent,
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
    restState: RestState = "exploration"


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
