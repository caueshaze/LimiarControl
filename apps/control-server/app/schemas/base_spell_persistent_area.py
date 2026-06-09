from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


SpellPersistentAreaKind = Literal["obscurement", "hazard", "no_semantic_effect"]
SpellPersistentAreaObscurement = Literal["heavily_obscured"]
SpellPersistentAreaTerrainEffect = Literal["difficult_terrain"]


class PersistentAreaObscurementParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    obscurement: SpellPersistentAreaObscurement


class PersistentAreaHazardParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    terrainEffect: SpellPersistentAreaTerrainEffect | None = None
    movementDamageDice: str | None = None
    damageType: str | None = None
    damagePerMeters: float | None = None
    # Spell-level identifier for hazards whose semantics are implemented in code (e.g. "moonbeam").
    effectKind: Optional[str] = None
    # Triggers that cause the hazard damage to fire (e.g. enter_first_time_on_turn, start_turn).
    damageTriggers: Optional[list[str]] = None
    # Distance in meters the caster can move the area per turn.
    moveDistanceMeters: Optional[float] = None

    @model_validator(mode="after")
    def validate_hazard_params(self):
        has_terrain = self.terrainEffect is not None
        has_damage_dice = isinstance(self.movementDamageDice, str) and bool(self.movementDamageDice.strip())
        has_damage_type = isinstance(self.damageType, str) and bool(self.damageType.strip())
        has_damage_per_meters = isinstance(self.damagePerMeters, (int, float))
        has_effect_kind = isinstance(self.effectKind, str) and bool(self.effectKind.strip())

        if not has_terrain and not has_damage_dice and not has_damage_type and not has_damage_per_meters and not has_effect_kind:
            raise ValueError("hazard params must define at least one semantic effect")
        if has_damage_dice != has_damage_per_meters:
            raise ValueError(
                "hazard movement damage requires both movementDamageDice and damagePerMeters"
            )
        if has_damage_dice and not has_damage_type:
            raise ValueError("hazard movement damage requires damageType")
        if has_damage_per_meters and self.damagePerMeters is not None and self.damagePerMeters <= 0:
            raise ValueError("damagePerMeters must be greater than 0")

        if isinstance(self.movementDamageDice, str):
            self.movementDamageDice = self.movementDamageDice.strip() or None
        if isinstance(self.damageType, str):
            self.damageType = self.damageType.strip() or None
        return self


class PersistentAreaNoSemanticEffectParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pass


class SpellPersistentAreaEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: SpellPersistentAreaKind
    params: (
        PersistentAreaObscurementParams
        | PersistentAreaHazardParams
        | PersistentAreaNoSemanticEffectParams
        | None
    ) = None

    @model_validator(mode="after")
    def validate_params_shape(self):
        if self.kind == "obscurement":
            if not isinstance(self.params, PersistentAreaObscurementParams):
                raise ValueError(
                    "obscurement persistentArea entries require PersistentAreaObscurementParams"
                )
        elif self.kind == "hazard":
            if not isinstance(self.params, PersistentAreaHazardParams):
                raise ValueError("hazard persistentArea entries require PersistentAreaHazardParams")
        elif self.kind == "no_semantic_effect":
            if self.params is None:
                self.params = PersistentAreaNoSemanticEffectParams()
            elif not isinstance(self.params, PersistentAreaNoSemanticEffectParams):
                raise ValueError(
                    "no_semantic_effect persistentArea entries require empty params"
                )
        return self
