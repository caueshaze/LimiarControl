
import type { Coordinate, GridCalibration, Obstacle } from "@limiarmap/shared-contracts";

export type GridEditInteractionMode = "move" | "resize-x" | "resize-y" | "resize-both";

export interface GridEditInteraction {
  mode: GridEditInteractionMode;
  startClientX: number;
  startClientY: number;
  startCalibration: GridCalibration;
}

export interface ObstacleCellState {
  blocksMovement: boolean;
  blocksEffect: boolean;
  blocksVision: boolean;
  cover: Obstacle["cover"];
  /** Phase 7: highest movement cost multiplier among all obstacles on this cell. */
  movementCostMultiplier: number;
}

// ─── Colors (matching CSS Grid renderer) ─────────────────────────────────────

