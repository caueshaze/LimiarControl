import type { AbilityName } from "../model/characterSheet.types";

export type GuidedPresetFeatureEntry = {
  id: string;
  requiresSubclass?: string;
};

export type GuidedPresetFeatureStep = {
  level: number;
  features: GuidedPresetFeatureEntry[];
};

export type GuidedPresetAsiBonus = {
  ability: AbilityName;
  bonus: number;
  level: number;
};

export type GuidedPresetConfig = {
  /**
   * Guided preset classes can be mostly configured through data, as long as
   * their referenced features already exist in FEATURE_REGISTRY and any
   * required spell source mappings are defined elsewhere.
   */
  fixedSubclass: { id: string; level: number } | null;
  fixedFightingStyle: { id: string; level: number } | null;
  fixedAsiBonuses: GuidedPresetAsiBonus[] | null;
  featureProgression: GuidedPresetFeatureStep[];
};

export const normalizeClassId = (value: string | null | undefined) =>
  String(value ?? "")
    .trim()
    .toLowerCase();

export const GUIDED_PRESETS: Record<string, GuidedPresetConfig> = {
  guardian: {
    fixedSubclass: { id: "hunter", level: 3 },
    fixedFightingStyle: { id: "archery", level: 2 },
    fixedAsiBonuses: [{ ability: "dexterity", bonus: 2, level: 4 }],
    featureProgression: [
      {
        level: 1,
        features: [
          { id: "favored_enemy_beasts" },
          { id: "natural_explorer_forest" },
        ],
      },
      {
        level: 2,
        features: [
          { id: "fighting_style_archery" },
          { id: "spellcasting_guardian" },
        ],
      },
      {
        level: 3,
        features: [
          { id: "primeval_awareness" },
          { id: "subclass_hunter", requiresSubclass: "hunter" },
          { id: "hunter_colossus_slayer", requiresSubclass: "hunter" },
        ],
      },
      {
        level: 4,
        features: [{ id: "asi_guardian_dexterity_2" }],
      },
    ],
  },
};

export const isGuidedPreset = (classId: string): boolean =>
  normalizeClassId(classId) in GUIDED_PRESETS;

export const getGuidedPreset = (classId: string): GuidedPresetConfig | undefined =>
  GUIDED_PRESETS[normalizeClassId(classId)];
