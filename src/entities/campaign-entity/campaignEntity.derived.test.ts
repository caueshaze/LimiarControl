import { describe, expect, it } from "vitest";

import type { CampaignEntityPayload } from "./campaignEntity.types";
import {
  getCampaignEntityAbilityModifier,
  getCampaignEntityExplicitSkillEntries,
  getCampaignEntityInitiativeBonus,
  getCampaignEntitySavingThrowBonus,
  getCampaignEntitySavingThrowEntries,
  getCampaignEntitySkillBonus,
  normalizeCampaignEntityOverrides,
} from "./campaignEntity.derived";
import { EMPTY_ENTITY_ABILITIES } from "./campaignEntity.statblock";

const createEntity = (overrides?: Partial<CampaignEntityPayload>): CampaignEntityPayload => ({
  name: "Goblin",
  category: "enemy",
  size: null,
  creatureType: null,
  creatureSubtype: null,
  description: null,
  imageUrl: null,
  armorClass: 13,
  maxHp: 7,
  speedMeters: 9,
  initiativeBonus: null,
  abilities: {
    ...EMPTY_ENTITY_ABILITIES,
    dexterity: 14,
    wisdom: 12,
    charisma: 8,
  },
  savingThrows: {},
  skills: {},
  senses: null,
  spellcasting: null,
  damageResistances: [],
  damageImmunities: [],
  damageVulnerabilities: [],
  conditionImmunities: [],
  combatActions: [],
  actions: null,
  notesPrivate: null,
  notesPublic: null,
  ...overrides,
});

describe("campaignEntity.derived", () => {
  it("derives ability modifiers from ability scores", () => {
    expect(getCampaignEntityAbilityModifier(14)).toBe(2);
    expect(getCampaignEntityAbilityModifier(9)).toBe(-1);
  });

  it("uses initiative override when present and dexterity otherwise", () => {
    expect(getCampaignEntityInitiativeBonus(createEntity())).toBe(2);
    expect(getCampaignEntityInitiativeBonus(createEntity({ initiativeBonus: 5 }))).toBe(5);
  });

  it("resolves saving throws with override or attribute fallback", () => {
    const entity = createEntity({
      savingThrows: { dexterity: 5 },
    });

    expect(getCampaignEntitySavingThrowBonus(entity, "dexterity")).toBe(5);
    expect(getCampaignEntitySavingThrowBonus(entity, "wisdom")).toBe(1);
  });

  it("resolves skills with override or base ability fallback", () => {
    const entity = createEntity({
      skills: { stealth: 6, intimidation: 2 },
    });

    expect(getCampaignEntitySkillBonus(entity, "stealth")).toBe(6);
    expect(getCampaignEntitySkillBonus(entity, "acrobatics")).toBe(2);
    expect(getCampaignEntitySkillBonus(entity, "intimidation")).toBe(2);
  });

  it("normalizes redundant initiative, save, and skill overrides", () => {
    const normalized = normalizeCampaignEntityOverrides(
      createEntity({
        initiativeBonus: 2,
        savingThrows: { dexterity: 2, wisdom: 3 },
        skills: { acrobatics: 2, stealth: 6 },
      }),
    );

    expect(normalized.initiativeBonus).toBeNull();
    expect(normalized.savingThrows).toEqual({ wisdom: 3 });
    expect(normalized.skills).toEqual({ stealth: 6 });
  });

  it("builds save entries from all abilities and keeps only explicit skills in preview helpers", () => {
    const entity = createEntity({
      savingThrows: { wisdom: 4 },
      skills: { stealth: 6, perception: 3 },
    });

    const saveEntries = getCampaignEntitySavingThrowEntries(entity);
    const explicitSkills = getCampaignEntityExplicitSkillEntries(entity);

    expect(saveEntries).toHaveLength(6);
    expect(saveEntries.find((entry) => entry.key === "wisdom")).toMatchObject({
      bonus: 4,
      isOverride: true,
    });
    expect(saveEntries.find((entry) => entry.key === "dexterity")).toMatchObject({
      bonus: 2,
      isOverride: false,
    });
    expect(explicitSkills.map((entry) => entry.key)).toEqual(["perception", "stealth"]);
  });
});
