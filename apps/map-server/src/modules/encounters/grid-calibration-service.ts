import type { ControllerType, GridCalibration } from "@limiarmap/shared-contracts";
import { gridCalibrationSchema, gridDimensionsSchema } from "@limiarmap/shared-contracts";
import { nextEncounterVersion } from "@limiarmap/tactical-engine";
import type { InMemoryEncounterRepository } from "./encounter-repository";

function getMinimumGridDimensions(encounter: ReturnType<InMemoryEncounterRepository["requireEncounter"]>) {
  let gridWidth = 1;
  let gridHeight = 1;

  encounter.tokens.forEach((token) => {
    gridWidth = Math.max(gridWidth, token.position.x + 1);
    gridHeight = Math.max(gridHeight, token.position.y + 1);
  });

  encounter.obstacles.forEach((obstacle) => {
    obstacle.cells.forEach((cell) => {
      gridWidth = Math.max(gridWidth, cell.x + 1);
      gridHeight = Math.max(gridHeight, cell.y + 1);
    });
  });

  return { gridWidth, gridHeight };
}

export class GridCalibrationService {
  constructor(private readonly repository: InMemoryEncounterRepository) {}

  updateGridCalibration(
    sessionId: string,
    actorType: ControllerType,
    gridCalibration: GridCalibration,
    gridWidth: number,
    gridHeight: number,
    actionId: string
  ) {
    const encounter = this.repository.requireEncounter(sessionId);
    if (encounter.actionTracker.has(actionId)) {
      return { accepted: false, rejectionReason: "duplicate_action", encounter };
    }

    if (actorType !== "gm") {
      return { accepted: false, rejectionReason: "not_gm", encounter };
    }

    const validation = gridCalibrationSchema.safeParse(gridCalibration);
    if (!validation.success) {
      return { accepted: false, rejectionReason: "invalid_grid_calibration", encounter };
    }

    const dimensionValidation = gridDimensionsSchema.safeParse({ gridWidth, gridHeight });
    if (!dimensionValidation.success) {
      return { accepted: false, rejectionReason: "invalid_grid_dimensions", encounter };
    }

    const minimumGridDimensions = getMinimumGridDimensions(encounter);
    if (
      dimensionValidation.data.gridWidth < minimumGridDimensions.gridWidth ||
      dimensionValidation.data.gridHeight < minimumGridDimensions.gridHeight
    ) {
      return {
        accepted: false,
        rejectionReason: "grid_dimensions_too_small",
        encounter
      };
    }

    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };

    this.repository.updateBattleMapGridCalibration(
      sessionId,
      validation.data,
      dimensionValidation.data.gridWidth,
      dimensionValidation.data.gridHeight
    );
    this.repository.updateCombatState(sessionId, encounter.combatState);

    return {
      accepted: true,
      encounter: this.repository.requireEncounter(sessionId)
    };
  }
}
