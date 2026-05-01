from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.campaign_entity_shared import AbilityName


SpellDeclarativeEffectType = Literal[
    "apply_condition",
    "modify_stat",
    "advantage_on_checks",
    "disadvantage_on_checks",
    "restrict_action",
    "grant_temp_hp",
    "passive_skill_bonus",
    "carrying_capacity_multiplier",
    "fall_damage_immunity_threshold",
]

SpellDeclarativeEffectTarget = Literal["selected_target", "caster"]
SpellDeclarativeDurationType = Literal[
    "manual",
    "rounds",
    "until_turn_start",
    "until_turn_end",
]
SpellDeclarativeDurationAnchor = Literal["target", "caster"]
SpellDeclarativeConditionType = Literal[
    "blinded",
    "charmed",
    "deafened",
    "frightened",
    "grappled",
    "hostile_to_caster",
    "incapacitated",
    "invisible",
    "paralyzed",
    "petrified",
    "poisoned",
    "prone",
    "restrained",
    "stunned",
    "unconscious",
]
SpellDeclarativeModifyStat = Literal[
    "temp_ac_bonus",
    "attack_bonus",
    "damage_bonus",
]
SpellDeclarativeRestrictActionKind = Literal[
    "actions",
    "bonus_actions",
    "reactions",
    "movement",
]
SpellDeclarativeEffectStacking = Literal["stack", "replace"]


class SpellDeclarativeDuration(BaseModel):
    type: SpellDeclarativeDurationType
    rounds: int | None = Field(default=None, ge=1)
    anchor: SpellDeclarativeDurationAnchor | None = None

    @model_validator(mode="after")
    def validate_duration(self):
        if self.type == "rounds":
            if self.rounds is None:
                raise ValueError("rounds is required when duration.type is 'rounds'")
        else:
            self.rounds = None

        if self.type == "manual":
            self.anchor = None
        elif self.anchor is None:
            self.anchor = "target"
        return self


class ApplyConditionParams(BaseModel):
    condition: SpellDeclarativeConditionType


class ModifyStatParams(BaseModel):
    stat: SpellDeclarativeModifyStat
    value: int


class CheckModifierParams(BaseModel):
    ability: AbilityName


class RestrictActionParams(BaseModel):
    action: SpellDeclarativeRestrictActionKind


class GrantTempHpParams(BaseModel):
    dice: str


class PassiveSkillBonusParams(BaseModel):
    skill: str
    bonus: int


class CarryingCapacityMultiplierParams(BaseModel):
    multiplier: float


class FallDamageImmunityThresholdParams(BaseModel):
    max_distance_meters: float


class SpellDeclarativeEffect(BaseModel):
    type: SpellDeclarativeEffectType
    target: SpellDeclarativeEffectTarget
    duration: SpellDeclarativeDuration | None = None
    params: (
        ApplyConditionParams
        | ModifyStatParams
        | CheckModifierParams
        | RestrictActionParams
        | GrantTempHpParams
        | PassiveSkillBonusParams
        | CarryingCapacityMultiplierParams
        | FallDamageImmunityThresholdParams
    )
    stacking: SpellDeclarativeEffectStacking | None = None

    @model_validator(mode="after")
    def validate_params_shape(self):
        if self.type == "apply_condition" and not isinstance(self.params, ApplyConditionParams):
            raise ValueError("apply_condition effects require ApplyConditionParams")
        if self.type == "modify_stat" and not isinstance(self.params, ModifyStatParams):
            raise ValueError("modify_stat effects require ModifyStatParams")
        if self.type in {"advantage_on_checks", "disadvantage_on_checks"} and not isinstance(
            self.params, CheckModifierParams
        ):
            raise ValueError(f"{self.type} effects require CheckModifierParams")
        if self.type == "restrict_action" and not isinstance(self.params, RestrictActionParams):
            raise ValueError("restrict_action effects require RestrictActionParams")
        if self.type == "grant_temp_hp" and not isinstance(self.params, GrantTempHpParams):
            raise ValueError("grant_temp_hp effects require GrantTempHpParams")
        if self.type == "passive_skill_bonus" and not isinstance(self.params, PassiveSkillBonusParams):
            raise ValueError("passive_skill_bonus effects require PassiveSkillBonusParams")
        if self.type == "carrying_capacity_multiplier" and not isinstance(self.params, CarryingCapacityMultiplierParams):
            raise ValueError("carrying_capacity_multiplier effects require CarryingCapacityMultiplierParams")
        if self.type == "fall_damage_immunity_threshold" and not isinstance(self.params, FallDamageImmunityThresholdParams):
            raise ValueError("fall_damage_immunity_threshold effects require FallDamageImmunityThresholdParams")
        return self
