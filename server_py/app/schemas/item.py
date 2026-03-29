import re
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.base_item import (
    BaseItemArmorCategory,
    BaseItemCostUnit,
    BaseItemDamageType,
    BaseItemDexBonusRule,
    BaseItemKind,
    BaseItemWeaponCategory,
    BaseItemWeaponRangeType,
)
from app.models.item import ItemType
from app.services.item_properties import normalize_item_properties

DICE_EXPRESSION_RE = re.compile(
    r"^\s*(?:(\d*)d(\d+)|(\d+))\s*(?:([+-])\s*(\d+))?\s*$",
    re.IGNORECASE,
)
ITEM_DAMAGE_TYPE_MAP = {
    value.value.lower(): value.value for value in BaseItemDamageType
}
ITEM_DEX_BONUS_RULE_MAP = {
    "full": BaseItemDexBonusRule.FULL.value,
    "unlimited": BaseItemDexBonusRule.FULL.value,
    "max_2": BaseItemDexBonusRule.MAX_2.value,
    "max 2": BaseItemDexBonusRule.MAX_2.value,
    "none": BaseItemDexBonusRule.NONE.value,
}


def _raw_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _normalize_slug(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


MagicItemRechargeType = Literal["none", "short_rest", "long_rest", "dawn", "custom"]


class MagicItemCastSpellEffect(BaseModel):
    type: Literal["cast_spell"]
    spellCanonicalKey: str
    castLevel: int = Field(default=1, ge=0, le=9)
    ignoreComponents: bool = False
    noFreeHandRequired: bool = False

    @field_validator("spellCanonicalKey", mode="before")
    @classmethod
    def normalize_spell_canonical_key(cls, value: object):
        normalized = _normalize_slug(_raw_value(value))
        if not normalized:
            raise ValueError("spellCanonicalKey cannot be blank")
        return normalized


class ItemCreate(BaseModel):
    name: str
    type: ItemType
    description: str
    price: Optional[float] = None
    weight: Optional[float] = None
    damageDice: Optional[str] = None
    damageType: Optional[BaseItemDamageType] = None
    healDice: Optional[str] = None
    healBonus: Optional[int] = None
    chargesMax: Optional[int] = Field(default=None, ge=0)
    rechargeType: Optional[MagicItemRechargeType] = None
    magicEffect: Optional[MagicItemCastSpellEffect] = None
    rangeMeters: Optional[float] = None
    rangeLongMeters: Optional[float] = None
    versatileDamage: Optional[str] = None
    weaponCategory: Optional[BaseItemWeaponCategory] = None
    weaponRangeType: Optional[BaseItemWeaponRangeType] = None
    armorCategory: Optional[BaseItemArmorCategory] = None
    armorClassBase: Optional[int] = None
    dexBonusRule: Optional[BaseItemDexBonusRule] = None
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

    @field_validator("damageDice", "healDice", "versatileDamage", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]):
        if value is None:
            return None
        normalized = _raw_value(value).strip()
        return normalized or None

    @field_validator("price", "weight", "rangeMeters", "rangeLongMeters")
    @classmethod
    def validate_non_negative_numbers(cls, value: Optional[float]):
        if value is None:
            return None
        if value < 0:
            raise ValueError("Value cannot be negative")
        return value

    @field_validator("armorClassBase", "strengthRequirement", "healBonus")
    @classmethod
    def validate_non_negative_ints(cls, value: Optional[int]):
        if value is None:
            return None
        if value < 0:
            raise ValueError("Value cannot be negative")
        return value

    @field_validator("damageDice", "healDice", "versatileDamage")
    @classmethod
    def validate_dice_expression(cls, value: Optional[str]):
        if value is None:
            return None
        if DICE_EXPRESSION_RE.match(value) is None:
            raise ValueError("Invalid dice expression")
        return value.lower().replace(" ", "")

    @field_validator("damageType", mode="before")
    @classmethod
    def normalize_damage_type(cls, value: Optional[str | BaseItemDamageType]):
        if value is None:
            return None
        if isinstance(value, BaseItemDamageType):
            return value
        canonical = ITEM_DAMAGE_TYPE_MAP.get(_raw_value(value).lower())
        if canonical is None:
            raise ValueError(f"Unknown damage type: {value}")
        return canonical

    @field_validator("dexBonusRule", mode="before")
    @classmethod
    def normalize_dex_bonus_rule(cls, value: Optional[str | BaseItemDexBonusRule]):
        if value is None:
            return None
        if isinstance(value, BaseItemDexBonusRule):
            return value
        canonical = ITEM_DEX_BONUS_RULE_MAP.get(_raw_value(value).lower())
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
        normalized_properties, invalid_properties = normalize_item_properties(self.properties)
        if invalid_properties:
            raise ValueError(f"Invalid item properties: {', '.join(invalid_properties)}")
        self.properties = normalized_properties

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
            has_ranged_profile = self.weaponRangeType == BaseItemWeaponRangeType.RANGED
            has_thrown_property = "thrown" in self.properties
            if self.rangeMeters is None:
                raise ValueError("Weapons must define range")
            if (
                self.rangeLongMeters is not None
                and not has_ranged_profile
                and not has_thrown_property
                and self.rangeLongMeters != self.rangeMeters
            ):
                raise ValueError(
                    "Long range can only differ from range for ranged weapons or thrown weapons"
                )
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

        if self.type == ItemType.CONSUMABLE:
            pass
        elif self.healDice is not None or self.healBonus is not None:
            raise ValueError("Only consumables can define healDice or healBonus")
        else:
            self.healDice = None
            self.healBonus = None

        if self.chargesMax is None:
            self.rechargeType = None
        elif self.rechargeType is None:
            raise ValueError("rechargeType is required when chargesMax is provided")

        if self.magicEffect is not None and self.chargesMax is None:
            raise ValueError("chargesMax is required when magicEffect is provided")
        if self.magicEffect is not None and self.type != ItemType.MAGIC:
            raise ValueError("magicEffect requires item type MAGIC")

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
            if self.isShield:
                self.dexBonusRule = None
                self.strengthRequirement = None
                self.stealthDisadvantage = False
            elif self.stealthDisadvantage:
                self.properties.append("stealth_disadvantage")
            if (
                self.strengthRequirement is not None
                and self.armorCategory != BaseItemArmorCategory.HEAVY
            ):
                raise ValueError(
                    "strengthRequirement only applies to heavy armor"
                )
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
    damageType: Optional[BaseItemDamageType]
    healDice: Optional[str]
    healBonus: Optional[int]
    chargesMax: Optional[int] = None
    rechargeType: Optional[MagicItemRechargeType] = None
    magicEffect: Optional[MagicItemCastSpellEffect] = None
    rangeMeters: Optional[float]
    rangeLongMeters: Optional[float]
    versatileDamage: Optional[str]
    weaponCategory: Optional[BaseItemWeaponCategory] = None
    weaponRangeType: Optional[BaseItemWeaponRangeType] = None
    armorCategory: Optional[BaseItemArmorCategory] = None
    armorClassBase: Optional[int] = None
    dexBonusRule: Optional[BaseItemDexBonusRule] = None
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
