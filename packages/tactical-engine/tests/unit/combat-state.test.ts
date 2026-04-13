import { describe, expect, it } from "vitest";
import { advanceCombat, canTokenAct } from "../../src";

describe("combat state", () => {
  it("advances to the next active combatant", () => {
    const next = advanceCombat({
      id: "combat",
      battleMapId: "map",
      status: "active",
      roundNumber: 1,
      turnIndex: 0,
      activeCombatantId: "a",
      initiativeOrder: ["a", "b"],
      advancedBy: "LimiarControl",
      version: 1
    });

    expect(next.activeCombatantId).toBe("b");
    expect(next.version).toBe(2);
  });

  it("guards acting tokens by active turn", () => {
    expect(
      canTokenAct(
        {
          id: "combat",
          battleMapId: "map",
          status: "active",
          roundNumber: 1,
          turnIndex: 0,
          activeCombatantId: "a",
          initiativeOrder: ["a", "b"],
          advancedBy: "LimiarControl",
          version: 1
        },
        "b"
      )
    ).toBe(false);
  });
});
