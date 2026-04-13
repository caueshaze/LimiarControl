import type { ControllerType } from "@limiarmap/shared-contracts";
import {
  nextEncounterVersion,
  validateMovement,
  type GridState
} from "@limiarmap/tactical-engine";
import type { InMemoryEncounterRepository } from "./encounter-repository";
import { getTacticalActionRejectionReason } from "./action-authorization";

export class MovementService {
  constructor(private readonly repository: InMemoryEncounterRepository) {}

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
      return { accepted: false, rejectionReason: "duplicate_action", encounter };
    }

    const token = encounter.tokens.find((candidate) => candidate.id === tokenId);
    if (!token) {
      return { accepted: false, rejectionReason: "unknown_token", encounter, tokenId };
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
    const validation = validateMovement(gridState, token, path, encounter.combatState);
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
