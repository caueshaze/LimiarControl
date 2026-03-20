import { z } from "zod/v4";
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
  baseItemId: z.string().nullable().optional(),
});

const currencySchema = z.object({
  cp: z.number().min(0),
  sp: z.number().min(0),
  ep: z.number().min(0),
  gp: z.number().min(0),
  pp: z.number().min(0),
});

const spellSchema = z.object({
  id: z.string(),
  name: z.string(),
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

const abilitiesRecord = z.record(abilityNameSchema, z.number().min(0).max(30));
const savesRecord = z.record(abilityNameSchema, z.boolean());
const skillsRecord = z.record(skillNameSchema, proficiencyLevelSchema);
const conditionsRecord = z.record(conditionNameSchema, z.boolean());

export const characterSheetSchema = z.object({
  schemaVersion: z.number().default(1),

  name: z.string(),
  class: z.string(),
  level: z.number().min(1).max(20),
  background: z.string(),
  playerName: z.string(),
  race: z.string(),
  alignment: z.string(),
  experiencePoints: z.number().min(0),
  inspiration: z.boolean(),

  abilities: abilitiesRecord,
  savingThrowProficiencies: savesRecord,
  skillProficiencies: skillsRecord,

  equippedArmor: armorSchema,
  equippedShield: shieldSchema.nullable(),
  miscACBonus: z.number(),
  speed: z.number().min(0),

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
  classEquipmentSelections: z.record(z.string(), z.string()).default({}),
  languageChoices: z.array(z.string()).default([]),

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
  return result.data as CharacterSheet;
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
    return { ok: true, sheet: result.data as CharacterSheet };
  }
  return { ok: false, error: z.prettifyError(result.error) };
}
