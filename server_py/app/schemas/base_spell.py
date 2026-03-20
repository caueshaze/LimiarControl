from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.base_spell import SpellSchool
from app.models.campaign import SystemType

SPELL_CLASS_VALUES = (
    "Bard",
    "Cleric",
    "Druid",
    "Paladin",
    "Ranger",
    "Sorcerer",
    "Warlock",
    "Wizard",
)
SPELL_COMPONENT_VALUES = ("V", "S", "M")
SPELL_DAMAGE_TYPE_VALUES = (
    "Acid",
    "Bludgeoning",
    "Cold",
    "Fire",
    "Force",
    "Lightning",
    "Necrotic",
    "Piercing",
    "Poison",
    "Psychic",
    "Radiant",
    "Slashing",
    "Thunder",
)
SPELL_SAVING_THROW_VALUES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

SPELL_CLASS_MAP = {value.lower(): value for value in SPELL_CLASS_VALUES}
SPELL_COMPONENT_MAP = {value.lower(): value for value in SPELL_COMPONENT_VALUES}
SPELL_DAMAGE_TYPE_MAP = {value.lower(): value for value in SPELL_DAMAGE_TYPE_VALUES}
SPELL_SAVING_THROW_MAP = {value.lower(): value for value in SPELL_SAVING_THROW_VALUES}


class BaseSpellAliasRead(BaseModel):
    id: str
    alias: str
    locale: Optional[str] = None
    aliasType: Optional[str] = None


class BaseSpellUpdate(BaseModel):
    nameEn: Optional[str] = None
    namePt: Optional[str] = None
    descriptionEn: Optional[str] = None
    descriptionPt: Optional[str] = None
    level: Optional[int] = None
    school: Optional[SpellSchool] = None
    classesJson: Optional[list[str]] = None
    castingTime: Optional[str] = None
    rangeText: Optional[str] = None
    duration: Optional[str] = None
    componentsJson: Optional[list[str]] = None
    materialComponentText: Optional[str] = None
    concentration: Optional[bool] = None
    ritual: Optional[bool] = None
    damageType: Optional[str] = None
    savingThrow: Optional[str] = None

    @field_validator(
        "nameEn",
        "descriptionEn",
        mode="before",
    )
    @classmethod
    def normalize_required_text_fields(cls, value: Optional[str]):
        if value is None:
            raise ValueError("Field cannot be blank")
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank")
        return normalized

    @field_validator(
        "namePt",
        "castingTime",
        "rangeText",
        "duration",
        "materialComponentText",
        "descriptionPt",
        "damageType",
        "savingThrow",
        mode="before",
    )
    @classmethod
    def normalize_optional_text_fields(cls, value: Optional[str]):
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("descriptionEn")
    @classmethod
    def validate_required_text(cls, value: Optional[str]):
        if value is None:
            raise ValueError("Field cannot be blank")
        return value

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: Optional[int]):
        if value is None:
            return value
        if value < 0 or value > 9:
            raise ValueError("Spell level must be between 0 and 9")
        return value

    @field_validator("classesJson", mode="before")
    @classmethod
    def normalize_spell_classes(cls, value: Optional[list[str]]):
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("classesJson must be a list")

        normalized: list[str] = []
        seen: set[str] = set()
        for entry in value:
            if entry is None:
                continue
            text = str(entry).strip()
            if not text:
                continue
            canonical = SPELL_CLASS_MAP.get(text.lower())
            if canonical is None:
                raise ValueError(f"Unknown spell class: {text}")
            if canonical in seen:
                continue
            seen.add(canonical)
            normalized.append(canonical)

        return normalized or None

    @field_validator("componentsJson", mode="before")
    @classmethod
    def normalize_spell_components(cls, value: Optional[list[str]]):
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("componentsJson must be a list")

        normalized: list[str] = []
        seen: set[str] = set()
        for entry in value:
            if entry is None:
                continue
            text = str(entry).strip()
            if not text:
                continue
            canonical = SPELL_COMPONENT_MAP.get(text.lower())
            if canonical is None:
                raise ValueError(f"Unknown spell component: {text}")
            if canonical in seen:
                continue
            seen.add(canonical)
            normalized.append(canonical)

        return normalized or None

    @field_validator("damageType")
    @classmethod
    def normalize_damage_type(cls, value: Optional[str]):
        if value is None:
            return None
        canonical = SPELL_DAMAGE_TYPE_MAP.get(value.lower())
        if canonical is None:
            raise ValueError(f"Unknown damage type: {value}")
        return canonical

    @field_validator("savingThrow")
    @classmethod
    def normalize_saving_throw(cls, value: Optional[str]):
        if value is None:
            return None
        canonical = SPELL_SAVING_THROW_MAP.get(value.lower())
        if canonical is None:
            raise ValueError(f"Unknown saving throw: {value}")
        return canonical

    @model_validator(mode="after")
    def clear_material_without_material_component(self):
        if not self.componentsJson or "M" not in self.componentsJson:
            self.materialComponentText = None
        return self


class BaseSpellRead(BaseModel):
    id: str
    system: SystemType
    canonicalKey: str
    nameEn: str
    namePt: Optional[str] = None
    descriptionEn: str
    descriptionPt: Optional[str] = None
    level: int
    school: SpellSchool
    classesJson: Optional[Any] = None
    castingTime: Optional[str] = None
    rangeText: Optional[str] = None
    duration: Optional[str] = None
    componentsJson: Optional[Any] = None
    materialComponentText: Optional[str] = None
    concentration: bool
    ritual: bool
    damageType: Optional[str] = None
    savingThrow: Optional[str] = None
    source: Optional[str] = None
    sourceRef: Optional[str] = None
    isSrd: bool
    isActive: bool
    aliases: list[BaseSpellAliasRead] = Field(default_factory=list)
