import type { CampaignSystemType } from "../campaign";

export const SpellSchool = {
  ABJURATION: "abjuration",
  CONJURATION: "conjuration",
  DIVINATION: "divination",
  ENCHANTMENT: "enchantment",
  EVOCATION: "evocation",
  ILLUSION: "illusion",
  NECROMANCY: "necromancy",
  TRANSMUTATION: "transmutation",
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
  SPECIAL: "special",
} as const;

export type CastingTimeType =
  (typeof CastingTimeType)[keyof typeof CastingTimeType];

export const TargetMode = {
  SELF: "self",
  TOUCH: "touch",
  RANGED: "ranged",
  CONE: "cone",
  CUBE: "cube",
  SPHERE: "sphere",
  LINE: "line",
  CYLINDER: "cylinder",
  SPECIAL: "special",
} as const;

export type TargetMode = (typeof TargetMode)[keyof typeof TargetMode];

export const ResolutionType = {
  NONE: "none",
  SPELL_ATTACK: "spell_attack",
  SAVING_THROW: "saving_throw",
  AUTOMATIC: "automatic",
  HEAL: "heal",
} as const;

export type ResolutionType =
  (typeof ResolutionType)[keyof typeof ResolutionType];

export const UpcastMode = {
  NONE: "none",
  ADD_DICE: "add_dice",
  ADD_TARGETS: "add_targets",
  INCREASE_DURATION: "increase_duration",
  CUSTOM: "custom",
} as const;

export type UpcastMode = (typeof UpcastMode)[keyof typeof UpcastMode];

export const SpellSource = {
  ADMIN_PANEL: "admin_panel",
  SEED_JSON_BOOTSTRAP: "seed_json_bootstrap",
} as const;

export type SpellSource = (typeof SpellSource)[keyof typeof SpellSource];

export const SpellSavingThrow = {
  STR: "STR",
  DEX: "DEX",
  CON: "CON",
  INT: "INT",
  WIS: "WIS",
  CHA: "CHA",
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
  THUNDER: "Thunder",
} as const;

export type SpellDamageType =
  (typeof SpellDamageType)[keyof typeof SpellDamageType];

export const SaveSuccessOutcome = {
  NONE: "none",
  HALF_DAMAGE: "half_damage",
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
  targetMode?: TargetMode | null;
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

  // Upcast
  upcastMode?: UpcastMode | null;
  upcastValue?: string | null;

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
  targetMode?: TargetMode | null;
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
  upcastMode?: UpcastMode | null;
  upcastValue?: string | null;
  source?: SpellSource | null;
  sourceRef?: string | null;
  isSrd?: boolean;
  isActive?: boolean;
};
