import type { ControllerType, Coordinate, TargetingTemplate } from "@limiarmap/shared-contracts";
import {
  chebyshevDistance,
  hasLineOfEffect,
  hasLineOfSight,
  nextEncounterVersion,
  resolveCone,
  resolveCube,
  resolveLine,
  resolveSphere,
  resolveCylinder
} from "@limiarmap/tactical-engine";
import { canSubmitTacticalAction } from "./action-authorization";
import type { InMemoryEncounterRepository } from "./encounter-repository";

export class TargetingService {
  constructor(private readonly repository: InMemoryEncounterRepository) {}

  resolveTargeting(
    sessionId: string,
    template: TargetingTemplate,
    actorId: string,
    actorType: ControllerType,
    options?: { requiresSight?: boolean; requiresEffect?: boolean }
  ) {
    const encounter = this.repository.requireEncounter(sessionId);
    if (encounter.actionTracker.has(template.actionId)) {
      return { accepted: false, rejectionReason: "duplicate_action", encounter };
    }

    const token = encounter.tokens.find((candidate) => candidate.id === template.tokenId);
    if (!token) {
      return { accepted: false, rejectionReason: "unknown_token", encounter };
    }

    if (!canSubmitTacticalAction(actorId, actorType, token, encounter.combatState)) {
      return { accepted: false, rejectionReason: "unauthorized_action", encounter };
    }

    if (chebyshevDistance(template.originCell, template.anchorCell) > template.rangeCells) {
      return { accepted: false, rejectionReason: "out_of_range", encounter };
    }

    const { obstacles, edgeObstacles } = encounter;

    if (options?.requiresSight && !hasLineOfSight(obstacles, template.originCell, template.anchorCell, edgeObstacles)) {
      return { accepted: false, rejectionReason: "no_line_of_sight", encounter };
    }

    if (options?.requiresEffect && !hasLineOfEffect(obstacles, template.originCell, template.anchorCell, edgeObstacles)) {
      return { accepted: false, rejectionReason: "no_line_of_effect", encounter };
    }

    // Phase 11: all shape resolvers now receive edgeObstacles so propagation
    // respects both cell obstacles and edge obstacles.
    let affectedCells: Coordinate[] = [];
    switch (template.shape) {
      case "line":
        affectedCells = resolveLine(
          template.originCell,
          template.anchorCell,
          template.rangeCells,
          obstacles,
          edgeObstacles
        );
        break;
      case "cone":
        affectedCells = resolveCone(
          template.originCell,
          template.anchorCell,
          template.sizeCells,
          obstacles,
          edgeObstacles
        );
        break;
      case "sphere":
        affectedCells = resolveSphere(template.anchorCell, template.sizeCells, obstacles, edgeObstacles);
        break;
      case "cylinder":
        affectedCells = resolveCylinder(template.anchorCell, template.sizeCells, obstacles, edgeObstacles);
        break;
      case "cube":
        affectedCells = resolveCube(template.anchorCell, template.sizeCells, obstacles, edgeObstacles);
        break;
    }

    encounter.actionTracker.record(template.actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };
    this.repository.updateCombatState(sessionId, encounter.combatState);

    return {
      accepted: true,
      affectedCells,
      encounter: this.repository.requireEncounter(sessionId)
    };
  }
}
