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
    expect(derived.resistances).toEqual(["lightning"]);
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
});
