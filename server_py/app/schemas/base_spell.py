from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.base_spell import (
    CastingTimeType,
    ResolutionType,
    SpellSchool,
    SpellSource,
    TargetMode,
    UpcastMode,
)
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
SPELL_SAVE_SUCCESS_OUTCOME_VALUES = ("none", "half_damage")

SPELL_CLASS_MAP = {value.lower(): value for value in SPELL_CLASS_VALUES}
SPELL_COMPONENT_MAP = {value.lower(): value for value in SPELL_COMPONENT_VALUES}
SPELL_DAMAGE_TYPE_MAP = {value.lower(): value for value in SPELL_DAMAGE_TYPE_VALUES}
SPELL_SAVING_THROW_MAP = {value.lower(): value for value in SPELL_SAVING_THROW_VALUES}
SPELL_SAVE_SUCCESS_OUTCOME_MAP = {
    value.lower(): value for value in SPELL_SAVE_SUCCESS_OUTCOME_VALUES
}

CASTING_TIME_TYPE_MAP = {member.value: member.value for member in CastingTimeType}
TARGET_MODE_MAP = {member.value: member.value for member in TargetMode}
RESOLUTION_TYPE_MAP = {member.value: member.value for member in ResolutionType}
UPCAST_MODE_MAP = {member.value: member.value for member in UpcastMode}
SPELL_SOURCE_MAP = {member.value: member.value for member in SpellSource}
SPELL_SOURCE_MAP.update({
    "csv": SpellSource.SEED_JSON_BOOTSTRAP.value,
    "csv_import": SpellSource.SEED_JSON_BOOTSTRAP.value,
    "seed": SpellSource.SEED_JSON_BOOTSTRAP.value,
})

DICE_EXPRESSION_RE = re.compile(
    r"^\s*(?:(\d*)d(\d+)|(\d+))\s*(?:([+-])\s*(\d+))?\s*$",
    re.IGNORECASE,
)

_CANONICAL_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_]*[a-z0-9]$|^[a-z0-9]$")


def _normalize_canonical_key(value: str) -> str:
    text = value.strip()
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug


class BaseSpellAliasRead(BaseModel):
    id: str
    alias: str
    locale: Optional[str] = None
    aliasType: Optional[str] = None


# ---------------------------------------------------------------------------
# Write schema (shared by Create and Update)
# ---------------------------------------------------------------------------

class BaseSpellWrite(BaseModel):
    nameEn: Optional[str] = None
    namePt: Optional[str] = None
    descriptionEn: Optional[str] = None
    descriptionPt: Optional[str] = None
    level: Optional[int] = None
    school: Optional[SpellSchool] = None
    classesJson: Optional[list[str]] = None

    # Casting
    castingTimeType: Optional[str] = None
    castingTime: Optional[str] = None
    rangeMeters: Optional[int] = None
    rangeText: Optional[str] = None
    targetMode: Optional[str] = None
    duration: Optional[str] = None
    componentsJson: Optional[list[str]] = None
    materialComponentText: Optional[str] = None
    concentration: Optional[bool] = None
    ritual: Optional[bool] = None

    # Resolution
    resolutionType: Optional[str] = None
    savingThrow: Optional[str] = None
    saveSuccessOutcome: Optional[str] = None

    # Effect
    damageDice: Optional[str] = None
    damageType: Optional[str] = None
    healDice: Optional[str] = None

    # Upcast
    upcastMode: Optional[str] = None
    upcastValue: Optional[str] = None

    # Metadata
    source: Optional[str] = None
    sourceRef: Optional[str] = None
    isSrd: Optional[bool] = None
    isActive: Optional[bool] = None

    # --- Field validators ---

    @field_validator("nameEn", "descriptionEn", mode="before")
    @classmethod
    def normalize_required_text_fields(cls, value: Optional[str]):
        if value is None:
            return None
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
        "sourceRef",
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

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: Optional[int]):
        if value is None:
            return value
        if value < 0 or value > 9:
            raise ValueError("Spell level must be between 0 and 9")
        return value

    @field_validator("rangeMeters")
    @classmethod
    def validate_range_meters(cls, value: Optional[int]):
        if value is None:
            return None
        if value < 0:
            raise ValueError("rangeMeters cannot be negative")
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
        text = value.strip()
        if not text:
            return None
        canonical = SPELL_DAMAGE_TYPE_MAP.get(text.lower())
        if canonical is None:
            raise ValueError(f"Unknown damage type: {value}")
        return canonical

    @field_validator("savingThrow")
    @classmethod
    def normalize_saving_throw(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        canonical = SPELL_SAVING_THROW_MAP.get(text.lower())
        if canonical is None:
            raise ValueError(f"Unknown saving throw ability: {value}")
        return canonical

    @field_validator("saveSuccessOutcome")
    @classmethod
    def normalize_save_success_outcome(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        canonical = SPELL_SAVE_SUCCESS_OUTCOME_MAP.get(text.lower())
        if canonical is None:
            raise ValueError(f"Unknown save success outcome: {value}")
        return canonical

    @field_validator("castingTimeType")
    @classmethod
    def normalize_casting_time_type(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in CASTING_TIME_TYPE_MAP:
            raise ValueError(f"Unknown casting time type: {value}")
        return text

    @field_validator("targetMode")
    @classmethod
    def normalize_target_mode(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in TARGET_MODE_MAP:
            raise ValueError(f"Unknown target mode: {value}")
        return text

    @field_validator("resolutionType")
    @classmethod
    def normalize_resolution_type(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in RESOLUTION_TYPE_MAP:
            raise ValueError(f"Unknown resolution type: {value}")
        return text

    @field_validator("upcastMode")
    @classmethod
    def normalize_upcast_mode(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in UPCAST_MODE_MAP:
            raise ValueError(f"Unknown upcast mode: {value}")
        return text

    @field_validator("upcastValue")
    @classmethod
    def normalize_upcast_value(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("damageDice", "healDice")
    @classmethod
    def validate_dice_expression(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if not DICE_EXPRESSION_RE.match(text):
            raise ValueError(f"Invalid dice expression: {value}")
        return text

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        canonical = SPELL_SOURCE_MAP.get(text)
        if canonical is None:
            raise ValueError(f"Unknown source: {value}")
        return canonical

    # --- Cross-field validation ---

    @model_validator(mode="after")
    def cross_field_validation(self):
        # Clear material text if no M component
        if not self.componentsJson or "M" not in self.componentsJson:
            self.materialComponentText = None

        # Resolution type coherence
        if self.resolutionType == ResolutionType.SAVING_THROW.value:
            if self.savingThrow is None:
                raise ValueError(
                    "savingThrow is required when resolutionType is 'saving_throw'"
                )
        elif self.resolutionType is not None:
            # Clear saving throw fields for non-saving-throw resolutions
            self.savingThrow = None
            self.saveSuccessOutcome = None

        # Clear save outcome if no saving throw
        if self.savingThrow is None:
            self.saveSuccessOutcome = None

        # Resolution type: heal requires heal_dice
        if self.resolutionType == ResolutionType.HEAL.value:
            if self.healDice is None:
                raise ValueError(
                    "healDice is required when resolutionType is 'heal'"
                )

        # Upcast coherence
        if self.upcastMode == UpcastMode.NONE.value:
            self.upcastValue = None

        return self


# ---------------------------------------------------------------------------
# Create schema (adds required identity fields)
# ---------------------------------------------------------------------------

class BaseSpellCreate(BaseSpellWrite):
    system: SystemType = SystemType.DND5E
    canonicalKey: str

    # Override: these are required on creation
    nameEn: str  # type: ignore[assignment]
    descriptionEn: str  # type: ignore[assignment]
    level: int  # type: ignore[assignment]
    school: SpellSchool  # type: ignore[assignment]

    @field_validator("canonicalKey", mode="before")
    @classmethod
    def normalize_canonical_key(cls, value: str):
        if not isinstance(value, str):
            raise ValueError("canonicalKey must be a string")
        normalized = _normalize_canonical_key(value)
        if not normalized:
            raise ValueError("canonicalKey cannot be empty")
        if not _CANONICAL_KEY_RE.match(normalized):
            raise ValueError(f"Invalid canonical key format: {normalized}")
        return normalized

    @field_validator("nameEn", "descriptionEn", mode="before")
    @classmethod
    def require_text(cls, value: Optional[str]):
        if value is None:
            raise ValueError("Field cannot be blank")
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be blank")
        return normalized

    @model_validator(mode="after")
    def ensure_name_fallback(self):
        if not self.namePt:
            self.namePt = self.nameEn
        return self


# ---------------------------------------------------------------------------
# Update schema (all optional, for partial updates)
# ---------------------------------------------------------------------------

class BaseSpellUpdate(BaseSpellWrite):
    pass


# ---------------------------------------------------------------------------
# Read schema
# ---------------------------------------------------------------------------

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

    # Casting
    castingTimeType: Optional[str] = None
    castingTime: Optional[str] = None
    rangeMeters: Optional[int] = None
    rangeText: Optional[str] = None
    targetMode: Optional[str] = None
    duration: Optional[str] = None
    componentsJson: Optional[Any] = None
    materialComponentText: Optional[str] = None
    concentration: bool
    ritual: bool

    # Resolution
    resolutionType: Optional[str] = None
    savingThrow: Optional[str] = None
    saveSuccessOutcome: Optional[str] = None

    # Effect
    damageDice: Optional[str] = None
    damageType: Optional[str] = None
    healDice: Optional[str] = None

    # Upcast
    upcastMode: Optional[str] = None
    upcastValue: Optional[str] = None

    # Metadata
    source: Optional[str] = None
    sourceRef: Optional[str] = None
    isSrd: bool
    isActive: bool
    aliases: list[BaseSpellAliasRead] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Seed document
# ---------------------------------------------------------------------------

class BaseSpellSeedDocument(BaseModel):
    version: int = 1
    spells: list[BaseSpellCreate]

    @model_validator(mode="after")
    def reject_duplicate_entries(self):
        seen: set[str] = set()
        for spell in self.spells:
            key = f"{spell.system.value}:{spell.canonicalKey}"
            if key in seen:
                raise ValueError(f"Duplicate seed entry: {key}")
            seen.add(key)
        return self
