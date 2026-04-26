from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .base_spell_constants import DICE_EXPRESSION_RE


CantripScalingMode = Literal["character_level"]
CantripScalingEffectType = Literal["damage_dice", "effect_instances"]


def _validate_dice(value: str) -> str:
    text = value.strip()
    if not text or not DICE_EXPRESSION_RE.match(text):
        raise ValueError(f"Invalid dice expression: {value}")
    return text


class CantripScalingDamage(BaseModel):
    dice: str

    @field_validator("dice")
    @classmethod
    def validate_dice_expression(cls, value: str) -> str:
        return _validate_dice(value)


class CantripInstanceDamage(BaseModel):
    dice: str

    @field_validator("dice")
    @classmethod
    def validate_dice_expression(cls, value: str) -> str:
        return _validate_dice(value)


class CantripScalingThreshold(BaseModel):
    """Flexible threshold: supports both damage_dice and effect_instances shapes."""

    characterLevel: int = Field(ge=1, le=20)
    # damage_dice fields
    damage: Optional[CantripScalingDamage] = None
    # effect_instances fields
    instances: Optional[int] = Field(default=None, ge=1)
    instanceDamage: Optional[CantripInstanceDamage] = None


class SpellCantripScalingConfig(BaseModel):
    scalingMode: CantripScalingMode
    scalingEffectType: CantripScalingEffectType
    thresholds: list[CantripScalingThreshold]

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_format(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values
        values = dict(values)
        # Migrate old "mode" → "scalingMode"
        if "mode" in values and "scalingMode" not in values:
            values["scalingMode"] = values.pop("mode")
        # Infer scalingEffectType from thresholds when absent
        if "scalingEffectType" not in values:
            thresholds = values.get("thresholds") or []
            has_instances = any(
                isinstance(t, dict) and ("instances" in t or "instanceDamage" in t)
                for t in thresholds
            )
            values["scalingEffectType"] = "effect_instances" if has_instances else "damage_dice"
        return values

    @model_validator(mode="after")
    def validate_thresholds(self) -> SpellCantripScalingConfig:
        if not self.thresholds:
            raise ValueError("cantripScaling requires at least one threshold.")
        levels = [entry.characterLevel for entry in self.thresholds]
        if len(set(levels)) != len(levels):
            raise ValueError("cantripScaling thresholds cannot repeat characterLevel.")
        if levels != sorted(levels):
            raise ValueError("cantripScaling thresholds must be sorted by characterLevel.")
        if self.scalingEffectType == "damage_dice":
            for threshold in self.thresholds:
                if threshold.damage is None:
                    raise ValueError(
                        f"damage_dice threshold at characterLevel {threshold.characterLevel} must have a damage field."
                    )
        elif self.scalingEffectType == "effect_instances":
            for threshold in self.thresholds:
                if threshold.instances is None or threshold.instanceDamage is None:
                    raise ValueError(
                        f"effect_instances threshold at characterLevel {threshold.characterLevel} must have instances and instanceDamage fields."
                    )
        return self
