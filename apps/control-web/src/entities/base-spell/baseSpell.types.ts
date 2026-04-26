import type { CampaignSystemType } from "../campaign";

export const SpellSchool = {
  ABJURATION: "abjuration",
  CONJURATION: "conjuration",
  DIVINATION: "divination",
  ENCHANTMENT: "enchantment",
  EVOCATION: "evocation",
  ILLUSION: "illusion",
  NECROMANCY: "necromancy",
  TRANSMUTATION: "transmutation"
} as const;

export type SpellSchool = (typeof SpellSchool)[keyof typeof SpellSchool];

export const CastingTimeType = {
  ACTION: "action",
  BONUS_ACTION: "bonus_action",
  REACTION: "reaction",
  MINUTE_1: "1_minute",
  MINUTES_10: "10_minutes",
  HOUR_1: "1_hour",
  HOURS_8: "8_hours",
  HOURS_12: "12_hours",
  HOURS_24: "24_hours",
  SPECIAL: "special"
} as const;

export type CastingTimeType =
  (typeof CastingTimeType)[keyof typeof CastingTimeType];

export const TargetType = {
  SELF: "self",
  TOUCH: "touch",
  RANGED: "ranged",
  SPECIAL: "special"
} as const;

export type TargetType = (typeof TargetType)[keyof typeof TargetType];

export const SpellSelectionType = {
  NONE: "none",
  SELF: "self",
  CREATURE: "creature",
  OBJECT: "object",
  CREATURE_OR_OBJECT: "creature_or_object",
  POINT: "point",
  DIRECTION: "direction"
} as const;

export type SpellSelectionType =
  (typeof SpellSelectionType)[keyof typeof SpellSelectionType];

export const SpellOriginType = {
  CASTER: "caster",
  SELECTED_TARGET: "selected_target",
  SELECTED_POINT: "selected_point"
} as const;

export type SpellOriginType =
  (typeof SpellOriginType)[keyof typeof SpellOriginType];

export const SpellTargetAnchor = {
  CASTER: "caster",
  SELECTED_TARGET: "selected_target",
  SELECTED_POINT: "selected_point",
  TRIGGER_TARGET: "trigger_target"
} as const;

export type SpellTargetAnchor =
  (typeof SpellTargetAnchor)[keyof typeof SpellTargetAnchor];

export const SpellAttackType = {
  NONE: "none",
  MELEE_SPELL: "melee_spell",
  RANGED_SPELL: "ranged_spell"
} as const;

export type SpellAttackType =
  (typeof SpellAttackType)[keyof typeof SpellAttackType];

export const SpellRangeKind = {
  SELF: "self",
  TOUCH: "touch",
  DISTANCE: "distance"
} as const;

export type SpellRangeKind =
  (typeof SpellRangeKind)[keyof typeof SpellRangeKind];

export const SpellEffectTiming = {
  IMMEDIATE: "immediate",
  PERSISTENT: "persistent",
  TRIGGERED: "triggered"
} as const;

export type SpellEffectTiming =
  (typeof SpellEffectTiming)[keyof typeof SpellEffectTiming];

export const AreaShape = {
  CONE: "cone",
  CUBE: "cube",
  SPHERE: "sphere",
  LINE: "line",
  CYLINDER: "cylinder"
} as const;

export type AreaShape = (typeof AreaShape)[keyof typeof AreaShape];

export const ResolutionType = {
  DAMAGE: "damage",
  HEAL: "heal",
  BUFF: "buff",
  DEBUFF: "debuff",
  CONTROL: "control",
  UTILITY: "utility"
} as const;

export type ResolutionType =
  (typeof ResolutionType)[keyof typeof ResolutionType];

export const UpcastMode = {
  EXTRA_DAMAGE_DICE: "extra_damage_dice",
  EXTRA_HEAL_DICE: "extra_heal_dice",
  FLAT_BONUS: "flat_bonus",
  ADDITIONAL_EFFECT_INSTANCES: "additional_effect_instances",
  ADDITIONAL_TARGETS: "additional_targets",
  DURATION_SCALING: "duration_scaling",
  EFFECT_SCALING: "effect_scaling",
  EXTRA_EFFECT: "extra_effect"
} as const;

export type UpcastMode = (typeof UpcastMode)[keyof typeof UpcastMode];

export type SpellUpcast = {
  mode: UpcastMode;
  dice?: string | null;
  flat?: number | null;
  perLevel?: number | null;
  maxLevel?: number | null;
  scalingKey?: string | null;
  scalingSummary?: string | null;
  scalingEditorial?: string | null;
  unlockKey?: string | null;
  unlockSummary?: string | null;
  unlockEditorial?: string | null;
};

export type SpellCantripScaling = {
  mode: "character_level";
  thresholds: Array<{
    characterLevel: number;
    damage: {
      dice: string;
    };
  }>;
};

export const SpellSource = {
  ADMIN_PANEL: "admin_panel",
  SEED_JSON_BOOTSTRAP: "seed_json_bootstrap"
} as const;

export type SpellSource = (typeof SpellSource)[keyof typeof SpellSource];

export const SpellSavingThrow = {
  STR: "STR",
  DEX: "DEX",
  CON: "CON",
  INT: "INT",
  WIS: "WIS",
  CHA: "CHA"
} as const;

export type SpellSavingThrow =
  (typeof SpellSavingThrow)[keyof typeof SpellSavingThrow];

export const SpellDamageType = {
  ACID: "Acid",
  BLUDGEONING: "Bludgeoning",
  COLD: "Cold",
  FIRE: "Fire",
  FORCE: "Force",
  LIGHTNING: "Lightning",
  NECROTIC: "Necrotic",
  PIERCING: "Piercing",
  POISON: "Poison",
  PSYCHIC: "Psychic",
  RADIANT: "Radiant",
  SLASHING: "Slashing",
  THUNDER: "Thunder"
} as const;

export type SpellDamageType =
  (typeof SpellDamageType)[keyof typeof SpellDamageType];

export const SaveSuccessOutcome = {
  NONE: "none",
  HALF_DAMAGE: "half_damage"
} as const;

export type SaveSuccessOutcome =
  (typeof SaveSuccessOutcome)[keyof typeof SaveSuccessOutcome];

export type BaseSpellAlias = {
  id: string;
  alias: string;
  locale?: string | null;
  aliasType?: string | null;
};

export type BaseSpell = {
  id: string;
  system: CampaignSystemType;
  canonicalKey: string;
  nameEn: string;
  namePt?: string | null;
  descriptionEn: string;
  descriptionPt?: string | null;
  level: number;
  school: SpellSchool;
  classesJson?: string[] | null;

  // Casting
  castingTimeType?: CastingTimeType | null;
  castingTime?: string | null;
  rangeMeters?: number | null;
  rangeText?: string | null;
  targetType?: TargetType | null;
  maxTargets?: number | null;
  selectionType?: SpellSelectionType | null;
  originType?: SpellOriginType | null;
  targetAnchor?: SpellTargetAnchor | null;
  attackType?: SpellAttackType | null;
  rangeKind?: SpellRangeKind | null;
  effectTiming?: SpellEffectTiming | null;
  areaShape?: AreaShape | null;
  /** AoE radius in meters — sphere, cylinder. */
  radiusMeters?: number | null;
  /** AoE length in meters — cone, line. */
  lengthMeters?: number | null;
  /** AoE side length in meters — cube. */
  sideMeters?: number | null;
  duration?: string | null;
  componentsJson?: string[] | null;
  materialComponentText?: string | null;
  concentration: boolean;
  ritual: boolean;

  // Resolution
  resolutionType?: ResolutionType | null;
  savingThrow?: SpellSavingThrow | null;
  saveSuccessOutcome?: SaveSuccessOutcome | null;

  // Effect
  damageDice?: string | null;
  damageType?: SpellDamageType | null;
  healDice?: string | null;

  // Targeting requirements
  requiresTargetSight?: boolean | null;
  requiresTargetEffect?: boolean | null;
  requiresPointSight?: boolean | null;
  requiresPointEffect?: boolean | null;

  // Upcast
  upcast?: SpellUpcast | null;
  cantripScaling?: SpellCantripScaling | null;

  // Automation metadata (computed by backend — not stored in DB)
  automationMode?: string | null;
  defaultSpellMode?: string | null;
  requiresEffectInputs?: boolean | null;
  requiresMap?: boolean | null;
  handlerKey?: string | null;

  // Metadata
  source?: SpellSource | null;
  sourceRef?: string | null;
  isSrd: boolean;
  isActive: boolean;
  aliases: BaseSpellAlias[];
};

export type BaseSpellFilters = {
  system?: CampaignSystemType;
  level?: number;
  school?: SpellSchool;
  className?: string;
  canonicalKey?: string;
  search?: string;
  isActive?: boolean;
};

export type BaseSpellWritePayload = {
  system?: CampaignSystemType;
  canonicalKey?: string;
  nameEn?: string;
  namePt?: string | null;
  descriptionEn?: string;
  descriptionPt?: string | null;
  level?: number;
  school?: SpellSchool;
  classesJson?: string[] | null;
  castingTimeType?: CastingTimeType | null;
  castingTime?: string | null;
  rangeMeters?: number | null;
  rangeText?: string | null;
  targetType?: TargetType | null;
  maxTargets?: number | null;
  selectionType?: SpellSelectionType | null;
  originType?: SpellOriginType | null;
  targetAnchor?: SpellTargetAnchor | null;
  attackType?: SpellAttackType | null;
  rangeKind?: SpellRangeKind | null;
  effectTiming?: SpellEffectTiming | null;
  areaShape?: AreaShape | null;
  radiusMeters?: number | null;
  lengthMeters?: number | null;
  sideMeters?: number | null;
  duration?: string | null;
  componentsJson?: string[] | null;
  materialComponentText?: string | null;
  concentration?: boolean;
  ritual?: boolean;
  resolutionType?: ResolutionType | null;
  savingThrow?: SpellSavingThrow | null;
  saveSuccessOutcome?: SaveSuccessOutcome | null;
  damageDice?: string | null;
  damageType?: SpellDamageType | null;
  healDice?: string | null;
  requiresTargetSight?: boolean | null;
  requiresTargetEffect?: boolean | null;
  requiresPointSight?: boolean | null;
  requiresPointEffect?: boolean | null;
  upcast?: SpellUpcast | null;
  cantripScaling?: SpellCantripScaling | null;
  source?: SpellSource | null;
  sourceRef?: string | null;
  isSrd?: boolean;
  isActive?: boolean;
};
