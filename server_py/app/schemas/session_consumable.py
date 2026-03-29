from __future__ import annotations

from pydantic import BaseModel

from app.schemas.roll import RollSource


class SessionHealingConsumableTargetRead(BaseModel):
    playerUserId: str
    displayName: str
    currentHp: int
    maxHp: int
    isSelf: bool


class SessionUseConsumableRequest(BaseModel):
    inventoryItemId: str
    targetPlayerUserId: str | None = None
    rollSource: RollSource = "system"
    manualRolls: list[int] | None = None


class SessionUseConsumableRead(BaseModel):
    sessionId: str
    campaignId: str
    partyId: str | None = None
    actorUserId: str
    targetPlayerUserId: str
    inventoryItemId: str | None = None
    itemId: str | None = None
    itemName: str
    targetDisplayName: str
    healingApplied: int
    newHp: int
    maxHp: int
    remainingQuantity: int
    effectDice: str | None = None
    effectBonus: int = 0
    effectRolls: list[int] = []
    effectRollSource: RollSource
