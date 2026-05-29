from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from app.models.base_spell import SpellSchool
from app.models.campaign import SystemType

from .base_spell_constants import (
    CASTING_TIME_TYPE_MAP,
    DICE_EXPRESSION_RE,
    RESOLUTION_TYPE_MAP,
    SPELL_CLASS_MAP,
    SPELL_COMPONENT_MAP,
    SPELL_DAMAGE_TYPE_MAP,
    SPELL_ATTACK_MISS_OUTCOME_MAP,
    SPELL_SAVE_SUCCESS_OUTCOME_MAP,
    SPELL_SAVING_THROW_MAP,
    SPELL_SOURCE_MAP,
    AREA_SHAPE_MAP,
    SPELL_ATTACK_TYPE_MAP,
    SPELL_EFFECT_TIMING_MAP,
    SPELL_ORIGIN_TYPE_MAP,
    SPELL_RANGE_KIND_MAP,
    SPELL_SELECTION_TYPE_MAP,
    SPELL_TARGET_ANCHOR_MAP,
    TARGET_TYPE_MAP,
    UPCAST_MODE_MAP,
    _CANONICAL_KEY_RE,
    _normalize_canonical_key,
)
from .base_spell_upcast import SpellUpcastConfig, _build_structured_upcast_from_legacy
from .base_spell_cantrip_scaling import SpellCantripScalingConfig
from .base_spell_effects import AttackAdvantageCondition, SpellDeclarativeEffect
from .base_spell_persistent_area import SpellPersistentAreaEffect
from .base_spell_variants import SpellVariant


class BaseSpellWrite(BaseModel):
    nameEn: Optional[str] = None
    namePt: Optional[str] = None
    descriptionEn: Optional[str] = None
    descriptionPt: Optional[str] = None
    level: Optional[int] = None
    school: Optional[SpellSchool] = None
    classesJson: Optional[list[str]] = None

    castingTimeType: Optional[str] = None
    castingTime: Optional[str] = None
    rangeMeters: Optional[int] = None
    rangeText: Optional[str] = None
    targetType: Optional[str] = None
    maxTargets: Optional[int] = None
    selectionType: Optional[str] = None
    originType: Optional[str] = None
    targetAnchor: Optional[str] = None
    attackType: Optional[str] = None
    rangeKind: Optional[str] = None
    effectTiming: Optional[str] = None
    areaShape: Optional[str] = None
    radiusMeters: Optional[float] = None  # sphere, cylinder
    lengthMeters: Optional[float] = None  # cone, line
    sideMeters: Optional[float] = None    # cube
    duration: Optional[str] = None
    componentsJson: Optional[list[str]] = None
    materialComponentText: Optional[str] = None
    materialComponentConsumed: Optional[bool] = None
    consumableMaterialOptions: Optional[list[dict]] = None
    concentration: Optional[bool] = None
    ritual: Optional[bool] = None

    resolutionType: Optional[str] = None
    savingThrow: Optional[str] = None
    saveSuccessOutcome: Optional[str] = None
    attackMissOutcome: Optional[str] = None
    coverAppliesToSave: Optional[str] = None

    damageDice: Optional[str] = None
    damageType: Optional[str] = None
    healDice: Optional[str] = None
    effects: Optional[list[SpellDeclarativeEffect]] = None
    attackAdvantageCondition: Optional[AttackAdvantageCondition] = None
    onEndEffects: Optional[list[SpellDeclarativeEffect]] = None
    variants: Optional[list[SpellVariant]] = None
    persistentArea: Optional[SpellPersistentAreaEffect] = None

    requiresTargetSight: Optional[bool] = None
    requiresTargetHearing: Optional[bool] = None
    requiresTargetEffect: Optional[bool] = None
    requiresPointSight: Optional[bool] = None
    requiresPointEffect: Optional[bool] = None

    upcast: Optional[SpellUpcastConfig] = None
    upcastMode: Optional[str] = None
    upcastValue: Optional[str] = None
    cantripScaling: Optional[SpellCantripScalingConfig] = None

    source: Optional[str] = None
    sourceRef: Optional[str] = None
    isSrd: Optional[bool] = None
    isActive: Optional[bool] = None
    outOfCombatCastable: Optional[bool] = None
    outOfCombatTarget: Optional[str] = "self"

    @field_validator("outOfCombatTarget", mode="before")
    @classmethod
    def validate_out_of_combat_target(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return "self"
        allowed = {"self", "ally", "self_or_ally"}
        if value not in allowed:
            raise ValueError(f"outOfCombatTarget must be one of {sorted(allowed)}, got {value!r}")
        return value

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

    @field_validator("rangeMeters", mode="before")
    @classmethod
    def validate_range_meters(cls, value):
        if value is None:
            return None
        if isinstance(value, float):
            if value.is_integer():
                value = int(value)
            else:
                # Catalog compatibility: normalize decimal meter ranges into integer
                # storage without rejecting seed sync (e.g., 1.5m touch range).
                value = int(round(value))
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                parsed = float(value)
            except ValueError as exc:
                raise ValueError("rangeMeters must be numeric") from exc
            value = int(round(parsed))
        if not isinstance(value, int):
            raise ValueError("rangeMeters must be an integer")
        if value < 0:
            raise ValueError("rangeMeters cannot be negative")
        return value

    @field_validator("maxTargets")
    @classmethod
    def validate_max_targets(cls, value: Optional[int]):
        if value is None:
            return None
        if value < 1:
            raise ValueError("maxTargets must be at least 1")
        return value

    @field_validator("radiusMeters", "lengthMeters", "sideMeters")
    @classmethod
    def validate_explicit_dimension(cls, value: Optional[float]):
        if value is None:
            return None
        if value <= 0:
            raise ValueError("Area dimension must be greater than 0")
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

    @field_validator("attackMissOutcome")
    @classmethod
    def normalize_attack_miss_outcome(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        canonical = SPELL_ATTACK_MISS_OUTCOME_MAP.get(text.lower())
        if canonical is None:
            raise ValueError(f"Unknown attack miss outcome: {value}")
        return canonical

    @field_validator("coverAppliesToSave")
    @classmethod
    def normalize_cover_applies_to_save(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        from app.services.combat_service.cover_modifiers import COVER_SAVE_RULE_VALUES

        if text not in COVER_SAVE_RULE_VALUES:
            raise ValueError(
                f"Unknown coverAppliesToSave value: '{value}'. "
                f"Must be one of: {', '.join(COVER_SAVE_RULE_VALUES)}"
            )
        return text

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

    @field_validator("targetType")
    @classmethod
    def normalize_target_type(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in TARGET_TYPE_MAP:
            raise ValueError(f"Unknown target type: {value}")
        return text

    @field_validator("selectionType")
    @classmethod
    def normalize_selection_type(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in SPELL_SELECTION_TYPE_MAP:
            raise ValueError(f"Unknown selection type: {value}")
        return text

    @field_validator("originType")
    @classmethod
    def normalize_origin_type(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in SPELL_ORIGIN_TYPE_MAP:
            raise ValueError(f"Unknown origin type: {value}")
        return text

    @field_validator("targetAnchor")
    @classmethod
    def normalize_target_anchor(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in SPELL_TARGET_ANCHOR_MAP:
            raise ValueError(f"Unknown target anchor: {value}")
        return text

    @field_validator("attackType")
    @classmethod
    def normalize_attack_type(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in SPELL_ATTACK_TYPE_MAP:
            raise ValueError(f"Unknown attack type: {value}")
        return text

    @field_validator("rangeKind")
    @classmethod
    def normalize_range_kind(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in SPELL_RANGE_KIND_MAP:
            raise ValueError(f"Unknown range kind: {value}")
        return text

    @field_validator("effectTiming")
    @classmethod
    def normalize_effect_timing(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in SPELL_EFFECT_TIMING_MAP:
            raise ValueError(f"Unknown effect timing: {value}")
        return text

    @field_validator("areaShape")
    @classmethod
    def normalize_area_shape(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        if not text:
            return None
        if text not in AREA_SHAPE_MAP:
            raise ValueError(f"Unknown area shape: {value}")
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

    @model_validator(mode="after")
    def cross_field_validation(self):
        if not self.componentsJson or "M" not in self.componentsJson:
            self.materialComponentText = None

        if self.upcast is None and self.upcastMode is not None:
            self.upcast = _build_structured_upcast_from_legacy(
                upcast_mode=self.upcastMode,
                upcast_value=self.upcastValue,
                resolution_type=self.resolutionType,
            )

        rt = self.resolutionType
        CAN_HAVE_SAVING_THROW = {"damage", "control", "debuff"}
        NEVER_DAMAGE = {"heal", "buff", "debuff", "control", "utility"}

        if rt == "heal" and not self.healDice:
            raise ValueError("healDice is required when resolutionType is 'heal'.")

        if rt in NEVER_DAMAGE:
            self.damageDice = None
            self.damageType = None

        if rt != "damage" or self.savingThrow is None:
            self.saveSuccessOutcome = None

        if rt != "damage":
            self.attackMissOutcome = None

        if rt is not None and rt not in CAN_HAVE_SAVING_THROW:
            self.savingThrow = None

        if self.upcastMode == "none":
            self.upcastValue = None
        if self.upcast is not None:
            if self.level == 0:
                raise ValueError("Cantrips cannot use upcast; use cantripScaling.")
            if self.upcast.mode == "extra_heal_dice" and rt != "heal":
                raise ValueError(
                    "Upcast 'extra_heal_dice' requires resolutionType 'heal'."
                )
            if self.upcast.mode == "extra_damage_dice" and rt not in {"damage", "attack"}:
                raise ValueError(
                    "Upcast 'extra_damage_dice' requires resolutionType 'damage' or 'attack'."
                )
        if self.cantripScaling is not None and self.level is not None and self.level > 0:
            raise ValueError("Only cantrips can use cantripScaling.")

        if self.onEndEffects and not self.effects:
            raise ValueError("onEndEffects requires effects to be present.")

        if self.variants:
            seen_variant_keys: set[str] = set()
            for variant in self.variants:
                variant_key = variant.key.lower()
                if variant_key in seen_variant_keys:
                    raise ValueError(
                        f"Duplicate spell variant key: {variant.key}"
                    )
                seen_variant_keys.add(variant_key)

        if self.persistentArea is not None and self.effectTiming not in (None, "persistent"):
            raise ValueError("persistentArea requires effectTiming to be 'persistent'.")

        return self


class BaseSpellCreate(BaseSpellWrite):
    system: SystemType = SystemType.DND5E
    canonicalKey: str

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


class BaseSpellUpdate(BaseSpellWrite):
    pass


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
