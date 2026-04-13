import { describe, expect, it } from "vitest";
import type { RollResolvedActivityEvent } from "../../../shared/api/sessionsRepo";
import { formatResolvedRollBreakdown } from "./sessionActivityRowUtils";

const baseEvent: RollResolvedActivityEvent = {
  type: "roll_resolved",
  actorKind: "player",
  actorName: "Player",
  advantageMode: "normal",
  displayName: "Player",
  isGmRoll: false,
  modifierUsed: 3,
  rollType: "save",
  rolls: [8, 8],
  selectedRoll: 8,
  sessionOffsetSeconds: 10,
  timestamp: "2026-03-30T22:00:00Z",
  total: 11,
  userId: "player-1",
};

describe("sessionActivityRowUtils", () => {
  it("shows a single d20 value for normal resolved rolls", () => {
    expect(
      formatResolvedRollBreakdown(baseEvent, "d20:"),
    ).toBe("d20: 8 + 3");
  });

  it("shows both d20 values for advantage or disadvantage", () => {
    expect(
      formatResolvedRollBreakdown(
        {
          ...baseEvent,
          advantageMode: "advantage",
          rolls: [8, 14],
          selectedRoll: 14,
        },
        "d20:",
      ),
    ).toBe("d20: [8, 14] → 14 + 3");
  });
});
