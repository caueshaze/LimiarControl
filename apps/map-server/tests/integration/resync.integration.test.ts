import { describe, expect, it } from "vitest";
import { encounterSnapshotResponseSchema } from "@limiarmap/shared-contracts";
import { InMemoryEncounterRepository } from "../../src/modules/encounters/encounter-repository";
import { toEncounterSnapshot } from "../../src/modules/encounters/encounter-snapshot";

describe("resync integration", () => {
  it("returns the latest authoritative snapshot", () => {
    const repository = new InMemoryEncounterRepository();
    const encounter = repository.requireEncounter("demo-session");
    const snapshot = toEncounterSnapshot(encounter);
    expect(snapshot.combatState.version).toBeGreaterThan(0);
    expect(snapshot.battleMap.gridCalibration).toEqual({
      x: 0,
      y: 0,
      width: 1,
      height: 1
    });
    expect(() => encounterSnapshotResponseSchema.parse(snapshot)).not.toThrow();
  });
});
