from __future__ import annotations

import math

from pydantic import BaseModel

FALL_DAMAGE_METERS_PER_DIE = 3
FALL_DAMAGE_DIE_SIDES = 6
MAX_FALL_DAMAGE_DICE = 20
# TODO: align with canonical damage-type enum/registry when established
FALL_DAMAGE_TYPE = "bludgeoning"


class FallDamageComputation(BaseModel):
    height_meters: float
    effective_height_meters: float
    dice_count: int
    dice_sides: int
    damage_type: str
    damage_formula: str | None
    causes_damage: bool


def compute_fall_damage(height_meters: float) -> FallDamageComputation:
    effective_height_meters = max(0.0, height_meters)
    causes_damage = effective_height_meters >= FALL_DAMAGE_METERS_PER_DIE
    if causes_damage:
        dice_count = min(
            MAX_FALL_DAMAGE_DICE,
            math.floor(effective_height_meters / FALL_DAMAGE_METERS_PER_DIE),
        )
    else:
        dice_count = 0
    return FallDamageComputation(
        height_meters=height_meters,
        effective_height_meters=effective_height_meters,
        dice_count=dice_count,
        dice_sides=FALL_DAMAGE_DIE_SIDES,
        damage_type=FALL_DAMAGE_TYPE,
        damage_formula=f"{dice_count}d{FALL_DAMAGE_DIE_SIDES}" if causes_damage else None,
        causes_damage=causes_damage,
    )
