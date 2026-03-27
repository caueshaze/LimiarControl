from __future__ import annotations

import re
import unicodedata
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.base_item import (
    BaseItemArmorCategory,
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
from app.services.item_properties import normalize_item_properties

DAMAGE_EXPRESSION_RE = re.compile(
    r"^\s*(?:(\d*)d(\d+)|(\d+))\s*(?:([+-])\s*(\d+))?\s*$",
    re.IGNORECASE,
)
ITEM_DAMAGE_TYPE_MAP = {
    value.value.lower(): value.value for value in BaseItemDamageType
}
ITEM_DEX_BONUS_RULE_MAP = {
    "full": BaseItemDexBonusRule.FULL.value,
    "unlimited": BaseItemDexBonusRule.FULL.value,
    "0": BaseItemDexBonusRule.NONE.value,
    "max_0": BaseItemDexBonusRule.NONE.value,
    "max 0": BaseItemDexBonusRule.NONE.value,
    "max_2": BaseItemDexBonusRule.MAX_2.value,
    "max 2": BaseItemDexBonusRule.MAX_2.value,
    "none": BaseItemDexBonusRule.NONE.value,
}
ITEM_SOURCE_MAP = {
    value.value: value.value for value in BaseItemSource
}
ITEM_SOURCE_MAP.update(
    {
        "csv": BaseItemSource.SEED_JSON_BOOTSTRAP.value,
        "csv_import": BaseItemSource.SEED_JSON_BOOTSTRAP.value,
        "seed": BaseItemSource.SEED_JSON_BOOTSTRAP.value,
    }
)
WEAPON_PROPERTY_SLUGS = {
    BaseItemProperty.AMMUNITION.value,
    BaseItemProperty.FINESSE.value,
    BaseItemProperty.HEAVY.value,
    BaseItemProperty.LIGHT.value,
    BaseItemProperty.LOADING.value,
    BaseItemProperty.RANGE.value,
    BaseItemProperty.REACH.value,
    BaseItemProperty.SPECIAL.value,
    BaseItemProperty.THROWN.value,
    BaseItemProperty.TWO_HANDED.value,
    BaseItemProperty.VERSATILE.value,
}


def _raw_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _normalize_slug(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    collapsed = re.sub(r"[^a-z0-9]+", "_", normalized.lower())
    return re.sub(r"_+", "_", collapsed).strip("_")


class BaseItemAliasRead(BaseModel):
    id: str
    alias: str
    locale: Optional[str] = None
    aliasType: Optional[str] = None


class BaseItemWrite(BaseModel):
    system: SystemType = SystemType.DND5E
    canonicalKey: str
    nameEn: Optional[str] = None
    namePt: Optional[str] = None
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
    rangeNormalMeters: Optional[int] = None
    rangeLongMeters: Optional[int] = None
    versatileDamage: Optional[str] = None
    weaponPropertiesJson: list[BaseItemProperty] = Field(default_factory=list)
    armorCategory: Optional[BaseItemArmorCategory] = None
    armorClassBase: Optional[int] = None
    dexBonusRule: Optional[BaseItemDexBonusRule] = None
    strengthRequirement: Optional[int] = None
    stealthDisadvantage: bool = False
    isShield: bool = False
    source: BaseItemSource = BaseItemSource.ADMIN_PANEL
    sourceRef: Optional[str] = None
    isSrd: bool = False
    isActive: bool = True

    @field_validator("canonicalKey")
    @classmethod
    def normalize_canonical_key(cls, value: str):
        normalized = _normalize_slug(value)
        if not normalized:
            raise ValueError("canonicalKey cannot be blank")
        return normalized

    @field_validator("nameEn", "namePt", "descriptionEn", "descriptionPt", "sourceRef", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]):
        if value is None:
            return None
        normalized = _raw_value(value).strip()
        return normalized or None

    @field_validator("equipmentCategory", mode="before")
    @classmethod
    def normalize_equipment_category(cls, value: Optional[str]):
        if value is None:
            return None
        if isinstance(value, BaseItemEquipmentCategory):
            return value.value
        normalized = _normalize_slug(_raw_value(value))
        return normalized or None

    @field_validator("costQuantity", "weight")
    @classmethod
    def validate_non_negative_numbers(cls, value: Optional[float]):
        if value is None:
            return None
        if value < 0:
            raise ValueError("Value cannot be negative")
        return value

    @field_validator("rangeNormalMeters", "rangeLongMeters", "armorClassBase")
    @classmethod
    def validate_non_negative_ints(cls, value: Optional[int]):
        if value is None:
            return None
        if value < 0:
            raise ValueError("Value cannot be negative")
        return value

    @field_validator("strengthRequirement")
    @classmethod
    def normalize_strength_requirement(cls, value: Optional[int]):
        if value is None or value == 0:
            return None
        if value < 0:
            raise ValueError("Value cannot be negative")
        return value

    @field_validator("damageDice", "versatileDamage")
    @classmethod
    def validate_damage_expression(cls, value: Optional[str]):
        if value is None:
            return None
        normalized = value.strip().lower().replace(" ", "")
        if not normalized:
            return None
        if normalized == "-":
            return None
        if DAMAGE_EXPRESSION_RE.match(normalized) is None:
            raise ValueError("Invalid damage expression")
        if normalized.isdigit():
            return normalized
        return normalized

    @field_validator("damageType", mode="before")
    @classmethod
    def normalize_damage_type(cls, value: Optional[str | BaseItemDamageType]):
        if value is None:
            return None
        if isinstance(value, BaseItemDamageType):
            return value
        canonical = ITEM_DAMAGE_TYPE_MAP.get(_raw_value(value).strip().lower())
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
        canonical = ITEM_DEX_BONUS_RULE_MAP.get(_raw_value(value).strip().lower())
        if canonical is None:
            raise ValueError(f"Unknown dex bonus rule: {value}")
        return canonical

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value: Optional[str]):
        if value is None:
            return BaseItemSource.ADMIN_PANEL.value
        if isinstance(value, BaseItemSource):
            return value
        canonical = ITEM_SOURCE_MAP.get(_normalize_slug(_raw_value(value)))
        if canonical is None:
            raise ValueError(f"Unknown source: {value}")
        return canonical

    @field_validator("weaponPropertiesJson", mode="before")
    @classmethod
    def normalize_weapon_properties_field(cls, value: object):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("weaponPropertiesJson must be a list")
        normalized_properties, invalid_properties = normalize_item_properties(value)
        if invalid_properties:
            raise ValueError(
                f"Invalid weapon properties: {', '.join(invalid_properties)}"
            )
        return normalized_properties

    @model_validator(mode="after")
    def validate_item_shape(self):
        if not self.nameEn and not self.namePt:
            raise ValueError("At least one name is required")
        if not self.nameEn:
            self.nameEn = self.namePt
        if not self.namePt:
            self.namePt = self.nameEn
        if not self.descriptionEn:
            self.descriptionEn = self.descriptionPt
        if not self.descriptionPt:
            self.descriptionPt = self.descriptionEn

        unsupported_weapon_properties = [
            property_value.value
            for property_value in self.weaponPropertiesJson
            if property_value.value not in WEAPON_PROPERTY_SLUGS
        ]
        if unsupported_weapon_properties:
            raise ValueError(
                "weaponPropertiesJson only accepts weapon properties"
            )

        if self.costQuantity is None:
            self.costUnit = None
        elif self.costUnit is None:
            raise ValueError("costUnit is required when costQuantity is provided")

        if self.rangeLongMeters is not None and self.rangeNormalMeters is None:
            raise ValueError("rangeLongMeters requires rangeNormalMeters")
        if (
            self.rangeNormalMeters is not None
            and self.rangeLongMeters is not None
            and self.rangeLongMeters < self.rangeNormalMeters
        ):
            raise ValueError("rangeLongMeters cannot be smaller than rangeNormalMeters")

        if self.itemKind == BaseItemKind.WEAPON:
            if self.weaponCategory is None or self.weaponRangeType is None:
                raise ValueError("Weapons must define weapon category and range type")
            if self.damageDice is not None and self.damageType is None:
                raise ValueError("Weapons with damageDice must define damageType")
            if self.damageType is not None and self.damageDice is None:
                raise ValueError("Weapons with damageType must define damageDice")
            has_ranged_profile = self.weaponRangeType == BaseItemWeaponRangeType.RANGED
            has_thrown_property = BaseItemProperty.THROWN in self.weaponPropertiesJson
            if self.rangeNormalMeters is None:
                raise ValueError("Weapons must define rangeNormalMeters")
            if (
                self.rangeLongMeters is not None
                and not has_ranged_profile
                and not has_thrown_property
                and self.rangeLongMeters != self.rangeNormalMeters
            ):
                raise ValueError(
                    "rangeLongMeters can only differ from rangeNormalMeters for ranged weapons or thrown weapons"
                )
            if (
                self.versatileDamage is not None
                and BaseItemProperty.VERSATILE not in self.weaponPropertiesJson
            ):
                raise ValueError(
                    "versatileDamage requires the versatile weapon property"
                )
            self.armorCategory = None
            self.armorClassBase = None
            self.dexBonusRule = None
            self.strengthRequirement = None
            self.stealthDisadvantage = False
            self.isShield = False
        else:
            self.weaponCategory = None
            self.weaponRangeType = None
            self.damageDice = None
            self.damageType = None
            self.rangeNormalMeters = None
            self.rangeLongMeters = None
            self.versatileDamage = None
            self.weaponPropertiesJson = []

        if self.itemKind == BaseItemKind.ARMOR:
            if self.armorCategory is None or self.armorClassBase is None:
                raise ValueError("Armor must define armorCategory and armorClassBase")
            self.isShield = self.armorCategory == BaseItemArmorCategory.SHIELD
            if self.isShield:
                self.dexBonusRule = None
                self.strengthRequirement = None
                self.stealthDisadvantage = False
            elif self.dexBonusRule is None:
                raise ValueError("Non-shield armor must define dexBonusRule")
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
            self.stealthDisadvantage = False
            self.isShield = False

        return self


class BaseItemCreate(BaseItemWrite):
    pass


class BaseItemUpdate(BaseItemWrite):
    pass


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
    rangeNormalMeters: Optional[int] = None
    rangeLongMeters: Optional[int] = None
    versatileDamage: Optional[str] = None
    weaponPropertiesJson: list[BaseItemProperty] = Field(default_factory=list)
    armorCategory: Optional[BaseItemArmorCategory] = None
    armorClassBase: Optional[int] = None
    dexBonusRule: Optional[BaseItemDexBonusRule] = None
    strengthRequirement: Optional[int] = None
    stealthDisadvantage: Optional[bool] = None
    isShield: bool
    source: BaseItemSource
    sourceRef: Optional[str] = None
    isSrd: bool
    isActive: bool
    aliases: list[BaseItemAliasRead] = Field(default_factory=list)


class BaseItemSeedDocument(BaseModel):
    version: int = 1
    items: list[BaseItemCreate]

    @model_validator(mode="after")
    def validate_unique_items(self):
        seen: set[tuple[str, str]] = set()
        for item in self.items:
            key = (item.system.value, item.canonicalKey)
            if key in seen:
                raise ValueError(
                    f"Duplicate seed entry for {item.system.value}:{item.canonicalKey}"
                )
            seen.add(key)
        return self
