import { describe, expect, it } from "vitest";
import { INITIAL_SHEET } from "../../character-sheet/model/initialSheet";
import { buildDragonWingsAction } from "./dragonWings";

const wingsSheet = (overrides: Record<string, unknown> = {}) => ({
  ...INITIAL_SHEET,
  class: "sorcerer",
  subclass: "draconic_bloodline",
  level: 14,
  speedMeters: 9,
  subclassConfig: { draconicAncestry: "red" },
  ...overrides,
});

describe("buildDragonWingsAction", () => {
  it("returns the action for a level-14 draconic sorcerer", () => {
    const action = buildDragonWingsAction(wingsSheet());
    expect(action).not.toBeNull();
    expect(action?.active).toBe(false);
    expect(action?.flySpeedMeters).toBe(0);
  });

  it("reports fly speed equal to walk speed when active", () => {
    const action = buildDragonWingsAction(wingsSheet({ dragonWings: { active: true } }));
    expect(action?.active).toBe(true);
    expect(action?.flySpeedMeters).toBe(9);
  });

  it("returns null below level 14", () => {
    expect(buildDragonWingsAction(wingsSheet({ level: 13 }))).toBeNull();
  });

  it("returns null for non-draconic characters", () => {
    expect(
      buildDragonWingsAction({ ...INITIAL_SHEET, class: "fighter", subclass: null, level: 20 }),
    ).toBeNull();
  });
});
