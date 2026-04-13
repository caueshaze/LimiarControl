import { describe, expect, it } from "vitest";
import { movementRequestSchema, movementAppliedEventSchema, actionRejectedEventSchema } from "@limiarmap/shared-contracts";

describe("movement contract", () => {
  it("accepts movement request payloads", () => {
    expect(() =>
      movementRequestSchema.parse({
        actionId: "a",
        sessionId: "s",
        tokenId: "t",
        path: [{ x: 1, y: 1 }],
        knownVersion: 1
      })
    ).not.toThrow();
  });

  it("accepts movement and rejection events", () => {
    expect(() =>
      movementAppliedEventSchema.parse({
        eventId: "e",
        eventType: "movement.applied",
        encounterId: "s",
        version: 2,
        actionId: "a",
        payload: { tokenId: "t", position: { x: 1, y: 1 }, pathCostUnits: 5, remainingBudget: 25 },
        replaySafe: true
      })
    ).not.toThrow();

    expect(() =>
      actionRejectedEventSchema.parse({
        eventId: "e2",
        eventType: "action.rejected",
        encounterId: "s",
        version: 2,
        actionId: "a",
        payload: {
          reason: "movement_budget_exceeded",
          message: "Rejected",
          tokenId: "t",
          pathCostUnits: 35,
          movementBudget: 30,
          exceededBy: 5
        },
        replaySafe: true
      })
    ).not.toThrow();
  });
});
