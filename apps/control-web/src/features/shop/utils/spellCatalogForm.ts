import {
  CastingTimeType as CastingTimeTypeValues,
  ResolutionType as ResolutionTypeValues,
  SaveSuccessOutcome as SaveSuccessOutcomeValues,
  SpellDamageType as SpellDamageTypeValues,
  SpellSavingThrow as SpellSavingThrowValues,
  SpellSchool,
  TargetMode as TargetModeValues,
  UpcastMode as UpcastModeValues,
  type BaseSpell,
  type CastingTimeType,
  type ResolutionType,
  type SaveSuccessOutcome,
  type SpellDamageType,
  type SpellSavingThrow,
  type TargetMode,
  type UpcastMode,
} from "../../../entities/base-spell";
import type { BaseSpellUpdatePayload } from "../../../shared/api/baseSpellsRepo";
import type { CampaignSpellCreatePayload } from "../../../shared/api/campaignSpellsRepo";

export const SPELL_LEVEL_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;

export const SPELL_SCHOOL_OPTIONS = Object.values(SpellSchool);

export const SPELL_CASTING_TIME_TYPE_OPTIONS = Object.values(CastingTimeTypeValues);

export const SPELL_TARGET_MODE_OPTIONS = Object.values(TargetModeValues);

export const SPELL_RESOLUTION_TYPE_OPTIONS = Object.values(ResolutionTypeValues);

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

export const SPELL_UPCAST_MODE_OPTIONS = Object.values(UpcastModeValues);

const SPELL_CLASS_OPTION_SET = new Set<string>(SPELL_CLASS_OPTIONS);
const SPELL_COMPONENT_OPTION_SET = new Set<string>(SPELL_COMPONENT_OPTIONS);
const SPELL_DAMAGE_TYPE_OPTION_SET = new Set<string>(SPELL_DAMAGE_TYPE_OPTIONS);
const SPELL_SAVING_THROW_OPTION_SET = new Set<string>(SPELL_SAVING_THROW_OPTIONS);
const SPELL_SAVE_SUCCESS_OUTCOME_OPTION_SET = new Set<string>(SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS);

const CASTING_TIME_LABELS: Record<CastingTimeType, string> = {
  action: "1 action",
  bonus_action: "1 bonus action",
  reaction: "1 reaction",
  "1_minute": "1 minute",
  "10_minutes": "10 minutes",
  "1_hour": "1 hour",
  "8_hours": "8 hours",
  "12_hours": "12 hours",
  "24_hours": "24 hours",
  special: "Special",
};

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

export const normalizeSpellCanonicalKey = (value: string) =>
  value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");

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

const toNullableBoolean = (value: boolean | null) => value;

const toNullablePositiveInteger = (value: string, fallback?: number) => {
  const normalized = value.trim();
  if (!normalized) {
    return fallback ?? null;
  }

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return fallback ?? null;
  }

  return Math.max(0, Math.trunc(parsed));
};

const deriveCastingTimeText = (
  castingTimeType: SpellCatalogEditorState["castingTimeType"],
  castingTime: string,
) => {
  const editorialText = toNullableText(castingTime);
  if (editorialText) {
    return editorialText;
  }

  if (!castingTimeType) {
    return null;
  }

  return CASTING_TIME_LABELS[castingTimeType] ?? null;
};

const supportsSavingThrow = (resolutionType: SpellCatalogEditorState["resolutionType"]) =>
  resolutionType === "damage" ||
  resolutionType === "control" ||
  resolutionType === "debuff";

const buildStructuredUpcast = (
  state: SpellCatalogEditorState,
): BaseSpellUpdatePayload["upcast"] => {
  if (!state.upcastMode) {
    return null;
  }

  return {
    mode: state.upcastMode,
    dice: toNullableText(state.upcastDice),
    flat: toNullablePositiveInteger(state.upcastFlat),
    perLevel: toNullablePositiveInteger(state.upcastPerLevel, 1),
    maxLevel: toNullablePositiveInteger(state.upcastMaxLevel),
    scalingKey:
      state.upcastMode === "effect_scaling" ? toNullableText(state.upcastScalingKey) : null,
    scalingSummary:
      state.upcastMode === "effect_scaling"
        ? toNullableText(state.upcastScalingSummary)
        : null,
    scalingEditorial:
      state.upcastMode === "effect_scaling"
        ? toNullableText(state.upcastScalingEditorial)
        : null,
    unlockKey:
      state.upcastMode === "extra_effect" ? toNullableText(state.upcastUnlockKey) : null,
    unlockSummary:
      state.upcastMode === "extra_effect"
        ? toNullableText(state.upcastUnlockSummary)
        : null,
    unlockEditorial:
      state.upcastMode === "extra_effect"
        ? toNullableText(state.upcastUnlockEditorial)
        : null,
  };
};

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
  castingTimeType: toNullableText(state.castingTimeType) as CastingTimeType | null,
  nameEn: state.nameEn.trim(),
  namePt: toNullableText(state.namePt),
  descriptionEn: state.descriptionEn.trim(),
  descriptionPt: toNullableText(state.descriptionPt),
  level: state.level,
  school: state.school,
  classesJson: state.classesJson.length > 0 ? state.classesJson : null,
  castingTime: deriveCastingTimeText(state.castingTimeType, state.castingTime),
  rangeMeters: toNullableInteger(state.rangeMeters),
  rangeText: toNullableText(state.rangeText),
  targetMode: toNullableText(state.targetMode) as TargetMode | null,
  areaSizeMeters: toNullableInteger(state.areaSizeMeters),
  duration: toNullableText(state.duration),
  componentsJson: state.componentsJson.length > 0 ? state.componentsJson : null,
  materialComponentText: state.componentsJson.includes("M")
    ? toNullableText(state.materialComponentText)
    : null,
  concentration: state.concentration,
  ritual: state.ritual,
  resolutionType: toNullableText(state.resolutionType) as ResolutionType | null,
  damageDice: state.resolutionType === "damage" ? toNullableText(state.damageDice) : null,
  damageType:
    state.resolutionType === "damage"
      ? (toNullableText(state.damageType) as SpellDamageType | null)
      : null,
  healDice: state.resolutionType === "heal" ? toNullableText(state.healDice) : null,
  savingThrow: supportsSavingThrow(state.resolutionType)
    ? (toNullableText(state.savingThrow) as SpellSavingThrow | null)
    : null,
  saveSuccessOutcome:
    state.resolutionType === "damage" && state.savingThrow
      ? ((toNullableText(state.saveSuccessOutcome) as SaveSuccessOutcome | null) ?? null)
      : null,
  requiresTargetSight: toNullableBoolean(state.requiresTargetSight),
  requiresTargetEffect: toNullableBoolean(state.requiresTargetEffect),
  requiresPointSight: toNullableBoolean(state.requiresPointSight),
  requiresPointEffect: toNullableBoolean(state.requiresPointEffect),
  upcast: buildStructuredUpcast(state),
});

export const buildSpellCreatePayload = (
  state: SpellCatalogEditorState,
): CampaignSpellCreatePayload => ({
  canonicalKey: normalizeSpellCanonicalKey(state.canonicalKey),
  ...buildSpellUpdatePayload(state),
  nameEn: state.nameEn.trim(),
  descriptionEn: state.descriptionEn.trim(),
  level: state.level,
  school: state.school,
});

export type SpellCatalogEditorState = {
  canonicalKey: string;
  nameEn: string;
  namePt: string;
  descriptionEn: string;
  descriptionPt: string;
  level: number;
  school: BaseSpell["school"];
  classesJson: string[];
  castingTimeType: CastingTimeType | "";
  castingTime: string;
  rangeMeters: string;
  rangeText: string;
  targetMode: TargetMode | "";
  duration: string;
  componentsJson: string[];
  materialComponentText: string;
  concentration: boolean;
  ritual: boolean;
  resolutionType: ResolutionType | "";
  damageDice: string;
  damageType: string;
  healDice: string;
  savingThrow: string;
  saveSuccessOutcome: string;
  areaSizeMeters: string;
  requiresTargetSight: boolean | null;
  requiresTargetEffect: boolean | null;
  requiresPointSight: boolean | null;
  requiresPointEffect: boolean | null;
  upcastMode: UpcastMode | "";
  upcastDice: string;
  upcastFlat: string;
  upcastPerLevel: string;
  upcastMaxLevel: string;
  upcastScalingKey: string;
  upcastScalingSummary: string;
  upcastScalingEditorial: string;
  upcastUnlockKey: string;
  upcastUnlockSummary: string;
  upcastUnlockEditorial: string;
};

export const createSpellEditorState = (spell: BaseSpell): SpellCatalogEditorState => ({
  canonicalKey: spell.canonicalKey,
  nameEn: spell.nameEn,
  namePt: spell.namePt ?? "",
  descriptionEn: spell.descriptionEn,
  descriptionPt: spell.descriptionPt ?? "",
  level: spell.level,
  school: spell.school,
  classesJson: filterKnownSpellValues(spell.classesJson, SPELL_CLASS_OPTION_SET),
  castingTimeType: spell.castingTimeType ?? "",
  castingTime: spell.castingTime ?? "",
  rangeMeters: spell.rangeMeters != null ? String(spell.rangeMeters) : "",
  rangeText: spell.rangeText ?? "",
  targetMode: spell.targetMode ?? "",
  areaSizeMeters: spell.areaSizeMeters != null ? String(spell.areaSizeMeters) : "",
  duration: spell.duration ?? "",
  componentsJson: filterKnownSpellValues(spell.componentsJson, SPELL_COMPONENT_OPTION_SET),
  materialComponentText: spell.materialComponentText ?? "",
  concentration: spell.concentration,
  ritual: spell.ritual,
  resolutionType: spell.resolutionType ?? "",
  damageDice: spell.damageDice ?? "",
  damageType: normalizeKnownSpellValue(spell.damageType, SPELL_DAMAGE_TYPE_OPTION_SET),
  healDice: spell.healDice ?? "",
  savingThrow: normalizeKnownSpellValue(spell.savingThrow, SPELL_SAVING_THROW_OPTION_SET),
  saveSuccessOutcome: normalizeKnownSpellValue(
    spell.saveSuccessOutcome,
    SPELL_SAVE_SUCCESS_OUTCOME_OPTION_SET,
  ),
  requiresTargetSight: spell.requiresTargetSight ?? null,
  requiresTargetEffect: spell.requiresTargetEffect ?? null,
  requiresPointSight: spell.requiresPointSight ?? null,
  requiresPointEffect: spell.requiresPointEffect ?? null,
  upcastMode: spell.upcast?.mode ?? "",
  upcastDice: spell.upcast?.dice ?? "",
  upcastFlat: spell.upcast?.flat != null ? String(spell.upcast.flat) : "",
  upcastPerLevel: spell.upcast?.perLevel != null ? String(spell.upcast.perLevel) : "1",
  upcastMaxLevel: spell.upcast?.maxLevel != null ? String(spell.upcast.maxLevel) : "",
  upcastScalingKey: spell.upcast?.scalingKey ?? "",
  upcastScalingSummary: spell.upcast?.scalingSummary ?? "",
  upcastScalingEditorial: spell.upcast?.scalingEditorial ?? "",
  upcastUnlockKey: spell.upcast?.unlockKey ?? "",
  upcastUnlockSummary: spell.upcast?.unlockSummary ?? "",
  upcastUnlockEditorial: spell.upcast?.unlockEditorial ?? "",
});

export const createEmptySpellEditorState = (): SpellCatalogEditorState => ({
  canonicalKey: "",
  nameEn: "",
  namePt: "",
  descriptionEn: "",
  descriptionPt: "",
  level: 0,
  school: SpellSchool.EVOCATION,
  classesJson: [],
  castingTimeType: "action",
  castingTime: "",
  rangeMeters: "",
  rangeText: "",
  targetMode: "",
  areaSizeMeters: "",
  duration: "",
  componentsJson: [],
  materialComponentText: "",
  concentration: false,
  ritual: false,
  resolutionType: "",
  damageDice: "",
  damageType: "",
  healDice: "",
  savingThrow: "",
  saveSuccessOutcome: "",
  requiresTargetSight: null,
  requiresTargetEffect: null,
  requiresPointSight: null,
  requiresPointEffect: null,
  upcastMode: "",
  upcastDice: "",
  upcastFlat: "",
  upcastPerLevel: "1",
  upcastMaxLevel: "",
  upcastScalingKey: "",
  upcastScalingSummary: "",
  upcastScalingEditorial: "",
  upcastUnlockKey: "",
  upcastUnlockSummary: "",
  upcastUnlockEditorial: "",
});
