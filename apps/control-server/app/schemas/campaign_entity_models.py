from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.campaign_entity_actions import CombatAction
from app.schemas.campaign_entity_shared import (
    AbilityName,
    AbilityScores,
    ConditionType,
    CreatureType,
    DamageType,
    EntitySenses,
    EntitySize,
    EntitySpellcasting,
    SkillName,
    SKILL_ABILITY_MAP,
    ability_modifier,
)
from app.services.media_storage_service import is_managed_url


class CampaignEntityBase(BaseModel):
    name: str
    category: str = "npc"
    size: EntitySize | None = None
    creatureType: CreatureType | None = None
    creatureSubtype: str | None = None
    description: str | None = None
    imageUrl: str | None = None
    armorClass: int | None = Field(default=None, ge=0)
    wearingMetalArmor: bool | None = None
    maxHp: int | None = Field(default=None, ge=0)
    speedMeters: int | None = Field(default=None, ge=0)
    initiativeBonus: int | None = None
    abilities: AbilityScores = Field(default_factory=AbilityScores)
    savingThrows: dict[AbilityName, int] = Field(default_factory=dict)
    skills: dict[SkillName, int] = Field(default_factory=dict)
    senses: EntitySenses | None = None
    spellcasting: EntitySpellcasting | None = None
    damageResistances: list[DamageType] = Field(default_factory=list)
    damageImmunities: list[DamageType] = Field(default_factory=list)
    damageVulnerabilities: list[DamageType] = Field(default_factory=list)
    conditionImmunities: list[ConditionType] = Field(default_factory=list)
    combatActions: list[CombatAction] = Field(default_factory=list)
    actions: str | None = None
    notesPrivate: str | None = None
    notesPublic: str | None = None

    @field_validator(
        "damageResistances",
        "damageImmunities",
        "damageVulnerabilities",
        "conditionImmunities",
        mode="after",
    )
    @classmethod
    def dedupe_lists(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def normalize_derived_overrides(self):
        base_initiative = ability_modifier(self.abilities.dexterity)
        if self.initiativeBonus == base_initiative:
            self.initiativeBonus = None

        self.savingThrows = {
            ability: bonus
            for ability, bonus in self.savingThrows.items()
            if bonus != ability_modifier(getattr(self.abilities, ability))
        }

        self.skills = {
            skill: bonus
            for skill, bonus in self.skills.items()
            if bonus != ability_modifier(getattr(self.abilities, SKILL_ABILITY_MAP[skill]))
        }

        return self


class CampaignEntityCreate(CampaignEntityBase):
    @field_validator("imageUrl", mode="before")
    @classmethod
    def normalize_image_url(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("imageUrl")
    @classmethod
    def validate_image_url(cls, value: str | None):
        if value is None:
            return None
        if not is_managed_url(value):
            raise ValueError("imageUrl must use the canonical managed asset URL")
        return value


class CampaignEntityUpdate(CampaignEntityBase):
    @field_validator("imageUrl", mode="before")
    @classmethod
    def normalize_image_url(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("imageUrl")
    @classmethod
    def validate_image_url(cls, value: str | None):
        if value is None:
            return None
        if not is_managed_url(value):
            raise ValueError("imageUrl must use the canonical managed asset URL")
        return value


class CampaignEntityRead(CampaignEntityBase):
    id: str
    campaignId: str
    createdAt: datetime
    updatedAt: datetime | None


class CampaignEntityPublicRead(CampaignEntityBase):
    id: str
    campaignId: str
    # Public schema deliberately strips private notes: only None is ever allowed.
    notesPrivate: None = None  # type: ignore[assignment]  # intentional narrowing of CampaignEntityBase.notesPrivate
    createdAt: datetime
