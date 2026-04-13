import type {
  ControllerType,
  Coordinate,
  Obstacle,
  ObstacleStyle
} from "@limiarmap/shared-contracts";
import { obstacleStyleSchema } from "@limiarmap/shared-contracts";
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
      if (chebyshevDistance(centerCell, coordinate) > radius || !isInsideMap({ map, obstacles: [], tokens: [] }, coordinate)) {
        continue;
      }

      cells.push(coordinate);
    }
  }

  return cells;
}

function removeCellsFromObstacles(obstacles: Obstacle[], cellsToRemove: Coordinate[]): Obstacle[] {
  const removedKeys = new Set(cellsToRemove.map((cell) => coordinateKey(cell)));

  return obstacles
    .map((obstacle) => ({
      ...obstacle,
      cells: obstacle.cells.filter((cell) => !removedKeys.has(coordinateKey(cell)))
    }))
    .filter((obstacle) => obstacle.cells.length > 0);
}

function buildObstacleLabel(style: ObstacleStyle): string {
  // Full solid wall: all blocking flags set
  if (style.blocksMovement && style.blocksEffect && style.blocksVision) {
    return "Parede solida";
  }

  // Dense obstacle: movement block + three-quarters cover (e.g. boulder, pillar)
  if (style.blocksMovement && style.cover === "threeQuarters") {
    return "Obstaculo denso";
  }

  // Transparent barrier: blocks movement + effect but not vision (e.g. force wall)
  if (style.blocksMovement && style.blocksEffect && !style.blocksVision) {
    return "Barreira transparente";
  }

  // Movement-only block, no cover
  if (style.blocksMovement && !style.blocksEffect) {
    return "Passagem bloqueada";
  }

  // Phase 7: difficult terrain — traversable but movement costs double
  if (!style.blocksMovement && style.movementCostMultiplier > 1) {
    return "Terreno dificil";
  }

  // Three-quarters cover only (no block flags)
  if (style.cover === "threeQuarters") {
    return "Cobertura 3/4";
  }

  // Half cover only (e.g. barricade, sandbags)
  if (style.cover === "half") {
    return "Barricada";
  }

  // Effect-only barrier, no vision block
  if (style.blocksEffect && !style.blocksVision) {
    return "Barreira de efeito";
  }

  // Vision-only barrier
  if (style.blocksVision && !style.blocksEffect) {
    return "Barreira visual";
  }

  return "Obstaculo tatico";
}

export class ObstaclePaintService {
  constructor(private readonly repository: InMemoryEncounterRepository) {}

  paintObstacle(
    sessionId: string,
    actorType: ControllerType,
    centerCell: Coordinate,
    radius: number,
    mode: "paint" | "erase",
    style: ObstacleStyle | undefined,
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
      return { accepted: false, rejectionReason: "invalid_obstacle_brush", encounter };
    }

    if (!isInsideMap({ map: encounter.battleMap, obstacles: [], tokens: [] }, centerCell)) {
      return { accepted: false, rejectionReason: "outside_map", encounter };
    }

    const targetCells = buildCircleCells(centerCell, radius, encounter.battleMap);
    if (targetCells.length === 0) {
      return { accepted: false, rejectionReason: "invalid_obstacle_brush", encounter };
    }

    let nextObstacles = removeCellsFromObstacles(encounter.obstacles, targetCells);

    if (mode === "paint") {
      const styleValidation = obstacleStyleSchema.safeParse(style);
      if (!styleValidation.success) {
        return { accepted: false, rejectionReason: "invalid_obstacle_style", encounter };
      }

      nextObstacles = [
        ...nextObstacles,
        {
          id: `obs:${actionId}`,
          battleMapId: encounter.battleMap.id,
          label: buildObstacleLabel(styleValidation.data),
          cells: targetCells,
          ...styleValidation.data
        }
      ];
    }

    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };

    this.repository.setObstacles(sessionId, nextObstacles);
    this.repository.updateCombatState(sessionId, encounter.combatState);

    return {
      accepted: true,
      encounter: this.repository.requireEncounter(sessionId)
    };
  }
}
