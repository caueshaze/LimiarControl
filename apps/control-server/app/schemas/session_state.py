from datetime import datetime

from pydantic import BaseModel


class SessionStateRead(BaseModel):
    id: str
    sessionId: str
    playerUserId: str
    state: dict
    createdAt: datetime
    updatedAt: datetime | None
    activeSpellEffects: list[dict] | None = None
    activeConcentration: dict | None = None
    pendingSpellPreparation: dict | None = None


class ClearConcentrationRequest(BaseModel):
    concentrationGroup: str | None = None


class OutOfCombatCastRequest(BaseModel):
    spellId: str
    slotLevel: int | None = None
    variantKey: str | None = None


class PrepareSpellsRequest(BaseModel):
    preparedSpellIds: list[str]


class SessionStateUpdate(BaseModel):
    state: dict


class SessionStateLoadoutUpdate(BaseModel):
    currentWeaponId: str | None = None
    equippedArmorItemId: str | None = None


class SessionUseHitDieRead(BaseModel):
    sessionId: str
    campaignId: str
    partyId: str | None = None
    playerUserId: str
    currentHp: int
    maxHp: int
    hitDiceRemaining: int
    hitDiceTotal: int
    hitDieType: str
    roll: int
    healingApplied: int
    healingRolled: int
    constitutionModifier: int
