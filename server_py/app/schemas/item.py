import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.base_item import (
    BaseItemArmorCategory,
    BaseItemCostUnit,
    BaseItemKind,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.item import ItemType

DICE_EXPRESSION_RE = re.compile(
    r"^\s*(?:(\d*)d(\d+))\s*(?:([+-])\s*(\d+))?\s*$",
    re.IGNORECASE,
)
ITEM_DAMAGE_TYPE_VALUES = (
    "acid",
    "bludgeoning",
    "cold",
    "fire",
    "force",
    "lightning",
    "necrotic",
    "piercing",
    "poison",
    "psychic",
    "radiant",
    "slashing",
    "thunder",
)
ITEM_DAMAGE_TYPE_MAP = {value.lower(): value for value in ITEM_DAMAGE_TYPE_VALUES}
ITEM_DEX_BONUS_RULE_MAP = {
    "full": "full",
    "unlimited": "full",
    "max_2": "max_2",
    "max 2": "max_2",
    "none": "none",
}


class ItemCreate(BaseModel):
    name: str
    type: ItemType
    description: str
    price: Optional[float] = None
    weight: Optional[float] = None
    damageDice: Optional[str] = None
    damageType: Optional[str] = None
    rangeMeters: Optional[float] = None
    rangeLongMeters: Optional[float] = None
    versatileDamage: Optional[str] = None
    weaponCategory: Optional[BaseItemWeaponCategory] = None
    weaponRangeType: Optional[BaseItemWeaponRangeType] = None
    armorCategory: Optional[BaseItemArmorCategory] = None
    armorClassBase: Optional[int] = None
    dexBonusRule: Optional[str] = None
    strengthRequirement: Optional[int] = None
    stealthDisadvantage: Optional[bool] = None
    isShield: bool = False
    properties: list[str] = Field(default_factory=list)

    @field_validator("name", "description")
    @classmethod
    def normalize_required_text(cls, value: str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank")
        return normalized

    @field_validator("damageDice", "damageType", "versatileDamage", "dexBonusRule", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("price", "weight", "rangeMeters", "rangeLongMeters")
    @classmethod
    def validate_non_negative_numbers(cls, value: Optional[float]):
        if value is None:
            return None
        if value < 0:
            raise ValueError("Value cannot be negative")
        return value

    @field_validator("armorClassBase", "strengthRequirement")
    @classmethod
    def validate_non_negative_ints(cls, value: Optional[int]):
        if value is None:
            return None
        if value < 0:
            raise ValueError("Value cannot be negative")
        return value

    @field_validator("damageDice", "versatileDamage")
    @classmethod
    def validate_dice_expression(cls, value: Optional[str]):
        if value is None:
            return None
        if DICE_EXPRESSION_RE.match(value) is None:
            raise ValueError("Invalid dice expression")
        return value.lower().replace(" ", "")

    @field_validator("damageType")
    @classmethod
    def normalize_damage_type(cls, value: Optional[str]):
        if value is None:
            return None
        canonical = ITEM_DAMAGE_TYPE_MAP.get(value.lower())
        if canonical is None:
            raise ValueError(f"Unknown damage type: {value}")
        return canonical

    @field_validator("dexBonusRule")
    @classmethod
    def normalize_dex_bonus_rule(cls, value: Optional[str]):
        if value is None:
            return None
        canonical = ITEM_DEX_BONUS_RULE_MAP.get(value.lower())
        if canonical is None:
            raise ValueError(f"Unknown dex bonus rule: {value}")
        return canonical

    @field_validator("properties", mode="before")
    @classmethod
    def normalize_properties_list(cls, value: Optional[list[str]]):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("properties must be a list")
        return value

    @model_validator(mode="after")
    def validate_structured_fields(self):
        deduped_properties: list[str] = []
        seen_properties: set[str] = set()
        for property_value in self.properties:
            normalized = str(property_value or "").strip()
            if not normalized or normalized in seen_properties:
                continue
            seen_properties.add(normalized)
            deduped_properties.append(normalized)
        self.properties = deduped_properties

        if (
            self.rangeLongMeters is not None
            and self.rangeMeters is None
        ):
            raise ValueError("Long range requires a normal range")

        if (
            self.rangeMeters is not None
            and self.rangeLongMeters is not None
            and self.rangeLongMeters < self.rangeMeters
        ):
            raise ValueError("Long range cannot be smaller than normal range")

        if self.type == ItemType.WEAPON:
            if self.damageDice is None or self.damageType is None:
                raise ValueError("Weapons must define damage dice and damage type")
            if self.weaponCategory is None or self.weaponRangeType is None:
                raise ValueError("Weapons must define weapon category and range type")
            if (
                self.weaponRangeType == BaseItemWeaponRangeType.RANGED
                and self.rangeMeters is None
            ):
                raise ValueError("Ranged weapons must define range")
            if self.versatileDamage is not None and "versatile" not in self.properties:
                raise ValueError("Versatile damage requires the versatile property")
        elif self.type == ItemType.MAGIC:
            if self.damageDice is not None and self.damageType is None:
                raise ValueError("Damage type is required when magic items define damage")
            self.weaponCategory = None
            self.weaponRangeType = None
            self.versatileDamage = None
        else:
            self.damageDice = None
            self.damageType = None
            self.rangeMeters = None
            self.rangeLongMeters = None
            self.versatileDamage = None
            self.weaponCategory = None
            self.weaponRangeType = None

        if self.type == ItemType.ARMOR:
            if self.armorCategory is None or self.armorClassBase is None:
                raise ValueError("Armor must define category and armor class")
            if (
                self.armorCategory != BaseItemArmorCategory.SHIELD
                and self.dexBonusRule is None
            ):
                raise ValueError("Armor must define dex bonus rule")
            self.isShield = self.armorCategory == BaseItemArmorCategory.SHIELD
            self.properties = [
                value
                for value in self.properties
                if value != "stealth_disadvantage"
            ]
            if self.stealthDisadvantage:
                self.properties.append("stealth_disadvantage")
            if self.isShield:
                self.dexBonusRule = None
        else:
            self.armorCategory = None
            self.armorClassBase = None
            self.dexBonusRule = None
            self.strengthRequirement = None
            self.stealthDisadvantage = None
            self.isShield = False
            self.properties = [
                value
                for value in self.properties
                if value != "stealth_disadvantage"
            ]

        return self


class ItemUpdate(ItemCreate):
    pass


class ItemRead(BaseModel):
    id: str
    campaignId: str
    name: str
    type: ItemType
    description: str
    price: Optional[float]
    priceCopperValue: Optional[int] = None
    weight: Optional[float]
    damageDice: Optional[str]
    damageType: Optional[str]
    rangeMeters: Optional[float]
    rangeLongMeters: Optional[float]
    versatileDamage: Optional[str]
    weaponCategory: Optional[BaseItemWeaponCategory] = None
    weaponRangeType: Optional[BaseItemWeaponRangeType] = None
    armorCategory: Optional[BaseItemArmorCategory] = None
    armorClassBase: Optional[int] = None
    dexBonusRule: Optional[str] = None
    strengthRequirement: Optional[int] = None
    stealthDisadvantage: Optional[bool] = None
    isShield: bool = False
    properties: list[str]
    baseItemId: Optional[str] = None
    canonicalKeySnapshot: Optional[str] = None
    nameEnSnapshot: Optional[str] = None
    namePtSnapshot: Optional[str] = None
    itemKind: Optional[BaseItemKind] = None
    costUnit: Optional[BaseItemCostUnit] = None
    isCustom: bool = False
    isEnabled: bool = True
    createdAt: datetime
    updatedAt: Optional[datetime]
