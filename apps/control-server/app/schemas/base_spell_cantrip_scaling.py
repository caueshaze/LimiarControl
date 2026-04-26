from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .base_spell_constants import DICE_EXPRESSION_RE


CantripScalingMode = Literal["character_level"]


class CantripScalingDamage(BaseModel):
    dice: str

    @field_validator("dice")
    @classmethod
    def validate_dice_expression(cls, value: str):
        text = value.strip()
        if not text or not DICE_EXPRESSION_RE.match(text):
            raise ValueError(f"Invalid dice expression: {value}")
        return text


class CantripScalingThreshold(BaseModel):
    characterLevel: int = Field(ge=1, le=20)
    damage: CantripScalingDamage


class SpellCantripScalingConfig(BaseModel):
    mode: CantripScalingMode
    thresholds: list[CantripScalingThreshold]

    @model_validator(mode="after")
    def validate_thresholds(self):
        if not self.thresholds:
            raise ValueError("cantripScaling requires at least one threshold.")
        levels = [entry.characterLevel for entry in self.thresholds]
        if len(set(levels)) != len(levels):
            raise ValueError("cantripScaling thresholds cannot repeat characterLevel.")
        if levels != sorted(levels):
            raise ValueError("cantripScaling thresholds must be sorted by characterLevel.")
        return self
