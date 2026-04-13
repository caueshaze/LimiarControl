import { describe, expect, it } from "vitest";
import {
  encounterSnapshotResponseSchema,
  gridCalibrationRequestSchema,
  gridCalibrationUpdatedEventSchema
} from "@limiarmap/shared-contracts";

describe("grid calibration contract", () => {
  it("accepts grid calibration requests", () => {
    expect(() =>
      gridCalibrationRequestSchema.parse({
        actionId: "grid-1",
        sessionId: "demo-session",
        knownVersion: 1,
        gridCalibration: {
          x: 0.1,
          y: 0.15,
          width: 0.8,
          height: 0.7
        },
        gridWidth: 72,
        gridHeight: 49
      })
    ).not.toThrow();
  });

  it("accepts grid calibration updated events", () => {
    expect(() =>
      gridCalibrationUpdatedEventSchema.parse({
        eventId: "grid-event-1",
        eventType: "grid.calibration.updated",
        encounterId: "demo-session",
        version: 2,
        actionId: "grid-1",
        payload: {
          battleMapId: "map_1",
          gridCalibration: {
            x: 0.1,
            y: 0.15,
            width: 0.8,
            height: 0.7
          },
          gridWidth: 72,
          gridHeight: 49
        },
        replaySafe: true
      })
    ).not.toThrow();
  });

  it("accepts encounter snapshots with grid calibration", () => {
    expect(() =>
      encounterSnapshotResponseSchema.parse({
        sessionId: "demo-session",
        battleMap: {
          id: "map_1",
          name: "Demo",
          gridWidth: 20,
          gridHeight: 14,
          terrainVersion: 1,
          gridCalibration: {
            x: 0,
            y: 0,
            width: 1,
            height: 1
          },
          activeEncounterId: "enc_1"
        },
        combatState: {
          id: "combat_1",
          battleMapId: "map_1",
          status: "active",
          roundNumber: 1,
          turnIndex: 0,
          activeCombatantId: "cmb_1",
          initiativeOrder: ["cmb_1", "cmb_2"],
          advancedBy: "LimiarControl",
          version: 1
        },
        tokens: [],
        obstacles: []
      })
    ).not.toThrow();
  });
});
