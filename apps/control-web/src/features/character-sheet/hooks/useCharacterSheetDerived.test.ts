import { describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../model/initialSheet";
import { useCharacterSheetDerived } from "./useCharacterSheetDerived";
import type { ActiveEffect } from "../../../shared/api/combatRepo";

const makePassivePerceptionEffect = (
  bonus: number,
  label = "Owl's Wisdom",
): ActiveEffect => ({
  id: `effect-${label}-${bonus}`,
  kind: "spell_effect",
  duration_type: "rounds",
  created_at: "2026-05-02T00:00:00Z",
  display_label: label,
  metadata: {
    declarative_effect: {
      type: "passive_skill_bonus",
      params: {
        skill: "perception",
        bonus,
      },
    },
  },
});

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

  it("adds passive perception bonus from active effects when present", () => {
    const derived = useCharacterSheetDerived(INITIAL_SHEET, [
      makePassivePerceptionEffect(5),
    ]);

    expect(derived.passivePerception).toBe(15);
    expect(derived.passivePerceptionBonus).toBe(5);
    expect(derived.passivePerceptionBonusSources).toEqual([
      { label: "Owl's Wisdom", value: 5 },
    ]);
  });

  it("stacks passive perception bonuses and preserves baseline without effects", () => {
    const baseline = useCharacterSheetDerived(INITIAL_SHEET);
    const derived = useCharacterSheetDerived(INITIAL_SHEET, [
      makePassivePerceptionEffect(3, "Aura of Vigilance"),
      makePassivePerceptionEffect(2, "Owl's Wisdom"),
    ]);

    expect(baseline.passivePerception).toBe(10);
    expect(baseline.passivePerceptionBonus).toBe(0);
    expect(baseline.passivePerceptionBonusSources).toEqual([]);
    expect(derived.passivePerception).toBe(15);
    expect(derived.passivePerceptionBonus).toBe(5);
    expect(derived.passivePerceptionBonusSources).toEqual([
      { label: "Aura of Vigilance", value: 3 },
      { label: "Owl's Wisdom", value: 2 },
    ]);
  });
});
