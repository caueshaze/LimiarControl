import { describe, expect, it } from "vitest";

import {
  DRACONIC_ANCESTRY_DAMAGE_TYPES,
  getDraconicLineageState,
  getDraconicAncestryLabel,
  getDraconicDamageType,
  getDraconicResistanceType,
  normalizeSubclassConfig,
  resolveElementalAffinityEligibility,
} from "./draconicAncestry";
import { formatClassDisplayName } from "./classes";

describe("draconicAncestry", () => {
  it("maps ancestry to the expected damage type", () => {
    Object.entries(DRACONIC_ANCESTRY_DAMAGE_TYPES).forEach(([ancestry, damageType]) => {
      expect(getDraconicDamageType(ancestry)).toBe(damageType);
    });
  });

  it("maps ancestry to the expected resistance type and label", () => {
    expect(getDraconicResistanceType("green")).toBe("poison");
    expect(getDraconicResistanceType("silver")).toBe("cold");
    expect(getDraconicAncestryLabel("gold")).toBe("Ouro");
  });

  it("normalizes legacy dragonAncestor into draconicAncestry", () => {
    expect(
      normalizeSubclassConfig("draconic_bloodline", {
        dragonAncestor: "gold",
      }),
    ).toEqual({ draconicAncestry: "gold" });
  });

  it("keeps the canonical draconicAncestry key unchanged when already normalized", () => {
    expect(
      normalizeSubclassConfig("draconic_bloodline", {
        draconicAncestry: "blue",
      }),
    ).toEqual({ draconicAncestry: "blue" });
  });

  it("drops draconic ancestry config for non-draconic origins", () => {
    expect(
      normalizeSubclassConfig("wild_magic", {
        draconicAncestry: "red",
      }),
    ).toBeNull();
  });

  it("formats Draconic Bloodline display names with the chosen ancestry", () => {
    expect(
      formatClassDisplayName("sorcerer", "draconic_bloodline", {
        draconicAncestry: "red",
      }),
    ).toBe("Feiticeiro - Linhagem Dracônica (Vermelho)");
  });

  it("derives elemental affinity and resistance from lineage state at level 6", () => {
    const lineage = getDraconicLineageState({
      classId: "sorcerer",
      subclass: "draconic_bloodline",
      level: 6,
      subclassConfig: { draconicAncestry: "silver" },
    });

    expect(lineage.damageType).toBe("cold");
    expect(lineage.resistanceType).toBe("cold");
    expect(lineage.resistances).toEqual(["cold"]);
    expect(lineage.hasElementalAffinity).toBe(true);
  });

  it("marks spells with matching damage type as eligible for Elemental Affinity", () => {
    expect(
      resolveElementalAffinityEligibility({
        classId: "sorcerer",
        subclass: "draconic_bloodline",
        level: 6,
        subclassConfig: { draconicAncestry: "red" },
        spellDamageType: "fire",
        charismaScore: 18,
      }),
    ).toEqual({
      eligible: true,
      damageType: "fire",
      bonus: 4,
    });
  });
});
