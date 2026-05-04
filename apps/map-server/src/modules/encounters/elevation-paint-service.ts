import type {
  CellElevation,
  ControllerType,
  Coordinate
} from "@limiarmap/shared-contracts";
import {
  chebyshevDistance,
  coordinateKey,
  isInsideMap,
  nextEncounterVersion
} from "@limiarmap/tactical-engine";
import type { InMemoryEncounterRepository } from "./encounter-repository";

function buildCircleCells(
  centerCell: Coordinate,
  radius: number,
  map: ReturnType<InMemoryEncounterRepository["requireEncounter"]>["battleMap"]
): Coordinate[] {
  const cells: Coordinate[] = [];

  for (let x = centerCell.x - radius; x <= centerCell.x + radius; x += 1) {
    for (let y = centerCell.y - radius; y <= centerCell.y + radius; y += 1) {
      const coordinate = { x, y };
      if (
        chebyshevDistance(centerCell, coordinate) > radius ||
        !isInsideMap({ map, obstacles: [], edgeObstacles: [], tokens: [] }, coordinate)
      ) {
        continue;
      }

      cells.push(coordinate);
    }
  }

  return cells;
}

export class ElevationPaintService {
  constructor(private readonly repository: InMemoryEncounterRepository) {}

  paintElevation(
    sessionId: string,
    actorType: ControllerType,
    centerCell: Coordinate,
    radius: number,
    mode: "paint" | "erase",
    elevationMeters: number | undefined,
    actionId: string
  ) {
    const encounter = this.repository.requireEncounter(sessionId);
    if (encounter.actionTracker.has(actionId)) {
      return { accepted: false, rejectionReason: "duplicate_action", encounter };
    }

    if (actorType !== "gm") {
      return { accepted: false, rejectionReason: "not_gm", encounter };
    }

    if ((mode !== "paint" && mode !== "erase") || !Number.isInteger(radius) || radius < 0 || radius > 12) {
      return { accepted: false, rejectionReason: "invalid_elevation_brush", encounter };
    }

    if (!isInsideMap({ map: encounter.battleMap, obstacles: [], edgeObstacles: [], tokens: [] }, centerCell)) {
      return { accepted: false, rejectionReason: "outside_map", encounter };
    }

    const targetCells = buildCircleCells(centerCell, radius, encounter.battleMap);
    if (targetCells.length === 0) {
      return { accepted: false, rejectionReason: "invalid_elevation_brush", encounter };
    }

    const targetKeys = new Set(targetCells.map((cell) => coordinateKey(cell)));

    let nextElevations: CellElevation[];

    if (mode === "paint" && elevationMeters !== undefined && elevationMeters > 0) {
      // Merge: keep existing entries not in target, add/update target entries
      const existing = encounter.cellElevations.filter(
        (e) => !targetKeys.has(coordinateKey(e.cell))
      );
      const painted = targetCells.map((cell) => ({
        cell,
        elevationMeters,
      }));
      nextElevations = [...existing, ...painted];
    } else {
      // Erase (or paint with 0): remove elevation from target cells
      nextElevations = encounter.cellElevations.filter(
        (e) => !targetKeys.has(coordinateKey(e.cell))
      );
    }

    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };

    this.repository.setCellElevations(sessionId, nextElevations);
    this.repository.updateCombatState(sessionId, encounter.combatState);

    return {
      accepted: true,
      encounter: this.repository.requireEncounter(sessionId)
    };
  }
}
