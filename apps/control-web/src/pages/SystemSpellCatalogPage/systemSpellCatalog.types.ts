import type {
  BaseSpell,
  CastingTimeType,
  ResolutionType,
  SaveSuccessOutcome,
  SpellDamageType,
  SpellSavingThrow,
  SpellSchool,
  SpellSource,
  TargetMode,
  UpcastMode,
} from "../../entities/base-spell";
import {
  CastingTimeType as CastingTimeTypeValues,
  ResolutionType as ResolutionTypeValues,
  SaveSuccessOutcome as SaveSuccessOutcomeValues,
  SpellDamageType as SpellDamageTypeValues,
  SpellSavingThrow as SpellSavingThrowValues,
  SpellSchool as SpellSchoolValues,
  SpellSource as SpellSourceValues,
  TargetMode as TargetModeValues,
  UpcastMode as UpcastModeValues,
} from "../../entities/base-spell";

export type ActiveFilter = "all" | "active" | "inactive";
export type LevelFilter = "ALL" | number;
export type SchoolFilter = "ALL" | SpellSchool;

export type FormState = {
  system: BaseSpell["system"];
  canonicalKey: string;
  nameEn: string;
  namePt: string;
  descriptionEn: string;
  descriptionPt: string;
  level: number;
  school: SpellSchool;
  classesJson: string[];
  castingTimeType: CastingTimeType | "";
  rangeMeters: string;
  targetMode: TargetMode | "";
  duration: string;
  componentsJson: string[];
  materialComponentText: string;
  concentration: boolean;
  ritual: boolean;
  resolutionType: ResolutionType | "";
  savingThrow: SpellSavingThrow | "";
  saveSuccessOutcome: SaveSuccessOutcome | "";
  damageDice: string;
  damageType: SpellDamageType | "";
  healDice: string;
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
  source: SpellSource;
  sourceRef: string;
  isSrd: boolean;
  isActive: boolean;
};

export { SpellSchoolValues, SpellSourceValues, UpcastModeValues };

export const SYSTEM_OPTIONS = ["DND5E"] as const;
export const LEVEL_OPTIONS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] as const;
export const SCHOOL_OPTIONS = Object.values(SpellSchoolValues);
export const CASTING_TIME_TYPE_OPTIONS = Object.values(CastingTimeTypeValues);
export const TARGET_MODE_OPTIONS = Object.values(TargetModeValues);
export const RESOLUTION_TYPE_OPTIONS = Object.values(ResolutionTypeValues);
export const DAMAGE_TYPE_OPTIONS = Object.values(SpellDamageTypeValues);
export const SAVING_THROW_OPTIONS = Object.values(SpellSavingThrowValues);
export const SAVE_SUCCESS_OUTCOME_OPTIONS = Object.values(SaveSuccessOutcomeValues);
export const UPCAST_MODE_OPTIONS = Object.values(UpcastModeValues);
export const SOURCE_OPTIONS = Object.values(SpellSourceValues);
export const DURATION_OPTIONS = [
  "Instantaneous",
  "Until dispelled",
  "Special",
  "1 round",
  "6 rounds",
  "1 minute",
  "10 minutes",
  "1 hour",
  "8 hours",
  "24 hours",
  "7 days",
  "10 days",
  "30 days",
  "Permanent",
  "Concentration, up to 1 round",
  "Concentration, up to 1 minute",
  "Concentration, up to 10 minutes",
  "Concentration, up to 1 hour",
  "Concentration, up to 8 hours",
  "Concentration, up to 24 hours",
] as const;
export const CLASS_OPTIONS = [
  "Bard",
  "Cleric",
  "Druid",
  "Paladin",
  "Ranger",
  "Sorcerer",
  "Warlock",
  "Wizard",
] as const;
export const COMPONENT_OPTIONS = ["V", "S", "M"] as const;

export const SCHOOL_COLORS: Record<string, string> = {
  abjuration: "text-blue-300 border-blue-400/30 bg-blue-400/10",
  conjuration: "text-yellow-300 border-yellow-400/30 bg-yellow-400/10",
  divination: "text-cyan-300 border-cyan-400/30 bg-cyan-400/10",
  enchantment: "text-pink-300 border-pink-400/30 bg-pink-400/10",
  evocation: "text-red-300 border-red-400/30 bg-red-400/10",
  illusion: "text-purple-300 border-purple-400/30 bg-purple-400/10",
  necromancy: "text-green-300 border-green-400/30 bg-green-400/10",
  transmutation: "text-orange-300 border-orange-400/30 bg-orange-400/10",
};

export const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-violet-400/50 focus:outline-none";
export const panelClassName =
  "rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(14,17,31,0.92),rgba(3,7,18,0.98))] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)]";
