import { describe, expect, it } from "vitest";
import { combatAdvanceRequestSchema, combatAdvancedEventSchema } from "@limiarmap/shared-contracts";

describe("combat contract", () => {
  it("accepts combat advance requests", () => {
    expect(() =>
      combatAdvanceRequestSchema.parse({
        actionId: "a",
        sessionId: "s",
        knownVersion: 1,
        requestedBy: "limiarControl"
      })
    ).not.toThrow();
  });

  it("accepts combat advanced events", () => {
    expect(() =>
      combatAdvancedEventSchema.parse({
        eventId: "e",
        eventType: "combat.advanced",
        encounterId: "s",
        version: 2,
        actionId: "a",
        payload: { roundNumber: 2, turnIndex: 1, activeCombatantId: "cmb_2" },
        replaySafe: true
      })
    ).not.toThrow();
  });
});
