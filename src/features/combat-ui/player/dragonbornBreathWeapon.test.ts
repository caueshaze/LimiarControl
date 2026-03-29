import { describe, expect, it } from "vitest";

import { INITIAL_SHEET } from "../../character-sheet/model/initialSheet";
import { buildDragonbornBreathWeaponAction } from "./dragonbornBreathWeapon";

describe("dragonborn breath weapon combat helper", () => {
  it("returns null for characters without dragonborn ancestry", () => {
    expect(buildDragonbornBreathWeaponAction(INITIAL_SHEET)).toBeNull();
  });

  it("builds a combat action using lineage data and remaining uses", () => {
    const action = buildDragonbornBreathWeaponAction({
      ...INITIAL_SHEET,
      level: 7,
      race: "dragonborn",
      abilities: {
        ...INITIAL_SHEET.abilities,
        constitution: 16,
      },
      raceConfig: { draconicAncestry: "blue" },
      classResources: {
        dragonbornBreathWeapon: {
          usesMax: 1,
          usesRemaining: 0,
        },
      },
    });

    expect(action).toEqual({
      id: "dragonborn_breath_weapon",
      ancestry: "blue",
      ancestryLabel: "Azul",
      damageType: "lightning",
      saveAbility: "dexterity",
      damageDice: "3d6",
      dc: 14,
      usesMax: 1,
      usesRemaining: 0,
    });
  });
});

