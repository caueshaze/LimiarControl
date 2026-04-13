import { describe, expect, it } from "vitest";
import { integrationSpatialEventEnvelopeSchema } from "@limiarmap/shared-contracts";

describe("integration realtime contract", () => {
  it("accepts the authoritative spatial event envelope used for Centrifugo publication", () => {
    expect(() =>
      integrationSpatialEventEnvelopeSchema.parse({
        eventId: "evt-1",
        eventType: "tokens.synced",
        encounterId: "session-123",
        version: 7,
        actionId: "control-combat-start:combat-123",
        payload: {
          tokens: []
        },
        replaySafe: true
      })
    ).not.toThrow();
  });
});
