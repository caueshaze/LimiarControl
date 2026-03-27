from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.campaign_entity_shared import AbilityName, ActionCost, CombatActionKind, DamageType

_DICE_EXPRESSION_RE = re.compile(r"^\d+d\d+(?:\s*[+-]\s*\d+)?$", re.IGNORECASE)


class CombatAction(BaseModel):
    id: str
    name: str
    kind: CombatActionKind
    campaignItemId: str | None = None
    weaponCanonicalKey: str | None = None
    spellCanonicalKey: str | None = None
    toHitBonus: int | None = None
    spellAttackBonus: int | None = None
    damageDice: str | None = None
    damageBonus: int | None = None
    damageType: DamageType | None = None
    rangeMeters: int | None = Field(default=None, ge=0)
    isMelee: bool | None = None
    saveAbility: AbilityName | None = None
    saveDc: int | None = Field(default=None, ge=1)
    castAtLevel: int | None = Field(default=None, ge=1, le=9)
    healDice: str | None = None
    healBonus: int | None = None
    description: str | None = None
    actionCost: ActionCost = "action"

    @field_validator("id", "name")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field is required.")
        return normalized

    @field_validator("campaignItemId", mode="before")
    @classmethod
    def normalize_reference_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("weaponCanonicalKey", "spellCanonicalKey", mode="before")
    @classmethod
    def normalize_canonical_keys(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("damageDice", "healDice", mode="before")
    @classmethod
    def validate_dice_expression(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"\s+", "", value.strip().lower())
        if not normalized:
            return None
        if not _DICE_EXPRESSION_RE.fullmatch(normalized):
            raise ValueError("Dice expressions must look like 1d6, 2d8+3, or 1d10-1.")
        return normalized

    @model_validator(mode="after")
    def validate_action_shape(self):
        executable_fields = (
            self.campaignItemId,
            self.weaponCanonicalKey,
            self.spellCanonicalKey,
            self.toHitBonus,
            self.spellAttackBonus,
            self.damageDice,
            self.damageBonus,
            self.damageType,
            self.rangeMeters,
            self.isMelee,
            self.saveAbility,
            self.saveDc,
            self.castAtLevel,
            self.healDice,
            self.healBonus,
        )

        if self.castAtLevel is not None and not self.spellCanonicalKey:
            raise ValueError("castAtLevel requires a spellCanonicalKey.")

        if self.kind == "utility":
            if any(value is not None for value in executable_fields):
                raise ValueError("Utility actions are manual-only and cannot define executable combat fields.")
            return self

        if self.kind == "weapon_attack":
            if self.spellCanonicalKey:
                raise ValueError("Weapon attacks cannot reference spellCanonicalKey.")
            if self.toHitBonus is None:
                raise ValueError("Weapon attacks require an explicit toHitBonus.")
            has_catalog_profile = self.campaignItemId is not None or self.weaponCanonicalKey is not None
            has_manual_profile = (
                self.damageDice is not None
                and self.damageType is not None
                and self.isMelee is not None
            )
            if not has_catalog_profile and not has_manual_profile:
                raise ValueError(
                    "Weapon attacks require campaignItemId/weaponCanonicalKey or a full manual profile "
                    "(damageDice, damageType, and melee/ranged mode)."
                )
            if any(value is not None for value in (self.saveAbility, self.saveDc, self.healDice, self.healBonus)):
                raise ValueError("Weapon attacks cannot define saving throw or healing fields.")
            return self

        if self.kind == "spell_attack":
            if self.weaponCanonicalKey:
                raise ValueError("Spell attacks cannot reference weaponCanonicalKey.")
            if not self.spellCanonicalKey:
                raise ValueError("Automated spell attacks require spellCanonicalKey.")
            if not self.damageDice:
                raise ValueError("Spell attacks require explicit damageDice until spell damage is fully catalog-driven.")
            if any(value is not None for value in (self.saveAbility, self.saveDc, self.healDice, self.healBonus)):
                raise ValueError("Spell attacks cannot define save/heal-only fields.")
            return self

        if self.kind == "saving_throw":
            if self.weaponCanonicalKey:
                raise ValueError("Saving throw actions cannot reference weaponCanonicalKey.")
            if not self.spellCanonicalKey:
                raise ValueError("Automated saving throw actions require spellCanonicalKey.")
            if not self.damageDice:
                raise ValueError(
                    "Saving throw actions require explicit damageDice. "
                    "Use utility for non-damaging effects not automated yet."
                )
            if any(value is not None for value in (self.toHitBonus, self.spellAttackBonus, self.healDice, self.healBonus)):
                raise ValueError("Saving throw actions cannot define attack or healing fields.")
            return self

        if self.kind == "heal":
            if self.weaponCanonicalKey:
                raise ValueError("Heal actions cannot reference weaponCanonicalKey.")
            if not self.healDice:
                raise ValueError("Heal actions require healDice.")
            if any(
                value is not None
                for value in (
                    self.toHitBonus,
                    self.spellAttackBonus,
                    self.damageDice,
                    self.damageBonus,
                    self.damageType,
                    self.saveAbility,
                    self.saveDc,
                )
            ):
                raise ValueError("Heal actions cannot define attack or damage fields.")
            return self

        return self
