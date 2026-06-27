import { describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import { useCharacterSheetDerived } from "./useCharacterSheetDerived";

describe("useCharacterSheetDerived", () => {
  it("exposes dragonborn ancestry damage, resistance and breath weapon data", () => {
    const derived = useCharacterSheetDerived({
      ...INITIAL_SHEET,
      race: "dragonborn",
      raceConfig: {
        draconicAncestry: "red",
      },
    });

    expect(derived.dragonbornAncestry).toBe("red");
    expect(derived.dragonbornAncestryLabel).toBe("Vermelho");
    expect(derived.dragonbornDamageType).toBe("fire");
    expect(derived.dragonbornResistanceType).toBe("fire");
    expect(derived.dragonbornBreathWeaponShape).toBe("cone");
    expect(derived.dragonbornBreathWeaponSaveType).toBe("constitution");
    expect(derived.resistances).toEqual(["fire"]);
  });

  it("exposes draconic ancestry damage and resistance for Draconic Bloodline", () => {
    const derived = useCharacterSheetDerived({
      ...INITIAL_SHEET,
      class: "sorcerer",
      subclass: "draconic_bloodline",
      level: 6,
      abilities: {
        ...INITIAL_SHEET.abilities,
        charisma: 18,
      },
      subclassConfig: {
        draconicAncestry: "blue",
      },
    });

    expect(derived.draconicAncestry).toBe("blue");
    expect(derived.draconicAncestryLabel).toBe("Azul");
    expect(derived.draconicDamageType).toBe("lightning");
    expect(derived.draconicResistanceType).toBe("lightning");
    expect(derived.hasElementalAffinity).toBe(true);
    expect(derived.elementalAffinityDamageType).toBe("lightning");
    expect(derived.elementalAffinityBonus).toBe(4);
    // Elemental Affinity resistance is activation-gated, not permanent, so it
    // is not listed among the passive sheet resistances.
    expect(derived.resistances).toEqual([]);
  });

  it("does not expose draconic lineage data for other subclasses", () => {
    const derived = useCharacterSheetDerived({
      ...INITIAL_SHEET,
      class: "sorcerer",
      subclass: "wild_magic",
      subclassConfig: {
        draconicAncestry: "red",
      },
    });

    expect(derived.draconicAncestry).toBeNull();
    expect(derived.draconicAncestryLabel).toBeNull();
    expect(derived.draconicDamageType).toBeNull();
    expect(derived.draconicResistanceType).toBeNull();
    expect(derived.hasElementalAffinity).toBe(false);
    expect(derived.resistances).toEqual([]);
  });

  it("exposes effectiveSpeedMeters as base speed with no active effects", () => {
    const derived = useCharacterSheetDerived({
      ...INITIAL_SHEET,
      speedMeters: 9,
    });
    expect(derived.effectiveSpeedMeters).toBe(9);
    expect(derived.movementSpeedBonus).toBeUndefined();
  });

  it("exposes effectiveSpeedMeters with movement speed bonus from active effects", () => {
    const activeEffects = [
      {
        id: "eff-1",
        kind: "spell_effect" as const,
        duration_type: "until_long_rest" as const,
        created_at: "2026-05-01T00:00:00Z",
        display_label: "Passos Longos",
        metadata: {
          source_spell_name: "Passos Longos",
          declarative_effect_group_id: "g1",
          declarative_effect: {
            type: "modify_movement_speed",
            params: { bonus_meters: 3 },
          },
        },
      },
    ];
    const derived = useCharacterSheetDerived(
      { ...INITIAL_SHEET, speedMeters: 9 },
      activeEffects,
    );
    expect(derived.effectiveSpeedMeters).toBe(12);
    expect(derived.movementSpeedBonus).toBe(3);
    expect(derived.movementSpeedBonusSources).toHaveLength(1);
    expect(derived.movementSpeedBonusSources![0].label).toBe("Passos Longos");
  });

  it("clamps effective speed to 0 with large negative bonus", () => {
    const activeEffects = [
      {
        id: "eff-neg",
        kind: "spell_effect" as const,
        duration_type: "until_long_rest" as const,
        created_at: "2026-05-01T00:00:00Z",
        metadata: {
          source_spell_name: "Slow",
          declarative_effect: {
            type: "modify_movement_speed",
            params: { bonus_meters: -15 },
          },
        },
      },
    ];
    const derived = useCharacterSheetDerived(
      { ...INITIAL_SHEET, speedMeters: 3 },
      activeEffects,
    );
    expect(derived.effectiveSpeedMeters).toBe(0);
  });

  it("does not crash with empty active effects array", () => {
    const derived = useCharacterSheetDerived(
      { ...INITIAL_SHEET, speedMeters: 9 },
      [],
    );
    expect(derived.effectiveSpeedMeters).toBe(9);
    expect(derived.movementSpeedBonus).toBeUndefined();
    expect(derived.movementSpeedBonusSources).toBeUndefined();
  });

  it("shows base speed equal to sheet speedMeters when no bonus", () => {
    const derived = useCharacterSheetDerived({
      ...INITIAL_SHEET,
      speedMeters: 11,
    });
    expect(derived.effectiveSpeedMeters).toBe(11);
    expect(derived.effectiveSpeedMeters).toBe(11);
  });
});
