import { describe, expect, it } from "vitest";
import {
  combatAdvanceRequestSchema,
  combatAdvancedEventSchema,
  syncActiveAreaEffectsRequestSchema,
} from "@limiarmap/shared-contracts";

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

  it("accepts active area effect sync requests", () => {
    expect(() =>
      syncActiveAreaEffectsRequestSchema.parse({
        activeAreaEffects: [
          {
            id: "area_effect:1",
            sourceSpellCanonicalKey: "fog_cloud",
            sourceSpellName: "Fog Cloud",
            casterParticipantId: "p1",
            casterRefId: "player-123",
            originPoint: { x: 10, y: 10 },
            anchorCell: { x: 10, y: 10 },
            areaShape: "sphere",
            sizeMeters: 6,
            radiusMeters: 6,
            affectedCells: [{ x: 10, y: 10 }],
            effectKind: "obscurement",
            obscurement: "heavily_obscured",
          },
        ],
      })
    ).not.toThrow();
  });
});
