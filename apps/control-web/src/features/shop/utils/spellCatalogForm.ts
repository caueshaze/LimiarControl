import {
  AreaShape as AreaShapeValues,
  CantripScalingEffectType as CantripScalingEffectTypeValues,
  CastingTimeType as CastingTimeTypeValues,
  ResolutionType as ResolutionTypeValues,
  SaveSuccessOutcome as SaveSuccessOutcomeValues,
  SpellDamageType as SpellDamageTypeValues,
  SpellAttackType as SpellAttackTypeValues,
  SpellEffectTiming as SpellEffectTimingValues,
  SpellOriginType as SpellOriginTypeValues,
  SpellRangeKind as SpellRangeKindValues,
  SpellSavingThrow as SpellSavingThrowValues,
  SpellSchool,
  SpellSelectionType as SpellSelectionTypeValues,
  SpellTargetAnchor as SpellTargetAnchorValues,
  TargetType as TargetTypeValues,
  UpcastMode as UpcastModeValues,
  type AreaShape,
  type BaseSpell,
  type CantripScalingEffectType,
  type CantripScalingThresholdInstances,
  type CastingTimeType,
  type ResolutionType,
  type SaveSuccessOutcome,
  type SpellDamageType,
  type SpellDeclarativeEffect,
  type SpellVariant,
  type SpellPersistentAreaKind,
  type SpellPersistentAreaObscurement,
  type SpellPersistentAreaTerrainEffect,
  type SpellAttackType,
  type SpellEffectTiming,
  type SpellOriginType,
  type SpellRangeKind,
  type SpellSavingThrow,
  type SpellSelectionType,
  type SpellTargetAnchor,
  type TargetType,
  type UpcastMode,
} from "../../../entities/base-spell";
import type { Locale } from "../../../shared/i18n";
import type { BaseSpellUpdatePayload } from "../../../shared/api/baseSpellsRepo";
import type { CampaignSpellCreatePayload } from "../../../shared/api/campaignSpellsRepo";
import { normalizeSpellVariantsForPayload } from "./spellVariantEditor";

export const SPELL_LEVEL_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;

export const SPELL_SCHOOL_OPTIONS = Object.values(SpellSchool);

export const SPELL_CASTING_TIME_TYPE_OPTIONS = Object.values(CastingTimeTypeValues);

export const SPELL_TARGET_TYPE_OPTIONS = Object.values(TargetTypeValues);
export const SPELL_SELECTION_TYPE_OPTIONS = Object.values(SpellSelectionTypeValues);
export const SPELL_ORIGIN_TYPE_OPTIONS = Object.values(SpellOriginTypeValues);
export const SPELL_TARGET_ANCHOR_OPTIONS = Object.values(SpellTargetAnchorValues);
export const SPELL_ATTACK_TYPE_OPTIONS = Object.values(SpellAttackTypeValues);
export const SPELL_RANGE_KIND_OPTIONS = Object.values(SpellRangeKindValues);
export const SPELL_EFFECT_TIMING_OPTIONS = Object.values(SpellEffectTimingValues);
export const SPELL_AREA_SHAPE_OPTIONS = Object.values(AreaShapeValues);

export const SPELL_RESOLUTION_TYPE_OPTIONS = Object.values(ResolutionTypeValues);

export const SPELL_CLASS_OPTIONS = [
  "Bard",
  "Cleric",
  "Druid",
  "Guardian",
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
export const SPELL_COVER_APPLIES_TO_SAVE_OPTIONS = ["none", "physical"] as const;
export const SPELL_DICE_COUNT_OPTIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] as const;
export const SPELL_DIE_SIZE_OPTIONS = [4, 6, 8, 10, 12] as const;

export const SPELL_UPCAST_MODE_OPTIONS = Object.values(UpcastModeValues);
export const SPELL_CANTRIP_SCALING_EFFECT_TYPE_OPTIONS = Object.values(CantripScalingEffectTypeValues);
export const SPELL_PERSISTENT_AREA_KIND_OPTIONS = ["obscurement", "hazard", "no_semantic_effect"] as const;
export const SPELL_PERSISTENT_AREA_OBSCUREMENT_OPTIONS = ["heavily_obscured"] as const;
export const SPELL_PERSISTENT_AREA_TERRAIN_OPTIONS = ["difficult_terrain"] as const;

const SPELL_CLASS_OPTION_SET = new Set<string>(SPELL_CLASS_OPTIONS);
const SPELL_COMPONENT_OPTION_SET = new Set<string>(SPELL_COMPONENT_OPTIONS);
const SPELL_DAMAGE_TYPE_OPTION_SET = new Set<string>(SPELL_DAMAGE_TYPE_OPTIONS);
const SPELL_SAVING_THROW_OPTION_SET = new Set<string>(SPELL_SAVING_THROW_OPTIONS);
const SPELL_SAVE_SUCCESS_OUTCOME_OPTION_SET = new Set<string>(SPELL_SAVE_SUCCESS_OUTCOME_OPTIONS);
const SPELL_COVER_APPLIES_TO_SAVE_OPTION_SET = new Set<string>(SPELL_COVER_APPLIES_TO_SAVE_OPTIONS);

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

const parseDiceParts = (value?: string | null) => {
  const match = value?.trim().match(/^(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?$/i);
  if (!match) {
    return { count: "", size: "", bonus: "" };
  }
  const sign = match[3] === "-" ? "-" : "";
  return {
    count: match[1] ?? "",
    size: match[2] ?? "",
    bonus: match[4] ? `${sign}${match[4]}` : "",
  };
};

const buildDiceExpression = (count: string, size: string, bonus: string) => {
  const parsedCount = toNullableInteger(count);
  const parsedSize = toNullableInteger(size);
  const parsedBonus = toNullableInteger(bonus);
  if (!parsedCount || !parsedSize || parsedCount < 1 || parsedSize < 1) {
    return null;
  }
  let expression = `${parsedCount}d${parsedSize}`;
  if (parsedBonus && parsedBonus > 0) {
    expression += `+${parsedBonus}`;
  } else if (parsedBonus && parsedBonus < 0) {
    expression += `${parsedBonus}`;
  }
  return expression;
};

const toNullableFloat = (value: string) => {
  const normalized = value.trim();
  if (!normalized) return null;
  const parsed = parseFloat(normalized);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
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

const buildPersistentArea = (
  state: SpellCatalogEditorState,
): BaseSpellUpdatePayload["persistentArea"] => {
  if (state.effectTiming !== "persistent" || !state.persistentAreaKind) {
    return null;
  }

  if (state.persistentAreaKind === "obscurement") {
    const obscurement = toNullableText(
      state.persistentAreaObscurement,
    ) as SpellPersistentAreaObscurement | null;
    return obscurement
      ? {
          kind: "obscurement",
          params: { obscurement },
        }
      : null;
  }

  if (state.persistentAreaKind === "hazard") {
    const terrainEffect = toNullableText(
      state.persistentAreaTerrainEffect,
    ) as SpellPersistentAreaTerrainEffect | null;
    const movementDamageDice = toNullableText(state.persistentAreaMovementDamageDice);
    const damageType = toNullableText(state.persistentAreaDamageType) as SpellDamageType | null;
    const damagePerMeters = toNullableFloat(state.persistentAreaDamagePerMeters);

    if (!terrainEffect && !movementDamageDice && !damageType && !damagePerMeters) {
      return null;
    }

    return {
      kind: "hazard",
      params: {
        terrainEffect,
        movementDamageDice,
        damageType,
        damagePerMeters,
      },
    };
  }

  return {
    kind: "no_semantic_effect",
    params: {},
  };
};

const buildStructuredUpcast = (
  state: SpellCatalogEditorState,
): BaseSpellUpdatePayload["upcast"] => {
  if (state.level === 0 || !state.upcastMode) {
    return null;
  }

  return {
    mode: state.upcastMode,
    dice: buildDiceExpression(
      state.upcastDiceCount,
      state.upcastDieSize,
      state.upcastFixedBonus,
    ),
    flat: toNullablePositiveInteger(state.upcastFlat),
    perLevel: toNullablePositiveInteger(state.upcastPerLevel, 1),
    maxLevel: toNullablePositiveInteger(state.upcastMaxLevel),
    baseEffectInstances:
      state.upcastMode === "additional_effect_instances"
        ? toNullablePositiveInteger(state.upcastBaseEffectInstances)
        : null,
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

const buildCantripDamageThreshold = (
  characterLevel: number,
  count: string,
  size: string,
  bonus: string,
) => {
  const dice = buildDiceExpression(count, size, bonus);
  return dice ? { characterLevel, damage: { dice } } : null;
};

const buildCantripInstanceThreshold = (
  characterLevel: number,
  instanceCount: string,
  diceCount: string,
  dieSize: string,
  fixedBonus: string,
) => {
  const parsedInstances = toNullablePositiveInteger(instanceCount);
  const dice = buildDiceExpression(diceCount, dieSize, fixedBonus);
  if (!parsedInstances || parsedInstances < 1 || !dice) return null;
  return { characterLevel, instances: parsedInstances, instanceDamage: { dice } };
};

const buildStructuredCantripScaling = (
  state: SpellCatalogEditorState,
): BaseSpellUpdatePayload["cantripScaling"] => {
  if (state.level !== 0 || state.cantripScalingMode !== "character_level") {
    return null;
  }

  const effectType: CantripScalingEffectType =
    state.cantripScalingEffectType === "effect_instances" ? "effect_instances" : "damage_dice";

  const LEVELS = [
    { level: 1, countKey: "cantripLevel1DiceCount" as const, dieKey: "cantripLevel1DieSize" as const, bonusKey: "cantripLevel1FixedBonus" as const, instanceCountKey: "cantripLevel1InstanceCount" as const, instanceDiceCountKey: "cantripLevel1InstanceDiceCount" as const, instanceDieSizeKey: "cantripLevel1InstanceDieSize" as const, instanceBonusKey: "cantripLevel1InstanceFixedBonus" as const },
    { level: 5, countKey: "cantripLevel5DiceCount" as const, dieKey: "cantripLevel5DieSize" as const, bonusKey: "cantripLevel5FixedBonus" as const, instanceCountKey: "cantripLevel5InstanceCount" as const, instanceDiceCountKey: "cantripLevel5InstanceDiceCount" as const, instanceDieSizeKey: "cantripLevel5InstanceDieSize" as const, instanceBonusKey: "cantripLevel5InstanceFixedBonus" as const },
    { level: 11, countKey: "cantripLevel11DiceCount" as const, dieKey: "cantripLevel11DieSize" as const, bonusKey: "cantripLevel11FixedBonus" as const, instanceCountKey: "cantripLevel11InstanceCount" as const, instanceDiceCountKey: "cantripLevel11InstanceDiceCount" as const, instanceDieSizeKey: "cantripLevel11InstanceDieSize" as const, instanceBonusKey: "cantripLevel11InstanceFixedBonus" as const },
    { level: 17, countKey: "cantripLevel17DiceCount" as const, dieKey: "cantripLevel17DieSize" as const, bonusKey: "cantripLevel17FixedBonus" as const, instanceCountKey: "cantripLevel17InstanceCount" as const, instanceDiceCountKey: "cantripLevel17InstanceDiceCount" as const, instanceDieSizeKey: "cantripLevel17InstanceDieSize" as const, instanceBonusKey: "cantripLevel17InstanceFixedBonus" as const },
  ];

  if (effectType === "effect_instances") {
    const thresholds = LEVELS.map((l) =>
      buildCantripInstanceThreshold(
        l.level,
        state[l.instanceCountKey],
        state[l.instanceDiceCountKey],
        state[l.instanceDieSizeKey],
        state[l.instanceBonusKey],
      ),
    ).filter((entry): entry is NonNullable<typeof entry> => Boolean(entry));
    return thresholds.length > 0
      ? { scalingMode: "character_level", scalingEffectType: "effect_instances", thresholds }
      : null;
  }

  const thresholds = LEVELS.map((l) =>
    buildCantripDamageThreshold(
      l.level,
      state[l.countKey],
      state[l.dieKey],
      state[l.bonusKey],
    ),
  ).filter((entry): entry is NonNullable<typeof entry> => Boolean(entry));
  return thresholds.length > 0
    ? { scalingMode: "character_level", scalingEffectType: "damage_dice", thresholds }
    : null;
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
  locale: Locale = "pt",
): BaseSpellUpdatePayload => {
  const normalizedVariants = normalizeSpellVariantsForPayload(state.variants, locale);
  if (normalizedVariants.errors.length > 0) {
    throw new Error(normalizedVariants.errors[0]);
  }
  const materialOptionKeys =
    state.componentsJson.includes("M") && state.materialComponentConsumed
      ? Array.from(
          new Set(
            state.consumableMaterialOptionKeys
              .map((entry) => entry.trim())
              .filter((entry) => entry.length > 0),
          ),
        )
      : [];
  const consumableMaterialOptions = materialOptionKeys.map((key) => ({
    key,
    nameEn: key,
    namePt: key,
    quantity: 1,
  }));

  return {
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
    targetType: toNullableText(state.targetType) as TargetType | null,
    maxTargets: toNullableInteger(state.maxTargets),
    selectionType: toNullableText(state.selectionType) as SpellSelectionType | null,
    originType: toNullableText(state.originType) as SpellOriginType | null,
    targetAnchor: toNullableText(state.targetAnchor) as SpellTargetAnchor | null,
    attackType: toNullableText(state.attackType) as SpellAttackType | null,
    rangeKind: toNullableText(state.rangeKind) as SpellRangeKind | null,
    effectTiming: toNullableText(state.effectTiming) as SpellEffectTiming | null,
    areaShape: toNullableText(state.areaShape) as AreaShape | null,
    radiusMeters:
      state.areaShape === "sphere" || state.areaShape === "cylinder"
        ? toNullableFloat(state.radiusMeters)
        : null,
    lengthMeters:
      state.areaShape === "cone" || state.areaShape === "line"
        ? toNullableFloat(state.lengthMeters)
        : null,
    sideMeters:
      state.areaShape === "cube"
        ? toNullableFloat(state.sideMeters)
        : null,
    duration: toNullableText(state.duration),
    componentsJson: state.componentsJson.length > 0 ? state.componentsJson : null,
    materialComponentText:
      state.componentsJson.includes("M") && consumableMaterialOptions.length > 0
        ? `${consumableMaterialOptions.map((entry) => entry.nameEn ?? entry.key).join(" or ")}, which the spell consumes`
        : null,
    materialComponentConsumed:
      state.componentsJson.includes("M") && consumableMaterialOptions.length > 0,
    consumableMaterialOptions:
      consumableMaterialOptions.length > 0 ? consumableMaterialOptions : null,
    concentration: state.concentration,
    ritual: state.ritual,
    resolutionType: toNullableText(state.resolutionType) as ResolutionType | null,
    damageDice:
      state.resolutionType === "damage"
        ? buildDiceExpression(
            state.damageDiceCount,
            state.damageDieSize,
            state.damageFixedBonus,
          )
        : null,
    damageType:
      state.resolutionType === "damage"
        ? (toNullableText(state.damageType) as SpellDamageType | null)
        : null,
    healDice: state.resolutionType === "heal" ? toNullableText(state.healDice) : null,
    effects: state.effects.length > 0 ? state.effects : null,
    onEndEffects: state.onEndEffects.length > 0 ? state.onEndEffects : null,
    variants: normalizedVariants.variants,
    persistentArea: buildPersistentArea(state),
    savingThrow: supportsSavingThrow(state.resolutionType)
      ? (toNullableText(state.savingThrow) as SpellSavingThrow | null)
      : null,
    saveSuccessOutcome:
      state.resolutionType === "damage" && state.savingThrow
        ? ((toNullableText(state.saveSuccessOutcome) as SaveSuccessOutcome | null) ?? null)
        : null,
    coverAppliesToSave: supportsSavingThrow(state.resolutionType)
      ? ((toNullableText(state.coverAppliesToSave) as "none" | "physical" | null) ?? null)
      : null,
    requiresTargetSight: toNullableBoolean(state.requiresTargetSight),
    requiresTargetEffect: toNullableBoolean(state.requiresTargetEffect),
    requiresPointSight: toNullableBoolean(state.requiresPointSight),
    requiresPointEffect: toNullableBoolean(state.requiresPointEffect),
    upcast: buildStructuredUpcast(state),
    cantripScaling: buildStructuredCantripScaling(state),
  };
};

export const buildSpellCreatePayload = (
  state: SpellCatalogEditorState,
  locale: Locale = "pt",
): CampaignSpellCreatePayload => ({
  canonicalKey: normalizeSpellCanonicalKey(state.canonicalKey),
  ...buildSpellUpdatePayload(state, locale),
  nameEn: state.nameEn.trim(),
  descriptionEn: state.descriptionEn.trim(),
  level: state.level,
  school: state.school,
});

export const getSpellCatalogEditorVariantErrors = (
  state: SpellCatalogEditorState,
  locale: Locale = "pt",
) => normalizeSpellVariantsForPayload(state.variants, locale).errors;

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
  targetType: TargetType | "";
  maxTargets: string;
  selectionType: SpellSelectionType | "";
  originType: SpellOriginType | "";
  targetAnchor: SpellTargetAnchor | "";
  attackType: SpellAttackType | "";
  rangeKind: SpellRangeKind | "";
  effectTiming: SpellEffectTiming | "";
  areaShape: AreaShape | "";
  duration: string;
  componentsJson: string[];
  materialComponentText: string;
  materialComponentConsumed: boolean;
  consumableMaterialOptionKeys: string[];
  concentration: boolean;
  ritual: boolean;
  resolutionType: ResolutionType | "";
  damageDice: string;
  damageDiceCount: string;
  damageDieSize: string;
  damageFixedBonus: string;
  damageType: string;
  healDice: string;
  effects: SpellDeclarativeEffect[];
  onEndEffects: SpellDeclarativeEffect[];
  variants: SpellVariant[];
  persistentAreaKind: SpellPersistentAreaKind | "";
  persistentAreaObscurement: SpellPersistentAreaObscurement | "";
  persistentAreaTerrainEffect: SpellPersistentAreaTerrainEffect | "";
  persistentAreaMovementDamageDice: string;
  persistentAreaDamageType: string;
  persistentAreaDamagePerMeters: string;
  savingThrow: string;
  saveSuccessOutcome: string;
  coverAppliesToSave: "" | "none" | "physical";
  radiusMeters: string;
  lengthMeters: string;
  sideMeters: string;
  requiresTargetSight: boolean | null;
  requiresTargetEffect: boolean | null;
  requiresPointSight: boolean | null;
  requiresPointEffect: boolean | null;
  upcastMode: UpcastMode | "";
  upcastDice: string;
  upcastDiceCount: string;
  upcastDieSize: string;
  upcastFixedBonus: string;
  upcastFlat: string;
  upcastPerLevel: string;
  upcastMaxLevel: string;
  upcastBaseEffectInstances: string;
  upcastScalingKey: string;
  upcastScalingSummary: string;
  upcastScalingEditorial: string;
  upcastUnlockKey: string;
  upcastUnlockSummary: string;
  upcastUnlockEditorial: string;
  cantripScalingMode: "" | "character_level";
  cantripScalingEffectType: "" | CantripScalingEffectType;
  // damage_dice threshold fields
  cantripLevel1DiceCount: string;
  cantripLevel1DieSize: string;
  cantripLevel1FixedBonus: string;
  cantripLevel5DiceCount: string;
  cantripLevel5DieSize: string;
  cantripLevel5FixedBonus: string;
  cantripLevel11DiceCount: string;
  cantripLevel11DieSize: string;
  cantripLevel11FixedBonus: string;
  cantripLevel17DiceCount: string;
  cantripLevel17DieSize: string;
  cantripLevel17FixedBonus: string;
  // effect_instances threshold fields
  cantripLevel1InstanceCount: string;
  cantripLevel1InstanceDiceCount: string;
  cantripLevel1InstanceDieSize: string;
  cantripLevel1InstanceFixedBonus: string;
  cantripLevel5InstanceCount: string;
  cantripLevel5InstanceDiceCount: string;
  cantripLevel5InstanceDieSize: string;
  cantripLevel5InstanceFixedBonus: string;
  cantripLevel11InstanceCount: string;
  cantripLevel11InstanceDiceCount: string;
  cantripLevel11InstanceDieSize: string;
  cantripLevel11InstanceFixedBonus: string;
  cantripLevel17InstanceCount: string;
  cantripLevel17InstanceDiceCount: string;
  cantripLevel17InstanceDieSize: string;
  cantripLevel17InstanceFixedBonus: string;
};

export const createSpellEditorState = (spell: BaseSpell): SpellCatalogEditorState => ({
  ...(() => {
    const damageParts = parseDiceParts(spell.damageDice);
    const upcastParts = parseDiceParts(spell.upcast?.dice);

    const effectType = spell.cantripScaling?.scalingEffectType ?? "damage_dice";

    const thresholdDice = (level: number) => {
      const threshold = spell.cantripScaling?.thresholds.find(
        (entry) => entry.characterLevel === level,
      );
      return (threshold as { damage?: { dice: string } } | undefined)?.damage?.dice;
    };
    const cantripLevel1Parts = parseDiceParts(thresholdDice(1));
    const cantripLevel5Parts = parseDiceParts(thresholdDice(5));
    const cantripLevel11Parts = parseDiceParts(thresholdDice(11));
    const cantripLevel17Parts = parseDiceParts(thresholdDice(17));

    const instanceThreshold = (level: number): CantripScalingThresholdInstances | undefined => {
      const threshold = spell.cantripScaling?.thresholds.find(
        (entry) => entry.characterLevel === level,
      );
      if (threshold && "instances" in threshold) {
        return threshold as CantripScalingThresholdInstances;
      }
      return undefined;
    };
    const instInfo = (level: number) => {
      const t = instanceThreshold(level);
      const diceParts = parseDiceParts(t?.instanceDamage?.dice);
      return {
        instanceCount: t?.instances != null ? String(t.instances) : "",
        instanceDiceCount: diceParts.count,
        instanceDieSize: diceParts.size,
        instanceFixedBonus: diceParts.bonus,
      };
    };
    const inst1 = instInfo(1);
    const inst5 = instInfo(5);
    const inst11 = instInfo(11);
    const inst17 = instInfo(17);

    return {
      damageDiceCount: damageParts.count,
      damageDieSize: damageParts.size,
      damageFixedBonus: damageParts.bonus,
      upcastDiceCount: upcastParts.count,
      upcastDieSize: upcastParts.size,
      upcastFixedBonus: upcastParts.bonus,
      cantripScalingEffectType: effectType,
      cantripLevel1DiceCount: cantripLevel1Parts.count,
      cantripLevel1DieSize: cantripLevel1Parts.size,
      cantripLevel1FixedBonus: cantripLevel1Parts.bonus,
      cantripLevel5DiceCount: cantripLevel5Parts.count,
      cantripLevel5DieSize: cantripLevel5Parts.size,
      cantripLevel5FixedBonus: cantripLevel5Parts.bonus,
      cantripLevel11DiceCount: cantripLevel11Parts.count,
      cantripLevel11DieSize: cantripLevel11Parts.size,
      cantripLevel11FixedBonus: cantripLevel11Parts.bonus,
      cantripLevel17DiceCount: cantripLevel17Parts.count,
      cantripLevel17DieSize: cantripLevel17Parts.size,
      cantripLevel17FixedBonus: cantripLevel17Parts.bonus,
      cantripLevel1InstanceCount: inst1.instanceCount,
      cantripLevel1InstanceDiceCount: inst1.instanceDiceCount,
      cantripLevel1InstanceDieSize: inst1.instanceDieSize,
      cantripLevel1InstanceFixedBonus: inst1.instanceFixedBonus,
      cantripLevel5InstanceCount: inst5.instanceCount,
      cantripLevel5InstanceDiceCount: inst5.instanceDiceCount,
      cantripLevel5InstanceDieSize: inst5.instanceDieSize,
      cantripLevel5InstanceFixedBonus: inst5.instanceFixedBonus,
      cantripLevel11InstanceCount: inst11.instanceCount,
      cantripLevel11InstanceDiceCount: inst11.instanceDiceCount,
      cantripLevel11InstanceDieSize: inst11.instanceDieSize,
      cantripLevel11InstanceFixedBonus: inst11.instanceFixedBonus,
      cantripLevel17InstanceCount: inst17.instanceCount,
      cantripLevel17InstanceDiceCount: inst17.instanceDiceCount,
      cantripLevel17InstanceDieSize: inst17.instanceDieSize,
      cantripLevel17InstanceFixedBonus: inst17.instanceFixedBonus,
    };
  })(),
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
  targetType: spell.targetType ?? "",
  maxTargets: spell.maxTargets != null ? String(spell.maxTargets) : "",
  selectionType: spell.selectionType ?? "",
  originType: spell.originType ?? "",
  targetAnchor: spell.targetAnchor ?? "",
  attackType: spell.attackType ?? "",
  rangeKind: spell.rangeKind ?? "",
  effectTiming: spell.effectTiming ?? "",
  areaShape: spell.areaShape ?? "",
  radiusMeters:
    spell.radiusMeters != null
      ? String(spell.radiusMeters)
      : "",
  lengthMeters:
    spell.lengthMeters != null
      ? String(spell.lengthMeters)
      : "",
  sideMeters:
    spell.sideMeters != null
      ? String(spell.sideMeters)
      : "",
  duration: spell.duration ?? "",
  componentsJson: filterKnownSpellValues(spell.componentsJson, SPELL_COMPONENT_OPTION_SET),
  materialComponentText: spell.materialComponentText ?? "",
  materialComponentConsumed: Boolean(spell.materialComponentConsumed),
  consumableMaterialOptionKeys: (spell.consumableMaterialOptions ?? [])
    .map((option) => option?.key?.trim())
    .filter((key): key is string => Boolean(key)),
  concentration: spell.concentration,
  ritual: spell.ritual,
  resolutionType: spell.resolutionType ?? "",
  damageDice: spell.damageDice ?? "",
  damageType: normalizeKnownSpellValue(spell.damageType, SPELL_DAMAGE_TYPE_OPTION_SET),
  healDice: spell.healDice ?? "",
  effects: spell.effects ?? [],
  onEndEffects: spell.onEndEffects ?? [],
  variants: spell.variants ?? [],
  persistentAreaKind: spell.persistentArea?.kind ?? "",
  persistentAreaObscurement:
    spell.persistentArea?.kind === "obscurement"
      ? spell.persistentArea.params.obscurement
      : "",
  persistentAreaTerrainEffect:
    spell.persistentArea?.kind === "hazard"
      ? (spell.persistentArea.params.terrainEffect ?? "")
      : "",
  persistentAreaMovementDamageDice:
    spell.persistentArea?.kind === "hazard"
      ? (spell.persistentArea.params.movementDamageDice ?? "")
      : "",
  persistentAreaDamageType:
    spell.persistentArea?.kind === "hazard"
      ? normalizeKnownSpellValue(spell.persistentArea.params.damageType, SPELL_DAMAGE_TYPE_OPTION_SET)
      : "",
  persistentAreaDamagePerMeters:
    spell.persistentArea?.kind === "hazard" && spell.persistentArea.params.damagePerMeters != null
      ? String(spell.persistentArea.params.damagePerMeters)
      : "",
  savingThrow: normalizeKnownSpellValue(spell.savingThrow, SPELL_SAVING_THROW_OPTION_SET),
  saveSuccessOutcome: normalizeKnownSpellValue(
    spell.saveSuccessOutcome,
    SPELL_SAVE_SUCCESS_OUTCOME_OPTION_SET,
  ),
  coverAppliesToSave: normalizeKnownSpellValue(
    spell.coverAppliesToSave,
    SPELL_COVER_APPLIES_TO_SAVE_OPTION_SET,
  ) as SpellCatalogEditorState["coverAppliesToSave"],
  requiresTargetSight: spell.requiresTargetSight ?? null,
  requiresTargetEffect: spell.requiresTargetEffect ?? null,
  requiresPointSight: spell.requiresPointSight ?? null,
  requiresPointEffect: spell.requiresPointEffect ?? null,
  upcastMode: spell.upcast?.mode ?? "",
  upcastDice: spell.upcast?.dice ?? "",
  upcastFlat: spell.upcast?.flat != null ? String(spell.upcast.flat) : "",
  upcastPerLevel: spell.upcast?.perLevel != null ? String(spell.upcast.perLevel) : "1",
  upcastMaxLevel: spell.upcast?.maxLevel != null ? String(spell.upcast.maxLevel) : "",
  upcastBaseEffectInstances:
    spell.upcast?.baseEffectInstances != null ? String(spell.upcast.baseEffectInstances) : "",
  upcastScalingKey: spell.upcast?.scalingKey ?? "",
  upcastScalingSummary: spell.upcast?.scalingSummary ?? "",
  upcastScalingEditorial: spell.upcast?.scalingEditorial ?? "",
  upcastUnlockKey: spell.upcast?.unlockKey ?? "",
  upcastUnlockSummary: spell.upcast?.unlockSummary ?? "",
  upcastUnlockEditorial: spell.upcast?.unlockEditorial ?? "",
  cantripScalingMode: (spell.cantripScaling?.scalingMode ?? spell.cantripScaling?.mode) ? "character_level" : "",
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
  targetType: "",
  maxTargets: "",
  selectionType: "",
  originType: "",
  targetAnchor: "",
  attackType: "",
  rangeKind: "",
  effectTiming: "",
  areaShape: "",
  radiusMeters: "",
  lengthMeters: "",
  sideMeters: "",
  duration: "",
  componentsJson: [],
  materialComponentText: "",
  materialComponentConsumed: false,
  consumableMaterialOptionKeys: [],
  concentration: false,
  ritual: false,
  resolutionType: "",
  damageDice: "",
  damageDiceCount: "",
  damageDieSize: "",
  damageFixedBonus: "",
  damageType: "",
  healDice: "",
  effects: [],
  onEndEffects: [],
  variants: [],
  persistentAreaKind: "",
  persistentAreaObscurement: "",
  persistentAreaTerrainEffect: "",
  persistentAreaMovementDamageDice: "",
  persistentAreaDamageType: "",
  persistentAreaDamagePerMeters: "",
  savingThrow: "",
  saveSuccessOutcome: "",
  coverAppliesToSave: "",
  requiresTargetSight: null,
  requiresTargetEffect: null,
  requiresPointSight: null,
  requiresPointEffect: null,
  upcastMode: "",
  upcastDice: "",
  upcastDiceCount: "",
  upcastDieSize: "",
  upcastFixedBonus: "",
  upcastFlat: "",
  upcastPerLevel: "1",
  upcastMaxLevel: "",
  upcastBaseEffectInstances: "",
  upcastScalingKey: "",
  upcastScalingSummary: "",
  upcastScalingEditorial: "",
  upcastUnlockKey: "",
  upcastUnlockSummary: "",
  upcastUnlockEditorial: "",
  cantripScalingMode: "character_level",
  cantripScalingEffectType: "damage_dice",
  cantripLevel1DiceCount: "1",
  cantripLevel1DieSize: "6",
  cantripLevel1FixedBonus: "",
  cantripLevel5DiceCount: "2",
  cantripLevel5DieSize: "6",
  cantripLevel5FixedBonus: "",
  cantripLevel11DiceCount: "3",
  cantripLevel11DieSize: "6",
  cantripLevel11FixedBonus: "",
  cantripLevel17DiceCount: "4",
  cantripLevel17DieSize: "6",
  cantripLevel17FixedBonus: "",
  cantripLevel1InstanceCount: "1",
  cantripLevel1InstanceDiceCount: "1",
  cantripLevel1InstanceDieSize: "10",
  cantripLevel1InstanceFixedBonus: "",
  cantripLevel5InstanceCount: "2",
  cantripLevel5InstanceDiceCount: "1",
  cantripLevel5InstanceDieSize: "10",
  cantripLevel5InstanceFixedBonus: "",
  cantripLevel11InstanceCount: "3",
  cantripLevel11InstanceDiceCount: "1",
  cantripLevel11InstanceDieSize: "10",
  cantripLevel11InstanceFixedBonus: "",
  cantripLevel17InstanceCount: "4",
  cantripLevel17InstanceDiceCount: "1",
  cantripLevel17InstanceDieSize: "10",
  cantripLevel17InstanceFixedBonus: "",
});
