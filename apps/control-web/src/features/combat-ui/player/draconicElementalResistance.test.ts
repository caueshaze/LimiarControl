import { describe, expect, it } from "vitest";
import { INITIAL_SHEET } from "../../character-sheet/model/initialSheet";
import {
  buildDraconicElementalResistanceAction,
  resolveActiveElementalResistance,
} from "./draconicElementalResistance";
import type { ActiveEffect } from "../../../shared/api/combatRepo";

const draconicSheet = (overrides: Record<string, unknown> = {}) => ({
  ...INITIAL_SHEET,
  class: "sorcerer",
  subclass: "draconic_bloodline",
  level: 6,
  subclassConfig: { draconicAncestry: "red" },
  classResources: { sorceryPoints: { usesMax: 6, usesRemaining: 4 } },
  ...overrides,
});

describe("buildDraconicElementalResistanceAction", () => {
  it("returns the action with sorcery points for a level-6 draconic sorcerer", () => {
    const action = buildDraconicElementalResistanceAction(draconicSheet());
    expect(action).not.toBeNull();
    expect(action?.damageType).toBe("fire");
    expect(action?.sorceryPointsMax).toBe(6);
    expect(action?.sorceryPointsRemaining).toBe(4);
  });

  it("returns null below level 6 (no Elemental Affinity yet)", () => {
    expect(buildDraconicElementalResistanceAction(draconicSheet({ level: 5 }))).toBeNull();
  });

  it("returns null for a non-draconic character", () => {
    expect(
      buildDraconicElementalResistanceAction({
        ...INITIAL_SHEET,
        class: "fighter",
        subclass: "",
      }),
    ).toBeNull();
  });

  it("clamps remaining to zero when the pool is empty", () => {
    const action = buildDraconicElementalResistanceAction(
      draconicSheet({ classResources: { sorceryPoints: { usesMax: 6, usesRemaining: 0 } } }),
    );
    expect(action?.sorceryPointsRemaining).toBe(0);
  });
});

describe("resolveActiveElementalResistance", () => {
  const effect = {
    id: "ea-1",
    kind: "elemental_affinity_resistance",
    duration_type: "timed",
    damage_type: "fire",
    expires_at_game_time_seconds: 1060,
  } as unknown as ActiveEffect;

  it("computes seconds remaining against current game time", () => {
    const resolved = resolveActiveElementalResistance([effect], 1030);
    expect(resolved?.damageType).toBe("fire");
    expect(resolved?.secondsRemaining).toBe(30);
  });

  it("clamps remaining seconds to zero once expired", () => {
    const resolved = resolveActiveElementalResistance([effect], 9999);
    expect(resolved?.secondsRemaining).toBe(0);
  });

  it("returns null without an elemental resistance effect", () => {
    expect(resolveActiveElementalResistance([], 0)).toBeNull();
  });
});
