import { describe, expect, it } from "vitest";
import {
  obstaclePaintRequestSchema,
  obstaclesUpdatedEventSchema
} from "@limiarmap/shared-contracts";

describe("obstacle paint contract", () => {
  it("accepts obstacle paint requests", () => {
    expect(() =>
      obstaclePaintRequestSchema.parse({
        actionId: "obs-1",
        sessionId: "demo-session",
        knownVersion: 1,
        mode: "paint",
        centerCell: { x: 10, y: 10 },
        radius: 2,
        style: {
          blocksMovement: true,
          blocksEffect: false,
          blocksVision: false,
          cover: "none",
          clipsDiagonalMovement: true,
          movementCostMultiplier: 1
        }
      })
    ).not.toThrow();
  });

  it("accepts obstacle update events", () => {
    expect(() =>
      obstaclesUpdatedEventSchema.parse({
        eventId: "obs-event-1",
        eventType: "obstacles.updated",
        encounterId: "demo-session",
        version: 2,
        actionId: "obs-1",
        payload: {
          battleMapId: "map_1",
          obstacles: [
            {
              id: "obs:obs-1",
              battleMapId: "map_1",
              label: "Path bloqueado",
              cells: [{ x: 10, y: 10 }],
              blocksMovement: true,
              blocksEffect: false,
              blocksVision: false,
              cover: "none",
              clipsDiagonalMovement: true,
              movementCostMultiplier: 1
            }
          ]
        },
        replaySafe: true
      })
    ).not.toThrow();
  });

  it("keeps backward compatibility for legacy obstacle style payloads", () => {
    const parsed = obstaclePaintRequestSchema.parse({
      actionId: "obs-legacy",
      sessionId: "demo-session",
      knownVersion: 1,
      mode: "paint",
      centerCell: { x: 10, y: 10 },
      radius: 0,
      style: {
        blocksMovement: false,
        blocksTargeting: false,
        blocksSpell: true,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    });

    expect(parsed.style?.blocksEffect).toBe(true);
  });
});
