from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .base_spell_constants import DICE_EXPRESSION_RE

SpellUpcastMode = Literal[
    "extra_damage_dice",
    "extra_heal_dice",
    "flat_bonus",
    "additional_effect_instances",
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
    scalingKey: Optional[str] = None
    scalingSummary: Optional[str] = None
    scalingEditorial: Optional[str] = None
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

    @field_validator(
        "scalingKey",
        "scalingSummary",
        "scalingEditorial",
        "unlockKey",
        "unlockSummary",
        "unlockEditorial",
        mode="before",
    )
    @classmethod
    def normalize_structured_text(cls, value: Optional[str]):
        if value is None:
            return None
        text = value.strip()
        return text or None

    @model_validator(mode="after")
    def validate_upcast_shape(self):
        needs_dice_or_flat = {
            "extra_damage_dice",
            "extra_heal_dice",
            "additional_effect_instances",
        }
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
                raise ValueError(
                    "Upcast mode 'effect_scaling' requires scalingSummary."
                )
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

    NEW_MODES_NEEDING_DICE: set[str] = {"extra_damage_dice", "extra_heal_dice"}
    NEW_MODES_NEEDING_FLAT: set[str] = {"flat_bonus"}
    NEW_MODES_NO_DICE: set[str] = {
        "additional_effect_instances",
        "additional_targets",
        "duration_scaling",
        "effect_scaling",
        "extra_effect",
    }

    if normalized_mode in NEW_MODES_NEEDING_DICE:
        if not normalized_value:
            raise ValueError(
                f"upcastMode '{normalized_mode}' requires upcastValue (dice expression)."
            )
        return SpellUpcastConfig(
            mode=normalized_mode, dice=normalized_value, perLevel=1
        )  # type: ignore[arg-type]
    if normalized_mode in NEW_MODES_NEEDING_FLAT:
        flat_val = (
            int(normalized_value)
            if normalized_value and normalized_value.isdigit()
            else None
        )
        if flat_val is None:
            raise ValueError("flat_bonus requires integer upcastValue.")
        return SpellUpcastConfig(mode="flat_bonus", flat=flat_val, perLevel=1)
    if normalized_mode in NEW_MODES_NO_DICE:
        per_level = 1
        if normalized_value and normalized_value.isdigit():
            per_level = int(normalized_value)
        return SpellUpcastConfig(mode=normalized_mode, perLevel=per_level)  # type: ignore[arg-type]

    if normalized_mode in ("add_dice", "add_damage", "add_heal"):
        if not normalized_value:
            raise ValueError(f"Legacy upcast '{normalized_mode}' requires upcastValue.")
        structured_mode: SpellUpcastMode = (
            "extra_heal_dice"
            if resolution_type == "heal" or normalized_mode == "add_heal"
            else "extra_damage_dice"
        )
        return SpellUpcastConfig(
            mode=structured_mode, dice=normalized_value, perLevel=1
        )
    if normalized_mode in ("add_targets", "increase_targets"):
        per_level = 1
        if normalized_value is not None:
            if not normalized_value.isdigit():
                raise ValueError(
                    "Legacy add_targets upcastValue must be a positive integer."
                )
            per_level = int(normalized_value)
            if per_level <= 0:
                raise ValueError("Legacy add_targets upcastValue must be positive.")
        return SpellUpcastConfig(mode="additional_targets", perLevel=per_level)
    if normalized_mode == "increase_duration":
        return SpellUpcastConfig(mode="duration_scaling", perLevel=1)
    if normalized_mode == "custom":
        return SpellUpcastConfig(mode="extra_effect", perLevel=1)
    raise ValueError(f"Unsupported upcast mode: {upcast_mode}")
