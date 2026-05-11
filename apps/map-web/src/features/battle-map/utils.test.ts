import { describe, expect, it } from "vitest";
import type { Token } from "@limiarmap/shared-contracts";
import { findTokenAtCell, tokenOccupiesCell } from "./utils";

function token(overrides: Partial<Token> = {}): Token {
  return {
    id: "t1",
    battleMapId: "m",
    label: "Hero",
    kind: "playerCharacter",
    controllerType: "player",
    controllerId: "p1",
    position: { x: 3, y: 3 },
    movementSpeedCells: 6,
    movementBudget: 30,
    conditions: [],
    ...overrides,
  };
}

describe("tokenOccupiesCell", () => {
  it("stops matching extra cells after temporary footprint is removed", () => {
    const enlarged = token({
      base_size: "Medium",
      effective_size: "Large",
      effective_footprint: { width: 2, height: 2 },
    });
    const reverted = token({ base_size: "Medium" });

    expect(tokenOccupiesCell(enlarged, { x: 4, y: 4 })).toBe(true);
    expect(tokenOccupiesCell(reverted, { x: 4, y: 4 })).toBe(false);
  });
});

describe("findTokenAtCell", () => {
  it("does not select a reverted token from a former extra footprint cell", () => {
    const enlarged = token({
      id: "hero",
      base_size: "Medium",
      effective_size: "Large",
      effective_footprint: { width: 2, height: 2 },
    });
    const reverted = token({ id: "hero", base_size: "Medium" });

    expect(findTokenAtCell([enlarged], { x: 4, y: 4 })?.id).toBe("hero");
    expect(findTokenAtCell([reverted], { x: 4, y: 4 })).toBeUndefined();
  });
});
