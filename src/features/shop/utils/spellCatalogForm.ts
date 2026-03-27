import { SpellSchool, type BaseSpell, type SaveSuccessOutcome, type SpellDamageType, type SpellSavingThrow } from "../../../entities/base-spell";
import type { BaseSpellUpdatePayload } from "../../../shared/api/baseSpellsRepo";

export const SPELL_LEVEL_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;

export const SPELL_SCHOOL_OPTIONS = Object.values(SpellSchool);

export const SPELL_CLASS_OPTIONS = [
  "Bard",
  "Cleric",
  "Druid",
  "Paladin",
  "Ranger",
  "Sorcerer",
  "Warlock",
  "Wizard",
] as const;

export const SPELL_COMPONENT_OPTIONS = ["V", "S", "M"] as const;

export const SPELL_DAMAGE_TYPE_OPTIONS = [
  "Acid",
  "Bludgeoning",
  "Cold",
  "Fire",
  "Force",
  "Lightning",
  "Necrotic",
  "Piercing",
  "Poison",
  "Psychic",
  "Radiant",
  "Slashing",
  "Thunder",
] as const;

export const SPELL_SAVING_THROW_OPTIONS = [
  "STR",
  "DEX",
  "CON",
  "INT",
  "WIS",
  "CHA",
] as const;

export const SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS = ["none", "half_damage"] as const;

const SPELL_CLASS_OPTION_SET = new Set<string>(SPELL_CLASS_OPTIONS);
const SPELL_COMPONENT_OPTION_SET = new Set<string>(SPELL_COMPONENT_OPTIONS);
const SPELL_DAMAGE_TYPE_OPTION_SET = new Set<string>(SPELL_DAMAGE_TYPE_OPTIONS);
const SPELL_SAVING_THROW_OPTION_SET = new Set<string>(SPELL_SAVING_THROW_OPTIONS);
const SPELL_SAVE_SUCCESS_OUTCOME_OPTION_SET = new Set<string>(SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS);

export const toggleSpellListValue = (current: string[], value: string) =>
  current.includes(value)
    ? current.filter((entry) => entry !== value)
    : [...current, value];

export const toDelimitedText = (values?: string[] | null) =>
  values?.join(", ") ?? "";

export const toNullableText = (value: string) => {
  const normalized = value.trim();
  return normalized ? normalized : null;
};

const toNullableInteger = (value: string) => {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
};

const filterKnownSpellValues = (values: readonly string[] | null | undefined, allowed: Set<string>) =>
  (values ?? []).filter((value) => allowed.has(value));

const normalizeKnownSpellValue = (value: string | null | undefined, allowed: Set<string>) =>
  value && allowed.has(value) ? value : "";

export const getUnsupportedSpellEditorValues = (spell: BaseSpell) => {
  const values = [
    ...(spell.classesJson ?? []).filter((value) => !SPELL_CLASS_OPTION_SET.has(value)),
    ...(spell.componentsJson ?? []).filter((value) => !SPELL_COMPONENT_OPTION_SET.has(value)),
  ];

  if (spell.damageType && !SPELL_DAMAGE_TYPE_OPTION_SET.has(spell.damageType)) {
    values.push(spell.damageType);
  }

  if (spell.savingThrow && !SPELL_SAVING_THROW_OPTION_SET.has(spell.savingThrow)) {
    values.push(spell.savingThrow);
  }

  if (
    spell.saveSuccessOutcome &&
    !SPELL_SAVE_SUCCESS_OUTCOME_OPTION_SET.has(spell.saveSuccessOutcome)
  ) {
    values.push(spell.saveSuccessOutcome);
  }

  return Array.from(new Set(values));
};

export const buildSpellUpdatePayload = (
  state: SpellCatalogEditorState,
): BaseSpellUpdatePayload => ({
  nameEn: state.nameEn.trim(),
  namePt: toNullableText(state.namePt),
  descriptionEn: state.descriptionEn.trim(),
  descriptionPt: toNullableText(state.descriptionPt),
  level: state.level,
  school: state.school,
  classesJson: state.classesJson.length > 0 ? state.classesJson : null,
  castingTime: toNullableText(state.castingTime),
  rangeMeters: toNullableInteger(state.rangeMeters),
  rangeText: toNullableText(state.rangeText),
  duration: toNullableText(state.duration),
  componentsJson: state.componentsJson.length > 0 ? state.componentsJson : null,
  materialComponentText: state.componentsJson.includes("M")
    ? toNullableText(state.materialComponentText)
    : null,
  concentration: state.concentration,
  ritual: state.ritual,
  damageType: toNullableText(state.damageType) as SpellDamageType | null,
  savingThrow: toNullableText(state.savingThrow) as SpellSavingThrow | null,
  saveSuccessOutcome: state.savingThrow ? toNullableText(state.saveSuccessOutcome) as SaveSuccessOutcome | null : null,
});

export type SpellCatalogEditorState = {
  nameEn: string;
  namePt: string;
  descriptionEn: string;
  descriptionPt: string;
  level: number;
  school: BaseSpell["school"];
  classesJson: string[];
  castingTime: string;
  rangeMeters: string;
  rangeText: string;
  duration: string;
  componentsJson: string[];
  materialComponentText: string;
  concentration: boolean;
  ritual: boolean;
  damageType: string;
  savingThrow: string;
  saveSuccessOutcome: string;
};

export const createSpellEditorState = (spell: BaseSpell): SpellCatalogEditorState => ({
  nameEn: spell.nameEn,
  namePt: spell.namePt ?? "",
  descriptionEn: spell.descriptionEn,
  descriptionPt: spell.descriptionPt ?? "",
  level: spell.level,
  school: spell.school,
  classesJson: filterKnownSpellValues(spell.classesJson, SPELL_CLASS_OPTION_SET),
  castingTime: spell.castingTime ?? "",
  rangeMeters: spell.rangeMeters != null ? String(spell.rangeMeters) : "",
  rangeText: spell.rangeText ?? "",
  duration: spell.duration ?? "",
  componentsJson: filterKnownSpellValues(spell.componentsJson, SPELL_COMPONENT_OPTION_SET),
  materialComponentText: spell.materialComponentText ?? "",
  concentration: spell.concentration,
  ritual: spell.ritual,
  damageType: normalizeKnownSpellValue(spell.damageType, SPELL_DAMAGE_TYPE_OPTION_SET),
  savingThrow: normalizeKnownSpellValue(spell.savingThrow, SPELL_SAVING_THROW_OPTION_SET),
  saveSuccessOutcome: normalizeKnownSpellValue(
    spell.saveSuccessOutcome,
    SPELL_SAVE_SUCCESS_OUTCOME_OPTION_SET,
  ),
});
