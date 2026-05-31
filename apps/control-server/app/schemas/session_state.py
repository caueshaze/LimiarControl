from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field


class PendingSpellPreparationRead(BaseModel):
    source: str
    classKey: str
    preparedLimit: int
    currentPreparedSpellIds: list[str]
    createdAt: str
    availableDuringRest: bool = False


class SessionStateRead(BaseModel):
    id: str
    sessionId: str
    playerUserId: str
    state: dict
    createdAt: datetime
    updatedAt: datetime | None
    activeSpellEffects: list[dict] | None = None
    activeConcentration: dict | None = None
    pendingSpellPreparation: PendingSpellPreparationRead | None = None


class ClearConcentrationRequest(BaseModel):
    concentrationGroup: str | None = None


class OutOfCombatCastRequest(BaseModel):
    spellId: str | None = None
    canonicalKey: str | None = None
    weapon_item_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("weapon_item_id", "weaponItemId"),
    )
    slotLevel: int | None = None
    variantKey: str | None = None
    targetPlayerUserId: str | None = None
    targetPlayerUserIds: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("targetPlayerUserIds", "target_player_user_ids"),
    )
    consumable_material_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("consumable_material_key", "consumableMaterialKey"),
    )


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
