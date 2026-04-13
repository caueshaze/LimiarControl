import { describe, expect, it } from "vitest";
import { encounterSnapshotResponseSchema } from "@limiarmap/shared-contracts";
import { InMemoryEncounterRepository } from "../../src/modules/encounters/encounter-repository";
import { GridCalibrationService } from "../../src/modules/encounters/grid-calibration-service";
import { toEncounterSnapshot } from "../../src/modules/encounters/encounter-snapshot";

describe("grid calibration integration", () => {
  it("allows the GM to save a valid grid calibration", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new GridCalibrationService(repository);

    const result = service.updateGridCalibration(
      "demo-session",
      "gm",
      { x: 0.08, y: 0.12, width: 0.84, height: 0.76 },
      72,
      50,
      "grid-action-1"
    );

    expect(result.accepted).toBe(true);
    expect(result.encounter.battleMap.gridCalibration).toEqual({
      x: 0.08,
      y: 0.12,
      width: 0.84,
      height: 0.76
    });
    expect(result.encounter.battleMap.gridWidth).toBe(72);
    expect(result.encounter.battleMap.gridHeight).toBe(50);
    expect(result.encounter.combatState.version).toBe(2);
  });

  it("rejects grid calibration updates from non-GM actors", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new GridCalibrationService(repository);

    const result = service.updateGridCalibration(
      "demo-session",
      "player",
      { x: 0.1, y: 0.1, width: 0.8, height: 0.8 },
      72,
      50,
      "grid-action-2"
    );

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("not_gm");
    expect(result.encounter.battleMap.gridCalibration).toEqual({
      x: 0,
      y: 0,
      width: 1,
      height: 1
    });
  });

  it("rejects calibration values that exceed image bounds", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new GridCalibrationService(repository);

    const result = service.updateGridCalibration(
      "demo-session",
      "gm",
      { x: 0.3, y: 0.2, width: 0.8, height: 0.9 },
      72,
      50,
      "grid-action-3"
    );

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("invalid_grid_calibration");
  });

  it("rejects grid dimensions that would exclude existing content", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new GridCalibrationService(repository);

    const result = service.updateGridCalibration(
      "demo-session",
      "gm",
      { x: 0.02, y: 0.05, width: 0.95, height: 0.9 },
      9,
      9,
      "grid-action-4"
    );

    expect(result.accepted).toBe(false);
    expect(result.rejectionReason).toBe("grid_dimensions_too_small");
  });

  it("returns the saved calibration in the authoritative snapshot", () => {
    const repository = new InMemoryEncounterRepository();
    const service = new GridCalibrationService(repository);

    service.updateGridCalibration(
      "demo-session",
      "gm",
      { x: 0.02, y: 0.05, width: 0.95, height: 0.9 },
      84,
      58,
      "grid-action-5"
    );

    const snapshot = toEncounterSnapshot(repository.requireEncounter("demo-session"));
    expect(snapshot.battleMap.gridCalibration).toEqual({
      x: 0.02,
      y: 0.05,
      width: 0.95,
      height: 0.9
    });
    expect(snapshot.battleMap.gridWidth).toBe(84);
    expect(snapshot.battleMap.gridHeight).toBe(58);
    expect(() => encounterSnapshotResponseSchema.parse(snapshot)).not.toThrow();
  });
});
