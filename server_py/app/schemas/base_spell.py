from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal, Optional

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
# Legacy aliases for resolution type
RESOLUTION_TYPE_MAP.update({
    "none": "none",
    "spell_attack": "spell_attack",
    "saving_throw": "saving_throw",
    "automatic": "automatic",
})
UPCAST_MODE_MAP = {member.value: member.value for member in UpcastMode}
# Legacy aliases
UPCAST_MODE_MAP.update({
    "add_dice": "add_dice",
    "add_damage": "add_damage",
    "add_heal": "add_heal",
    "increase_targets": "increase_targets",
    "increase_duration": "increase_duration",
    "custom": "custom",
})
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


SpellUpcastMode = Literal[
    "extra_damage_dice",
    "extra_heal_dice",
    "flat_bonus",
    "additional_targets",
    "duration_scaling",
    "effect_scaling",
    "extra_effect",
]


class SpellUpcastConfig(BaseModel):
    mode: SpellUpcastMode
    dice: Optional[str] = None
    flat: Optional[int] = Field(default=None, ge=0)
    perLevel: int = Field(default=1, ge=1)
    maxLevel: Optional[int] = Field(default=None, ge=1, le=9)
    # Structured fields for effect_scaling
    scalingKey: Optional[str] = None
    scalingSummary: Optional[str] = None
    scalingEditorial: Optional[str] = None
    # Structured fields for extra_effect
    unlockKey: Optional[str] = None
    unlockSummary: Optional[str] = None
    unlockEditorial: Optional[str] = None

    @field_validator("dice")
    @classmethod
    def validate_upcast_dice_expression(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if not DICE_EXPRESSION_RE.match(text):
            raise ValueError(f"Invalid dice expression: {value}")
        return text

    @field_validator("scalingKey", "scalingSummary", "scalingEditorial", "unlockKey", "unlockSummary", "unlockEditorial", mode="before")
    @classmethod
    def normalize_structured_text(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        return text or None

    @model_validator(mode="after")
    def validate_upcast_shape(self):
        needs_dice_or_flat = {"extra_damage_dice", "extra_heal_dice"}
        if self.mode in needs_dice_or_flat and self.dice is None and self.flat is None:
            raise ValueError(f"Upcast mode '{self.mode}' requires dice and/or flat.")
        if self.mode == "flat_bonus" and self.flat is None:
            raise ValueError("Upcast mode 'flat_bonus' requires a flat value.")
        if self.maxLevel is not None and self.maxLevel < 1:
            raise ValueError("Structured upcast maxLevel must be at least 1.")
        if self.mode == "effect_scaling":
            if not self.scalingKey:
                raise ValueError("Upcast mode 'effect_scaling' requires scalingKey.")
            if not self.scalingSummary:
                raise ValueError("Upcast mode 'effect_scaling' requires scalingSummary.")
        if self.mode == "extra_effect":
            if not self.unlockKey:
                raise ValueError("Upcast mode 'extra_effect' requires unlockKey.")
            if not self.unlockSummary:
                raise ValueError("Upcast mode 'extra_effect' requires unlockSummary.")
        return self


def _build_structured_upcast_from_legacy(
    *,
    upcast_mode: str | None,
    upcast_value: str | None,
    resolution_type: str | None,
) -> SpellUpcastConfig | None:
    normalized_mode = (upcast_mode or "").strip()
    normalized_value = (upcast_value or "").strip() or None
    if not normalized_mode or normalized_mode == "none":
        return None

    # New modes passed directly via legacy upcastMode field
    NEW_MODES_NEEDING_DICE: set[str] = {"extra_damage_dice", "extra_heal_dice"}
    NEW_MODES_NEEDING_FLAT: set[str] = {"flat_bonus"}
    NEW_MODES_NO_DICE: set[str] = {"additional_targets", "duration_scaling", "effect_scaling", "extra_effect"}

    if normalized_mode in NEW_MODES_NEEDING_DICE:
        if not normalized_value:
            raise ValueError(f"upcastMode '{normalized_mode}' requires upcastValue (dice expression).")
        return SpellUpcastConfig(mode=normalized_mode, dice=normalized_value, perLevel=1)  # type: ignore[arg-type]
    if normalized_mode in NEW_MODES_NEEDING_FLAT:
        flat_val = int(normalized_value) if normalized_value and normalized_value.isdigit() else None
        if flat_val is None:
            raise ValueError("flat_bonus requires integer upcastValue.")
        return SpellUpcastConfig(mode="flat_bonus", flat=flat_val, perLevel=1)
    if normalized_mode in NEW_MODES_NO_DICE:
        per_level = 1
        if normalized_value and normalized_value.isdigit():
            per_level = int(normalized_value)
        return SpellUpcastConfig(mode=normalized_mode, perLevel=per_level)  # type: ignore[arg-type]

    # Legacy values
    if normalized_mode in ("add_dice", "add_damage", "add_heal"):
        if not normalized_value:
            raise ValueError(f"Legacy upcast '{normalized_mode}' requires upcastValue.")
        structured_mode: SpellUpcastMode = (
            "extra_heal_dice"
            if resolution_type == "heal" or normalized_mode == "add_heal"
            else "extra_damage_dice"
        )
        return SpellUpcastConfig(mode=structured_mode, dice=normalized_value, perLevel=1)
    if normalized_mode in ("add_targets", "increase_targets"):
        per_level = 1
        if normalized_value is not None:
            if not normalized_value.isdigit():
                raise ValueError("Legacy add_targets upcastValue must be a positive integer.")
            per_level = int(normalized_value)
            if per_level <= 0:
                raise ValueError("Legacy add_targets upcastValue must be positive.")
        return SpellUpcastConfig(mode="additional_targets", perLevel=per_level)
    if normalized_mode == "increase_duration":
        return SpellUpcastConfig(mode="duration_scaling", perLevel=1)
    if normalized_mode == "custom":
        return SpellUpcastConfig(mode="extra_effect", perLevel=1)
    raise ValueError(f"Unsupported upcast mode: {upcast_mode}")


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
    upcast: Optional[SpellUpcastConfig] = None
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

        # Build structured upcast from legacy fields if needed
        if self.upcast is None and self.upcastMode is not None:
            self.upcast = _build_structured_upcast_from_legacy(
                upcast_mode=self.upcastMode,
                upcast_value=self.upcastValue,
                resolution_type=self.resolutionType,
            )

        # Resolution type rules
        rt = self.resolutionType
        CAN_HAVE_SAVING_THROW = {"damage", "control", "debuff"}
        NEVER_DAMAGE = {"heal", "buff", "debuff", "control", "utility"}

        # heal requires heal_dice
        if rt == "heal" and not self.healDice:
            raise ValueError("healDice is required when resolutionType is 'heal'.")

        # non-damage types must not have damage fields
        if rt in NEVER_DAMAGE:
            self.damageDice = None
            self.damageType = None

        # save_success_outcome only makes sense for damage + saving_throw
        if rt != "damage" or self.savingThrow is None:
            self.saveSuccessOutcome = None

        # Clear saving_throw for types where it doesn't belong
        if rt is not None and rt not in CAN_HAVE_SAVING_THROW:
            self.savingThrow = None

        # Upcast coherence
        if self.upcastMode == "none":
            self.upcastValue = None
        if self.upcast is not None:
            if self.upcast.mode == "extra_heal_dice" and rt != "heal":
                raise ValueError("Upcast 'extra_heal_dice' requires resolutionType 'heal'.")
            if self.upcast.mode == "extra_damage_dice" and rt != "damage":
                raise ValueError("Upcast 'extra_damage_dice' requires resolutionType 'damage'.")

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
    upcast: Optional[SpellUpcastConfig] = None
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
