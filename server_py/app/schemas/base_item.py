from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.base_item import (
    BaseItemArmorCategory,
    BaseItemCostUnit,
    BaseItemKind,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.campaign import SystemType


class BaseItemAliasRead(BaseModel):
    id: str
    alias: str
    locale: Optional[str] = None
    aliasType: Optional[str] = None


class BaseItemRead(BaseModel):
    id: str
    system: SystemType
    canonicalKey: str
    nameEn: str
    namePt: str
    descriptionEn: Optional[str] = None
    descriptionPt: Optional[str] = None
    itemKind: BaseItemKind
    equipmentCategory: Optional[str] = None
    costQuantity: Optional[float] = None
    costUnit: Optional[BaseItemCostUnit] = None
    weight: Optional[float] = None
    weaponCategory: Optional[BaseItemWeaponCategory] = None
    weaponRangeType: Optional[BaseItemWeaponRangeType] = None
    damageDice: Optional[str] = None
    damageType: Optional[str] = None
    rangeNormal: Optional[int] = None
    rangeLong: Optional[int] = None
    versatileDamage: Optional[str] = None
    weaponPropertiesJson: Optional[Any] = None
    armorCategory: Optional[BaseItemArmorCategory] = None
    armorClassBase: Optional[int] = None
    dexBonusRule: Optional[str] = None
    strengthRequirement: Optional[int] = None
    stealthDisadvantage: Optional[bool] = None
    isShield: bool
    source: Optional[str] = None
    sourceRef: Optional[str] = None
    isSrd: bool
    isActive: bool
    aliases: list[BaseItemAliasRead] = Field(default_factory=list)
