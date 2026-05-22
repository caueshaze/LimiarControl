from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models.base_item import (
    BaseItemArmorCategory,
    BaseItemArmorMaterial,
    BaseItemCostUnit,
    BaseItemDamageType,
    BaseItemDexBonusRule,
    BaseItemEquipmentCategory,
    BaseItemKind,
    BaseItemProperty,
    BaseItemSource,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.campaign import SystemType

from .base_item_write import BaseItemAliasRead, MagicItemCastSpellEffect, MagicItemRechargeType


class BaseItemRead(BaseModel):
    id: str
    system: SystemType
    canonicalKey: str
    nameEn: str
    namePt: str
    descriptionEn: Optional[str] = None
    descriptionPt: Optional[str] = None
    itemKind: BaseItemKind
    equipmentCategory: Optional[BaseItemEquipmentCategory] = None
    costQuantity: Optional[float] = None
    costUnit: Optional[BaseItemCostUnit] = None
    weight: Optional[float] = None
    weaponCategory: Optional[BaseItemWeaponCategory] = None
    weaponRangeType: Optional[BaseItemWeaponRangeType] = None
    damageDice: Optional[str] = None
    damageType: Optional[BaseItemDamageType] = None
    healDice: Optional[str] = None
    healBonus: Optional[int] = None
    chargesMax: Optional[int] = None
    rechargeType: Optional[MagicItemRechargeType] = None
    magicEffect: Optional[MagicItemCastSpellEffect] = None
    rangeNormalMeters: Optional[int] = None
    rangeLongMeters: Optional[int] = None
    versatileDamage: Optional[str] = None
    weaponPropertiesJson: list[BaseItemProperty] = Field(default_factory=list)
    armorCategory: Optional[BaseItemArmorCategory] = None
    armorClassBase: Optional[int] = None
    armorMaterial: Optional[BaseItemArmorMaterial] = None
    dexBonusRule: Optional[BaseItemDexBonusRule] = None
    strengthRequirement: Optional[int] = None
    stealthDisadvantage: Optional[bool] = None
    isShield: bool
    source: BaseItemSource
    sourceRef: Optional[str] = None
    isSrd: bool
    isActive: bool
    aliases: list[BaseItemAliasRead] = Field(default_factory=list)
