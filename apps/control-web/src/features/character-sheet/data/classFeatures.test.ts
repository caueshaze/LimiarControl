import { describe, expect, it } from "vitest";

import {
  buildClassFeatures,
  getClassLevelAbilityBonuses,
  getFixedFightingStyleForClassLevel,
  getFixedSubclassForClassLevel,
  validateGuidedPresetConfig,
} from "./classFeatures";
import type { GuidedPresetConfig } from "./guidedPresets";

describe("guided preset validation", () => {
  it("builds guardian guided preset progression and fixed milestones", () => {
    expect(getFixedFightingStyleForClassLevel("guardian", 1)).toBeNull();
    expect(getFixedFightingStyleForClassLevel("guardian", 2)).toBe("archery");
    expect(getFixedSubclassForClassLevel("guardian", 2)).toBeNull();
    expect(getFixedSubclassForClassLevel("guardian", 3)).toBe("hunter");
    expect(getClassLevelAbilityBonuses("guardian", 4).dexterity).toBe(2);
    expect(buildClassFeatures("guardian", 3, null).map((feature) => feature.id)).toEqual([
      "favored_enemy_beasts",
      "natural_explorer_forest",
      "fighting_style_archery",
      "spellcasting_guardian",
      "primeval_awareness",
      "subclass_hunter",
      "hunter_colossus_slayer",
    ]);
  });

  it("keeps ranger independent from guardian guided behavior", () => {
    expect(getFixedFightingStyleForClassLevel("ranger", 2)).toBeNull();
    expect(getFixedSubclassForClassLevel("ranger", 3)).toBeNull();
    expect(getClassLevelAbilityBonuses("ranger", 4).dexterity).toBe(0);
    expect(buildClassFeatures("ranger", 4, "hunter")).toEqual([]);
  });

  it("throws for unknown guided preset feature ids", () => {
    const preset: GuidedPresetConfig = {
      fixedSubclass: { id: "hunter", level: 3 },
      fixedFightingStyle: { id: "archery", level: 2 },
      fixedAsiBonuses: [{ ability: "dexterity", bonus: 2, level: 4 }],
      featureProgression: [{ level: 1, features: [{ id: "missing_feature_id" }] }],
    };

    expect(() => validateGuidedPresetConfig("guardian", preset)).toThrowError(
      'Guided preset "guardian" references unknown feature "missing_feature_id". Add it to FEATURE_REGISTRY or fix the preset config.'
    );
  });

  it("throws for invalid fixed ASI abilities", () => {
    const preset = {
      fixedSubclass: { id: "hunter", level: 3 },
      fixedFightingStyle: { id: "archery", level: 2 },
      fixedAsiBonuses: [{ ability: "luck", bonus: 2, level: 4 }],
      featureProgression: [{ level: 1, features: [{ id: "favored_enemy_beasts" }] }],
    } as unknown as GuidedPresetConfig;

    expect(() => validateGuidedPresetConfig("guardian", preset)).toThrowError(
      'Guided preset "guardian" has invalid fixedAsiBonuses[0].ability "luck".'
    );
  });

  it("throws for unknown mechanics families via class definition", () => {
    const preset: GuidedPresetConfig = {
      fixedSubclass: null,
      fixedFightingStyle: null,
      fixedAsiBonuses: null,
      featureProgression: [],
    };

    expect(() => validateGuidedPresetConfig("missing-guided-class", preset)).toThrowError(
      'Guided preset "missing-guided-class" references unknown class definition "missing-guided-class".'
    );
  });
});
