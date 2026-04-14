import { describe, expect, it } from "vitest";
import {
  areaTargetRequestSchema,
  areaTargetResponseSchema,
  singleTargetResponseSchema,
  targetingSubmitSchema,
  targetingResolvedEventSchema
} from "@limiarmap/shared-contracts";

describe("targeting contract", () => {
  it("accepts targeting submit payloads", () => {
    expect(() =>
      targetingSubmitSchema.parse({
        actionId: "a",
        sessionId: "s",
        tokenId: "t",
        shape: "cone",
        originCell: { x: 1, y: 1 },
        anchorCell: { x: 2, y: 1 },
        rangeCells: 6,
        sizeCells: 3,
        knownVersion: 1,
        requiresSight: true,
        requiresEffect: true
      })
    ).not.toThrow();
  });

  it("accepts targeting resolved events", () => {
    expect(() =>
      targetingResolvedEventSchema.parse({
        eventId: "e",
        eventType: "targeting.resolved",
        encounterId: "s",
        version: 2,
        actionId: "a",
        payload: {
          tokenId: "t",
          shape: "cone",
          affectedCells: [{ x: 2, y: 1 }]
        },
        replaySafe: true
      })
    ).not.toThrow();
  });

  it("accepts area targeting integration payloads", () => {
    expect(() =>
      areaTargetRequestSchema.parse({
        actionId: "area-1",
        combatantId: "cmb_1",
        shape: "sphere",
        originCell: { x: 4, y: 4 },
        anchorCell: { x: 10, y: 10 },
        rangeCells: 45,
        sizeCells: 6,
        requiresEffect: true
      })
    ).not.toThrow();
  });

  it("accepts area targeting integration responses", () => {
    expect(() =>
      areaTargetResponseSchema.parse({
        isValid: true,
        reason: null,
        sessionId: "demo-session",
        actionId: "area-1",
        version: 3,
        shape: "sphere",
        sourceTokenId: "tok_player",
        affectedCells: [{ x: 10, y: 10 }],
        affectedTokenIds: ["tok_enemy"],
        affectedCombatantIds: ["cmb_2"]
      })
    ).not.toThrow();
  });

  it("accepts single-target integration responses with distanceCells", () => {
    expect(() =>
      singleTargetResponseSchema.parse({
        isValid: false,
        reason: "out_of_range",
        sessionId: "demo-session",
        actionId: "target-1",
        version: 3,
        sourceTokenId: "tok_player",
        targetTokenId: "tok_enemy",
        distanceCells: 7,
        cover: "none"
      })
    ).not.toThrow();
  });
});
