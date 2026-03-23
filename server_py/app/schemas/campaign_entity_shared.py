from __future__ import annotations

from math import floor
from typing import Literal

from pydantic import BaseModel, Field

VALID_CATEGORIES = {"npc", "enemy", "creature", "ally"}

AbilityName = Literal["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
CombatActionKind = Literal["weapon_attack", "spell_attack", "saving_throw", "heal", "utility"]
EntitySize = Literal["tiny", "small", "medium", "large", "huge", "gargantuan"]
CreatureType = Literal[
    "aberration",
    "beast",
    "celestial",
    "construct",
    "dragon",
    "elemental",
    "fey",
    "fiend",
    "giant",
    "humanoid",
    "monstrosity",
    "ooze",
    "plant",
    "undead",
]
SkillName = Literal[
    "acrobatics",
    "animalHandling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleightOfHand",
    "stealth",
    "survival",
]
DamageType = Literal[
    "acid",
    "bludgeoning",
    "cold",
    "fire",
    "force",
    "lightning",
    "necrotic",
    "piercing",
    "poison",
    "psychic",
    "radiant",
    "slashing",
    "thunder",
]
ConditionType = Literal[
    "blinded",
    "charmed",
    "deafened",
    "frightened",
    "grappled",
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

SKILL_ABILITY_MAP: dict[SkillName, AbilityName] = {
    "acrobatics": "dexterity",
    "animalHandling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleightOfHand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
}


def ability_modifier(score: int) -> int:
    return floor((score - 10) / 2)


def _ability_scores_to_dict(abilities: "AbilityScores | dict | None") -> dict[str, int]:
    if isinstance(abilities, AbilityScores):
        return abilities.model_dump()
    if isinstance(abilities, dict):
        return {key: value for key, value in abilities.items() if isinstance(value, int)}
    return {}


def resolve_initiative_bonus(abilities: "AbilityScores | dict | None", initiative_bonus: int | None) -> int:
    if isinstance(initiative_bonus, int):
        return initiative_bonus
    ability_scores = _ability_scores_to_dict(abilities)
    return ability_modifier(ability_scores.get("dexterity", 10))


def resolve_saving_throw_bonus(
    abilities: "AbilityScores | dict | None",
    saving_throws: dict[AbilityName, int] | dict | None,
    ability_name: AbilityName,
) -> int:
    if isinstance(saving_throws, dict):
        explicit_bonus = saving_throws.get(ability_name)
        if isinstance(explicit_bonus, int):
            return explicit_bonus
    ability_scores = _ability_scores_to_dict(abilities)
    return ability_modifier(ability_scores.get(ability_name, 10))


def resolve_skill_bonus(
    abilities: "AbilityScores | dict | None",
    skills: dict[SkillName, int] | dict | None,
    skill_name: SkillName,
) -> int:
    if isinstance(skills, dict):
        explicit_bonus = skills.get(skill_name)
        if isinstance(explicit_bonus, int):
            return explicit_bonus
    ability_scores = _ability_scores_to_dict(abilities)
    base_ability = SKILL_ABILITY_MAP[skill_name]
    return ability_modifier(ability_scores.get(base_ability, 10))


class AbilityScores(BaseModel):
    strength: int = Field(default=10, ge=1, le=30)
    dexterity: int = Field(default=10, ge=1, le=30)
    constitution: int = Field(default=10, ge=1, le=30)
    intelligence: int = Field(default=10, ge=1, le=30)
    wisdom: int = Field(default=10, ge=1, le=30)
    charisma: int = Field(default=10, ge=1, le=30)


class EntitySenses(BaseModel):
    darkvisionMeters: int | None = Field(default=None, ge=0)
    blindsightMeters: int | None = Field(default=None, ge=0)
    tremorsenseMeters: int | None = Field(default=None, ge=0)
    truesightMeters: int | None = Field(default=None, ge=0)
    passivePerception: int | None = Field(default=None, ge=0)


class EntitySpellcasting(BaseModel):
    ability: AbilityName | None = None
    saveDc: int | None = Field(default=None, ge=0)
    attackBonus: int | None = None
