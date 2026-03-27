import { z } from "zod/v4";
import { normalizeSubclassId } from "../data/classes";
import { normalizeBackgroundId } from "../data/backgrounds";
import { getRaceFixedToolProficiencies, normalizeRaceState } from "../data/races";
import type { CharacterSheet } from "./characterSheet.types";

const abilityNameSchema = z.enum([
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
]);

const skillNameSchema = z.enum([
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
]);

const proficiencyLevelSchema = z.union([
  z.literal(0),
  z.literal(0.5),
  z.literal(1),
  z.literal(2),
]);

const conditionNameSchema = z.enum([
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
]);

const armorSchema = z.object({
  name: z.string(),
  baseAC: z.number(),
  dexCap: z.number().nullable(),
  armorType: z.enum(["none", "light", "medium", "heavy"]),
  allowsDex: z.boolean().optional(),
  stealthDisadvantage: z.boolean().optional(),
  minStrength: z.number().nullable().optional(),
});

const shieldSchema = z.object({
  name: z.string(),
  bonus: z.number(),
});

const weaponSchema = z.object({
  id: z.string(),
  name: z.string(),
  ability: abilityNameSchema,
  damageDice: z.string(),
  damageType: z.string(),
  proficient: z.boolean(),
  magicBonus: z.number(),
  properties: z.string(),
  range: z.string(),
});

const inventoryItemSchema = z.object({
  id: z.string(),
  name: z.string(),
  quantity: z.number().min(0),
  weight: z.number().min(0),
  notes: z.string(),
  canonicalKey: z.string().nullable().optional(),
  campaignItemId: z.string().nullable().optional(),
  baseItemId: z.string().nullable().optional(),
});

const currencySchema = z.object({
  copperValue: z.number().min(0),
}).or(
  z.object({
    cp: z.number().min(0),
    sp: z.number().min(0),
    ep: z.number().min(0),
    gp: z.number().min(0),
    pp: z.number().min(0),
  }).transform((value) => ({
    copperValue:
      value.cp +
      value.sp * 10 +
      value.ep * 50 +
      value.gp * 100 +
      value.pp * 1000,
  })),
);

const spellSchema = z.object({
  id: z.string(),
  name: z.string(),
  canonicalKey: z.string().nullable().optional(),
  level: z.number().min(0).max(9),
  school: z.string(),
  prepared: z.boolean(),
  notes: z.string(),
});

const spellSlotsSchema = z.object({
  max: z.number().min(0),
  used: z.number().min(0),
});

const spellcastingModeSchema = z.enum(["known", "prepared", "spellbook"]);

const spellcastingSchema = z.object({
  ability: abilityNameSchema,
  mode: spellcastingModeSchema.default("known"),
  slots: z.record(z.coerce.number(), spellSlotsSchema),
  spells: z.array(spellSchema),
});

const deathSavesSchema = z.object({
  successes: z.number().min(0).max(3),
  failures: z.number().min(0).max(3),
});
const restStateSchema = z.enum(["exploration", "short_rest", "long_rest"]);
const raceConfigSchema = z.object({
  dragonbornAncestry: z.string().nullable().optional(),
  gnomeSubrace: z.string().nullable().optional(),
  halfElfAbilityChoices: z.array(abilityNameSchema).max(2).optional(),
  halfElfSkillChoices: z.array(skillNameSchema).max(2).optional(),
});

const abilitiesRecord = z.record(abilityNameSchema, z.number().min(0).max(30));
const savesRecord = z.record(abilityNameSchema, z.boolean());
const skillsRecord = z.record(skillNameSchema, proficiencyLevelSchema);
const conditionsRecord = z.record(conditionNameSchema, z.boolean());

export const characterSheetSchema = z.object({
  schemaVersion: z.number().default(1),

  name: z.string(),
  class: z.string(),
  subclass: z.preprocess((value) => {
    if (value == null) return null;
    if (typeof value !== "string") return value;
    return value.trim().length > 0 ? value : null;
  }, z.string().nullable()),
  currentWeaponId: z.preprocess((value) => {
    if (value == null) return null;
    if (typeof value !== "string") return value;
    return value.trim().length > 0 ? value : null;
  }, z.string().nullable()).default(null),
  equippedArmorItemId: z.preprocess((value) => {
    if (value == null) return null;
    if (typeof value !== "string") return value;
    return value.trim().length > 0 ? value : null;
  }, z.string().nullable()).default(null),
  level: z.number().min(1).max(20),
  background: z.string(),
  playerName: z.string(),
  race: z.string(),
  alignment: z.string(),
  experiencePoints: z.number().min(0),
  restState: restStateSchema.default("exploration"),
  pendingLevelUp: z.boolean().default(false),
  inspiration: z.boolean(),

  abilities: abilitiesRecord,
  savingThrowProficiencies: savesRecord,
  skillProficiencies: skillsRecord,

  equippedArmor: armorSchema,
  equippedShield: shieldSchema.nullable(),
  miscACBonus: z.number(),
  speedMeters: z.number().min(0),

  maxHP: z.number().min(0),
  currentHP: z.number().min(0),
  tempHP: z.number().min(0),

  hitDiceType: z.string(),
  hitDiceTotal: z.number().min(0),
  hitDiceRemaining: z.number().min(0),

  deathSaves: deathSavesSchema,

  weapons: z.array(weaponSchema),
  inventory: z.array(inventoryItemSchema),
  currency: currencySchema,

  spellcasting: spellcastingSchema.nullable(),

  languages: z.array(z.string()),
  toolProficiencies: z.array(z.string()),
  weaponProficiencies: z.array(z.string()),
  armorProficiencies: z.array(z.string()),

  conditions: conditionsRecord,

  classSkillChoices: z.array(skillNameSchema).default([]),
  classToolProficiencyChoices: z.array(z.string()).default([]),
  raceToolProficiencyChoices: z.array(z.string()).default([]),
  classEquipmentSelections: z.record(z.string(), z.string()).default({}),
  languageChoices: z.array(z.string()).default([]),
  raceConfig: raceConfigSchema.nullable().default(null),
  subclassConfig: z.record(z.string(), z.string()).nullable().default(null),
  fightingStyle: z.string().nullable().default(null),
  expertiseChoices: z.array(skillNameSchema).default([]),

  featuresAndTraits: z.string(),
  notes: z.string(),
});

/**
 * Valida e transforma `unknown` em `CharacterSheet`.
 * Lança erro com mensagem legível se inválido.
 * Use no service layer — nunca deixe `unknown` tocar o estado React.
 */
export function parseCharacterSheet(raw: unknown): CharacterSheet {
  const result = characterSheetSchema.safeParse(raw);
  if (!result.success) {
    throw new Error(z.prettifyError(result.error));
  }
  const normalizedRace = normalizeRaceState(result.data.race, result.data.raceConfig);
  const fixedRaceTools = getRaceFixedToolProficiencies(
    normalizedRace.raceId,
    normalizedRace.raceConfig,
  );
  return {
    ...result.data,
    background: normalizeBackgroundId(result.data.background),
    race: normalizedRace.raceId,
    raceConfig: normalizedRace.raceConfig,
    toolProficiencies: [...new Set([...(result.data.toolProficiencies ?? []), ...fixedRaceTools])],
    subclass: normalizeSubclassId(result.data.class, result.data.subclass),
  } as CharacterSheet;
}

/**
 * Variante segura para import de JSON pelo usuário —
 * retorna { ok, sheet } | { ok, error } sem lançar.
 */
export function validateSheet(
  data: unknown,
): { ok: true; sheet: CharacterSheet } | { ok: false; error: string } {
  const result = characterSheetSchema.safeParse(data);
  if (result.success) {
    const normalizedRace = normalizeRaceState(result.data.race, result.data.raceConfig);
    const fixedRaceTools = getRaceFixedToolProficiencies(
      normalizedRace.raceId,
      normalizedRace.raceConfig,
    );
    return {
      ok: true,
      sheet: {
        ...result.data,
        background: normalizeBackgroundId(result.data.background),
        race: normalizedRace.raceId,
        raceConfig: normalizedRace.raceConfig,
        toolProficiencies: [...new Set([...(result.data.toolProficiencies ?? []), ...fixedRaceTools])],
        subclass: normalizeSubclassId(result.data.class, result.data.subclass),
      } as CharacterSheet,
    };
  }
  return { ok: false, error: z.prettifyError(result.error) };
}
