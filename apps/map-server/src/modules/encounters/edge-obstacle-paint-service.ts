import type {
  ControllerType,
  EdgeObstacle,
  ObstacleCover,
  ObstacleStyle
} from "@limiarmap/shared-contracts";
import { edgeObstacleSchema, obstacleStyleSchema } from "@limiarmap/shared-contracts";
import { isInsideMap, nextEncounterVersion } from "@limiarmap/tactical-engine";
import type { InMemoryEncounterRepository } from "./encounter-repository";

/**
 * Phase 10: Edge obstacle paint service.
 * Handles painting and erasing edge obstacles on the map grid.
 */
export class EdgeObstaclePaintService {
  constructor(private readonly repository: InMemoryEncounterRepository) {}

  /**
   * Paint or erase an edge obstacle at a specific cell and direction.
   */
  paintEdgeObstacle(
    sessionId: string,
    actorType: ControllerType,
    cell: { x: number; y: number },
    direction: "N" | "E" | "S" | "W",
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

    // Validate cell coordinates
    if (!isInsideMap({ map: encounter.battleMap, obstacles: [], edgeObstacles: [], tokens: [] }, cell)) {
      return { accepted: false, rejectionReason: "outside_map", encounter };
    }

    // Validate direction
    if (!["N", "E", "S", "W"].includes(direction)) {
      return { accepted: false, rejectionReason: "invalid_direction", encounter };
    }

    let nextEdgeObstacles = [...encounter.edgeObstacles];

    if (mode === "paint") {
      // Validate style
      const styleValidation = obstacleStyleSchema.safeParse(style);
      if (!styleValidation.success) {
        return { accepted: false, rejectionReason: "invalid_edge_style", encounter };
      }

      // Remove existing edge at same position if any
      nextEdgeObstacles = nextEdgeObstacles.filter(
        (e) => !(e.x === cell.x && e.y === cell.y && e.direction === direction)
      );

      // Create new edge obstacle
      const newEdgeObstacle: EdgeObstacle = {
        id: `edge:${actionId}`,
        battleMapId: encounter.battleMap.id,
        x: cell.x,
        y: cell.y,
        direction,
        blocksMovement: styleValidation.data.blocksMovement,
        blocksVision: styleValidation.data.blocksVision ?? false,
        blocksEffect: styleValidation.data.blocksEffect ?? false,
        cover: styleValidation.data.cover ?? "none",
        label: this.buildEdgeObstacleLabel(styleValidation.data)
      };

      nextEdgeObstacles.push(newEdgeObstacle);
    } else {
      // Remove edge obstacle at this position
      nextEdgeObstacles = nextEdgeObstacles.filter(
        (e) => !(e.x === cell.x && e.y === cell.y && e.direction === direction)
      );
    }

    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };

    this.repository.setEdgeObstacles(sessionId, nextEdgeObstacles);
    this.repository.updateCombatState(sessionId, encounter.combatState);

    return {
      accepted: true,
      encounter: this.repository.requireEncounter(sessionId)
    };
  }

  /**
   * Generate a human-readable label for an edge obstacle.
   */
  private buildEdgeObstacleLabel(style: ObstacleStyle): string {
    // Full wall edge: blocks movement, effect, and vision
    if (style.blocksMovement && style.blocksEffect && style.blocksVision) {
      return "Parede (borda)";
    }

    // Movement-only edge: blocks movement but allows vision and effects
    if (style.blocksMovement && !style.blocksEffect && !style.blocksVision) {
      return "Barreira de movimento";
    }

    // Effect-blocking edge: blocks effects but allows vision
    if (style.blocksEffect && !style.blocksVision) {
      return "Barreira de efeito (borda)";
    }

    // Vision-blocking edge: blocks vision but allows effects
    if (style.blocksVision && !style.blocksEffect) {
      return "Barreira visual (borda)";
    }

    // Cover edge: provides cover without blocking
    if (style.cover === "half") {
      return "Cobertura 1/2 (borda)";
    }

    if (style.cover === "threeQuarters") {
      return "Cobertura 3/4 (borda)";
    }

    return "Borda";
  }

  /**
   * Get edge obstacles for a specific cell.
   */
  getEdgeObstaclesForCell(sessionId: string, cell: { x: number; y: number }): EdgeObstacle[] {
    const encounter = this.repository.getEncounter(sessionId);
    if (!encounter) return [];

    return encounter.edgeObstacles.filter(
      (e) => e.x === cell.x && e.y === cell.y
    );
  }

  /**
   * Check if there's an edge between two adjacent cells.
   */
  getEdgeBetweenCells(
    sessionId: string,
    fromCell: { x: number; y: number },
    toCell: { x: number; y: number }
  ): EdgeObstacle | undefined {
    const encounter = this.repository.getEncounter(sessionId);
    if (!encounter) return undefined;

    // Determine which direction the edge is in
    const dx = toCell.x - fromCell.x;
    const dy = toCell.y - fromCell.y;

    // Only adjacent orthogonal cells have edges between them
    if (Math.abs(dx) + Math.abs(dy) !== 1) return undefined;

    let direction: "N" | "E" | "S" | "W";
    let cell: { x: number; y: number };

    if (dx === 1) {
      // Moving East: edge is on the East side of fromCell
      direction = "E";
      cell = fromCell;
    } else if (dx === -1) {
      // Moving West: edge is on the West side of fromCell
      direction = "W";
      cell = fromCell;
    } else if (dy === 1) {
      // Moving South: edge is on the South side of fromCell
      direction = "S";
      cell = fromCell;
    } else {
      // Moving North: edge is on the North side of fromCell
      direction = "N";
      cell = fromCell;
    }

    return encounter.edgeObstacles.find(
      (e) => e.x === cell.x && e.y === cell.y && e.direction === direction
    );
  }
}
