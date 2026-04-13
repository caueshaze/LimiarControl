import { ENTITY_ABILITIES, ENTITY_SKILLS } from "./campaignEntity.statblock";
import type {
  AbilityName,
  AbilityScores,
  CampaignEntity,
  CampaignEntityPayload,
  SavingThrowBonuses,
  SkillBonuses,
  SkillName,
} from "./campaignEntity.types";

type EntityDerivedSource = {
  abilities: AbilityScores;
  initiativeBonus?: number | null;
  savingThrows?: SavingThrowBonuses;
  skills?: SkillBonuses;
};

export const getCampaignEntityAbilityModifier = (score: number) => Math.floor((score - 10) / 2);

export const getCampaignEntityInitiativeBonus = (entity: EntityDerivedSource) =>
  typeof entity.initiativeBonus === "number"
    ? entity.initiativeBonus
    : getCampaignEntityAbilityModifier(entity.abilities.dexterity);

export const hasCampaignEntitySavingThrowOverride = (
  entity: EntityDerivedSource,
  ability: AbilityName,
) => typeof entity.savingThrows?.[ability] === "number";

export const getCampaignEntitySavingThrowBonus = (
  entity: EntityDerivedSource,
  ability: AbilityName,
) => {
  const explicitBonus = entity.savingThrows?.[ability];
  if (typeof explicitBonus === "number") {
    return explicitBonus;
  }
  return getCampaignEntityAbilityModifier(entity.abilities[ability]);
};

export const hasCampaignEntitySkillOverride = (
  entity: EntityDerivedSource,
  skill: SkillName,
) => typeof entity.skills?.[skill] === "number";

export const getCampaignEntitySkillBonus = (
  entity: EntityDerivedSource,
  skill: SkillName,
) => {
  const explicitBonus = entity.skills?.[skill];
  if (typeof explicitBonus === "number") {
    return explicitBonus;
  }
  const skillDefinition = ENTITY_SKILLS.find((entry) => entry.key === skill);
  const ability = skillDefinition?.ability ?? "dexterity";
  return getCampaignEntityAbilityModifier(entity.abilities[ability]);
};

export const getCampaignEntitySavingThrowEntries = (entity: EntityDerivedSource) =>
  ENTITY_ABILITIES.map((ability) => ({
    ...ability,
    bonus: getCampaignEntitySavingThrowBonus(entity, ability.key),
    isOverride: hasCampaignEntitySavingThrowOverride(entity, ability.key),
  }));

export const getCampaignEntityExplicitSkillEntries = (entity: EntityDerivedSource) =>
  ENTITY_SKILLS.filter((skill) => hasCampaignEntitySkillOverride(entity, skill.key)).map((skill) => ({
    ...skill,
    bonus: getCampaignEntitySkillBonus(entity, skill.key),
  }));

export const normalizeCampaignEntityOverrides = <T extends CampaignEntity | CampaignEntityPayload>(
  entity: T,
) => {
  const baseInitiativeBonus = getCampaignEntityAbilityModifier(entity.abilities.dexterity);
  const normalizedSavingThrows = Object.fromEntries(
    Object.entries(entity.savingThrows ?? {}).filter(([ability, bonus]) => {
      if (typeof bonus !== "number") {
        return false;
      }
      return bonus !== getCampaignEntityAbilityModifier(entity.abilities[ability as AbilityName]);
    }),
  ) as SavingThrowBonuses;
  const normalizedSkills = Object.fromEntries(
    Object.entries(entity.skills ?? {}).filter(([skill, bonus]) => {
      if (typeof bonus !== "number") {
        return false;
      }
      return bonus !== getCampaignEntitySkillBonus(
        {
          abilities: entity.abilities,
          skills: {},
        },
        skill as SkillName,
      );
    }),
  ) as SkillBonuses;

  return {
    initiativeBonus:
      typeof entity.initiativeBonus === "number" &&
      entity.initiativeBonus !== baseInitiativeBonus
        ? entity.initiativeBonus
        : null,
    savingThrows: normalizedSavingThrows,
    skills: normalizedSkills,
  };
};
