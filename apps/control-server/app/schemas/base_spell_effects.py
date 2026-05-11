from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.campaign_entity_shared import AbilityName


SpellDeclarativeEffectType = Literal[
    "apply_condition",
    "modify_stat",
    "modify_weapon_damage",
    "armor_class_formula",
    "advantage_on_checks",
    "disadvantage_on_checks",
    "advantage_on_saves",
    "disadvantage_on_saves",
    "size_modifier",
    "restrict_action",
    "grant_temp_hp",
    "passive_skill_bonus",
    "carrying_capacity_multiplier",
    "modify_movement_speed",
    "fall_damage_immunity_threshold",
]

SpellDeclarativeEffectTarget = Literal["selected_target", "caster"]
SpellDeclarativeDurationType = Literal[
    "manual",
    "rounds",
    "until_turn_start",
    "until_turn_end",
    "timed",
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
SpellDeclarativeAgainst = Literal["selected_target", "effect_target", "any"]


class SpellDeclarativeDuration(BaseModel):
    type: SpellDeclarativeDurationType
    rounds: int | None = Field(default=None, ge=1)
    seconds: int | None = Field(default=None, ge=1)
    anchor: SpellDeclarativeDurationAnchor | None = None

    @model_validator(mode="after")
    def validate_duration(self):
        if self.type == "rounds":
            if self.rounds is None:
                raise ValueError("rounds is required when duration.type is 'rounds'")
        else:
            self.rounds = None

        if self.type == "timed":
            if self.seconds is None:
                raise ValueError("seconds is required when duration.type is 'timed'")
        else:
            self.seconds = None

        if self.type in {"manual", "timed"}:
            self.anchor = None
        elif self.anchor is None:
            self.anchor = "target"
        return self


class SpellOutOfCombatTimedDuration(BaseModel):
    type: Literal["timed"] = "timed"
    seconds: int = Field(ge=1)


class ApplyConditionParams(BaseModel):
    condition: SpellDeclarativeConditionType


class ModifyStatParams(BaseModel):
    stat: SpellDeclarativeModifyStat
    value: int


class ModifyWeaponDamageParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dice: str
    operation: Literal["add", "subtract"] = "add"
    minimum_total_damage: int | None = None


class SizeModifierParams(BaseModel):
    value: Literal[-1, 1]


class CheckModifierParams(BaseModel):
    ability: AbilityName
    against: SpellDeclarativeAgainst | None = None


class SaveModifierParams(BaseModel):
    abilities: list[AbilityName]


class RestrictActionParams(BaseModel):
    action: SpellDeclarativeRestrictActionKind


class GrantTempHpParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dice: str


class PassiveSkillBonusParams(BaseModel):
    skill: str
    bonus: int


class CarryingCapacityMultiplierParams(BaseModel):
    multiplier: float


class FallDamageImmunityThresholdParams(BaseModel):
    max_distance_meters: float


class ModifyMovementSpeedParams(BaseModel):
    bonus_meters: float


class ArmorClassFormulaParams(BaseModel):
    base_value: int = Field(ge=0)
    ability: AbilityName
    requires_unarmored: bool | None = None


SpellDeclarativeTerminationConditionType = Literal[
    "target_dons_armor",
    "target_takes_damage_from_caster_or_allies",
]


class TerminationCondition(BaseModel):
    type: SpellDeclarativeTerminationConditionType


class SpellDeclarativeEffect(BaseModel):
    type: SpellDeclarativeEffectType
    target: SpellDeclarativeEffectTarget
    duration: SpellDeclarativeDuration | None = None
    out_of_combat_duration: SpellOutOfCombatTimedDuration | None = None
    termination_conditions: list[TerminationCondition] | None = None
    params: (
        ApplyConditionParams
        | ModifyStatParams
        | GrantTempHpParams
        | ModifyWeaponDamageParams
        | SizeModifierParams
        | ArmorClassFormulaParams
        | CheckModifierParams
        | SaveModifierParams
        | RestrictActionParams
        | PassiveSkillBonusParams
        | CarryingCapacityMultiplierParams
        | ModifyMovementSpeedParams
        | FallDamageImmunityThresholdParams
    )
    stacking: SpellDeclarativeEffectStacking | None = None

    @model_validator(mode="after")
    def validate_params_shape(self):
        if self.type == "apply_condition" and not isinstance(self.params, ApplyConditionParams):
            raise ValueError("apply_condition effects require ApplyConditionParams")
        if self.type == "modify_stat" and not isinstance(self.params, ModifyStatParams):
            raise ValueError("modify_stat effects require ModifyStatParams")
        if self.type == "modify_weapon_damage" and not isinstance(self.params, ModifyWeaponDamageParams):
            raise ValueError("modify_weapon_damage effects require ModifyWeaponDamageParams")
        if self.type == "size_modifier" and not isinstance(self.params, SizeModifierParams):
            raise ValueError("size_modifier effects require SizeModifierParams")
        if self.type == "armor_class_formula" and not isinstance(self.params, ArmorClassFormulaParams):
            raise ValueError("armor_class_formula effects require ArmorClassFormulaParams")
        if self.type in {"advantage_on_checks", "disadvantage_on_checks"} and not isinstance(
            self.params, CheckModifierParams
        ):
            raise ValueError(f"{self.type} effects require CheckModifierParams")
        if self.type in {"advantage_on_saves", "disadvantage_on_saves"} and not isinstance(
            self.params, SaveModifierParams
        ):
            raise ValueError(f"{self.type} effects require SaveModifierParams")
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
        if self.type == "modify_movement_speed" and not isinstance(self.params, ModifyMovementSpeedParams):
            raise ValueError("modify_movement_speed effects require ModifyMovementSpeedParams")
        return self
