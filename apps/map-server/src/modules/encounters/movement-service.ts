import type { ControllerType } from "@limiarmap/shared-contracts";
import {
  findMovementPath,
  nextEncounterVersion,
  validateMovement,
  type GridState
} from "@limiarmap/tactical-engine";
import type { InMemoryEncounterRepository } from "./encounter-repository";
import { getTacticalActionRejectionReason } from "./action-authorization";

export class MovementService {
  constructor(private readonly repository: InMemoryEncounterRepository) {}

  previewMovement(
    sessionId: string,
    combatantId: string,
    destination: { x: number; y: number }
  ) {
    const encounter = this.repository.requireEncounter(sessionId);
    const token = encounter.tokens.find(
      (candidate) => candidate.combatantId === combatantId
    );
    if (!token) {
      return {
        accepted: false,
        rejectionReason: "unknown_combatant",
        encounter
      };
    }

    const gridState: GridState = {
      map: encounter.battleMap,
      obstacles: encounter.obstacles,
      edgeObstacles: encounter.edgeObstacles,
      tokens: encounter.tokens
    };
    const preview = findMovementPath(
      gridState,
      token,
      destination,
      encounter.combatState
    );

    return {
      accepted: preview.accepted,
      rejectionReason: preview.rejectionReason,
      tokenId: token.id,
      combatantId,
      source: token.position,
      destination,
      path: preview.path,
      pathCostUnits: preview.pathCostUnits,
      movementBudget: token.movementBudget,
      movementSpeedCells: token.movementSpeedCells,
      remainingBudget: Math.max(
        0,
        token.movementBudget - preview.pathCostUnits
      ),
      encounter
    };
  }

  moveCombatant(
    sessionId: string,
    combatantId: string,
    destination: { x: number; y: number },
    actionId: string
  ) {
    const preview = this.previewMovement(sessionId, combatantId, destination);
    if (!preview.accepted) {
      return preview;
    }
    if (!preview.tokenId) {
      return {
        ...preview,
        accepted: false,
        rejectionReason: "unknown_token"
      };
    }

    const result = this.moveToken(
      sessionId,
      preview.tokenId,
      "limiarControl",
      "gm",
      preview.path,
      actionId
    );
    return {
      ...preview,
      ...result,
      source: preview.source,
      destination: preview.destination,
      path: preview.path,
      movementSpeedCells: preview.movementSpeedCells
    };
  }

  placeToken(
    sessionId: string,
    tokenId: string,
    position: { x: number; y: number },
    actionId: string
  ) {
    const encounter = this.repository.requireEncounter(sessionId);

    if (encounter.actionTracker.has(actionId)) {
      return {
        accepted: false,
        rejectionReason: "duplicate_action",
        encounter
      };
    }

    const token = encounter.tokens.find((t) => t.id === tokenId);
    if (!token) {
      return { accepted: false, rejectionReason: "unknown_token", encounter };
    }
    if (
      position.x < 0 ||
      position.y < 0 ||
      position.x >= encounter.battleMap.gridWidth ||
      position.y >= encounter.battleMap.gridHeight
    ) {
      return {
        accepted: false,
        rejectionReason: "invalid_destination",
        encounter,
        tokenId
      };
    }
    const blockedByObstacle = encounter.obstacles.some(
      (obstacle) =>
        obstacle.blocksMovement &&
        obstacle.cells.some(
          (cell) => cell.x === position.x && cell.y === position.y
        )
    );
    if (blockedByObstacle) {
      return {
        accepted: false,
        rejectionReason: "movement_blocked",
        encounter,
        tokenId
      };
    }
    const occupiedByOtherToken = encounter.tokens.some(
      (candidate) =>
        candidate.id !== tokenId &&
        candidate.position.x === position.x &&
        candidate.position.y === position.y
    );
    if (occupiedByOtherToken) {
      return {
        accepted: false,
        rejectionReason: "destination_occupied",
        encounter,
        tokenId
      };
    }

    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };
    this.repository.updateTokenMovement(
      sessionId,
      tokenId,
      position,
      token.movementBudget
    );

    return {
      accepted: true as const,
      tokenId,
      position,
      remainingBudget: token.movementBudget,
      encounter: this.repository.requireEncounter(sessionId)
    };
  }

  moveToken(
    sessionId: string,
    tokenId: string,
    actorId: string,
    actorType: ControllerType,
    path: Array<{ x: number; y: number }>,
    actionId: string
  ) {
    const encounter = this.repository.requireEncounter(sessionId);
    if (encounter.actionTracker.has(actionId)) {
      return {
        accepted: false,
        rejectionReason: "duplicate_action",
        encounter
      };
    }

    const token = encounter.tokens.find(
      (candidate) => candidate.id === tokenId
    );
    if (!token) {
      return {
        accepted: false,
        rejectionReason: "unknown_token",
        encounter,
        tokenId
      };
    }

    const tacticalActionRejectionReason = getTacticalActionRejectionReason(
      actorId,
      actorType,
      token,
      encounter.combatState
    );
    if (tacticalActionRejectionReason) {
      return {
        accepted: false,
        rejectionReason: tacticalActionRejectionReason,
        encounter,
        tokenId: token.id,
        movementBudget: token.movementBudget
      };
    }

    const gridState: GridState = {
      map: encounter.battleMap,
      obstacles: encounter.obstacles,
      edgeObstacles: encounter.edgeObstacles,
      tokens: encounter.tokens
    };
    const validation = validateMovement(
      gridState,
      token,
      path,
      encounter.combatState
    );
    if (!validation.accepted) {
      return {
        accepted: false,
        rejectionReason: validation.rejectionReason,
        encounter,
        tokenId: token.id,
        pathCostUnits: validation.pathCostUnits,
        movementBudget: token.movementBudget,
        exceededBy:
          validation.rejectionReason === "movement_budget_exceeded"
            ? Math.max(0, validation.pathCostUnits - token.movementBudget)
            : undefined
      };
    }

    const remainingBudget = token.movementBudget - validation.pathCostUnits;
    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };
    this.repository.updateTokenMovement(
      sessionId,
      tokenId,
      path[path.length - 1] ?? token.position,
      remainingBudget
    );

    return {
      accepted: true,
      pathCostUnits: validation.pathCostUnits,
      remainingBudget,
      encounter: this.repository.requireEncounter(sessionId)
    };
  }
}
