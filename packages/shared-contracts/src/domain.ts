import { z } from "zod";

export const MAX_GRID_DIMENSION = 150;

/**
 * Default map scale: 1.5 meters per cell.
 * Compatible with standard D&D 5e grids (5 ft ≈ 1.5 m per cell).
 * All meter values from the Control domain must be converted to cells
 * using this constant before being sent to the Map tactical engine.
 */
export const METERS_PER_CELL = 1.5;

export const coordinateSchema = z.object({
  x: z.number().int().nonnegative(),
  y: z.number().int().nonnegative()
});

export const gridCalibrationSchema = z
  .object({
    x: z.number().min(0).max(1),
    y: z.number().min(0).max(1),
    width: z.number().positive().max(1),
    height: z.number().positive().max(1)
  })
  .refine((value) => value.x + value.width <= 1, {
    message: "Grid calibration width exceeds image bounds"
  })
  .refine((value) => value.y + value.height <= 1, {
    message: "Grid calibration height exceeds image bounds"
  });

const gridDimensionSchema = z.number().int().positive().max(MAX_GRID_DIMENSION);

export const gridDimensionsSchema = z.object({
  gridWidth: gridDimensionSchema,
  gridHeight: gridDimensionSchema
});

export const controllerTypeSchema = z.enum(["player", "gm", "limiarControl"]);
export const actionResultSchema = z.enum(["pending", "accepted", "rejected"]);
export const combatStatusSchema = z.enum(["inactive", "active", "completed"]);
export const targetingShapeSchema = z.enum(["line", "cone", "sphere", "cube", "cylinder"]);
export const obstacleCoverSchema = z.enum(["none", "half", "threeQuarters", "full"]);
export const obstaclePaintModeSchema = z.enum(["paint", "erase"]);

/**
 * Phase 10: Edge obstacle direction.
 * An edge is the boundary of a cell in one of the four cardinal directions.
 */
export const edgeDirectionSchema = z.enum(["N", "E", "S", "W"]);

/**
 * Phase 10: Edge obstacle representation.
 * Each edge is defined between two adjacent cells by a coordinate and direction.
 * Example: (x=5, y=5, direction="E") represents the edge between (5,5) and (6,5).
 */
export const edgeObstacleSchema = z.object({
  id: z.string(),
  battleMapId: z.string(),
  x: z.number().int().nonnegative(),
  y: z.number().int().nonnegative(),
  direction: edgeDirectionSchema,
  blocksMovement: z.boolean(),
  blocksVision: z.boolean().default(false),
  blocksEffect: z.boolean(),
  cover: obstacleCoverSchema.default("none"),
  label: z.string().optional()
});

export const battleMapSchema = z.object({
  id: z.string(),
  name: z.string(),
  gridWidth: gridDimensionSchema,
  gridHeight: gridDimensionSchema,
  imageUrl: z.string().optional(),
  terrainVersion: z.number().int().nonnegative(),
  gridCalibration: gridCalibrationSchema,
  activeEncounterId: z.string().optional()
});

const obstacleSemanticsInputSchema = z.object({
  blocksMovement: z.boolean(),
  /**
   * Authoritative Phase 2 effect-blocking flag.
   * Old payloads may still send `blocksTargeting` or `blocksSpell`; those are
   * normalized into this field for backward compatibility.
   */
  blocksEffect: z.boolean().optional(),
  /**
   * Legacy alias kept only for backward-compatible parsing of old payloads.
   * Prefer `blocksEffect` everywhere else.
   */
  blocksTargeting: z.boolean().optional(),
  /**
   * Legacy alias kept only for backward-compatible parsing of old payloads.
   * Prefer `blocksEffect` everywhere else.
   */
  blocksSpell: z.boolean().optional(),
  blocksVision: z.boolean().default(false),
  cover: obstacleCoverSchema.default("none"),
  clipsDiagonalMovement: z.boolean().default(false),
  /**
   * Phase 7: movement cost multiplier for terrain.
   * 1 = normal traversal (default, backward-compatible).
   * 2 = difficult terrain — entering this cell costs twice the base step cost.
   * Only meaningful when blocksMovement = false; blocked cells remain invalid
   * regardless of this value. Use integer multipliers only.
   */
  movementCostMultiplier: z.number().int().min(1).default(1)
});

function normalizeObstacleSemantics<T extends z.input<typeof obstacleSemanticsInputSchema>>(
  value: T
) {
  return {
    blocksMovement: value.blocksMovement,
    blocksEffect:
      value.blocksEffect ?? (value.blocksTargeting === true || value.blocksSpell === true),
    blocksVision: value.blocksVision ?? false,
    cover: value.cover ?? "none",
    clipsDiagonalMovement: value.clipsDiagonalMovement ?? false,
    movementCostMultiplier: value.movementCostMultiplier ?? 1
  };
}

export const obstacleStyleSchema = obstacleSemanticsInputSchema.transform((value) =>
  normalizeObstacleSemantics(value)
);

export const obstacleSchema = obstacleSemanticsInputSchema
  .extend({
    id: z.string(),
    battleMapId: z.string(),
    cells: z.array(coordinateSchema),
    label: z.string().optional()
  })
  .transform((value) => ({
    id: value.id,
    battleMapId: value.battleMapId,
    cells: value.cells,
    ...(value.label !== undefined ? { label: value.label } : {}),
    ...normalizeObstacleSemantics(value)
  }));

export const tokenSchema = z.object({
  id: z.string(),
  battleMapId: z.string(),
  label: z.string(),
  kind: z.enum(["playerCharacter", "ally", "enemy", "neutral"]),
  controllerType: controllerTypeSchema,
  controllerId: z.string(),
  position: coordinateSchema,
  /**
   * Maximum movement per turn, in grid cells.
   * The tactical engine internally multiplies this by 5 to obtain the
   * movement budget in path-cost units (5 units per orthogonal step).
   * Conversion: speedMeters / METERS_PER_CELL = movementSpeedCells (floor).
   */
  movementSpeedCells: z.number().int().positive(),
  /**
   * Remaining movement budget for the current turn, in path-cost units
   * (5 units = 1 orthogonal cell, matches D&D 5-foot-square grid).
   * Reset to movementSpeedCells * 5 at the start of each turn.
   */
  movementBudget: z.number().int().nonnegative(),
  combatantId: z.string().optional(),
  /**
   * Active condition codes on this token (e.g. "blinded", "stunned").
   * Pushed by LimiarControl via syncTokens; empty when no conditions are active.
   * These are canonical machine-readable codes — the UI presentation layer
   * (condition-indicators.ts) maps them to labels, colours, and priority order.
   */
  conditions: z.array(z.string()).default([])
});

export const combatStateSchema = z.object({
  id: z.string(),
  battleMapId: z.string(),
  status: combatStatusSchema,
  roundNumber: z.number().int().nonnegative(),
  turnIndex: z.number().int().nonnegative(),
  activeCombatantId: z.string().nullable(),
  initiativeOrder: z.array(z.string()),
  advancedBy: z.literal("LimiarControl"),
  version: z.number().int().nonnegative()
});

export const movementActionSchema = z.object({
  actionId: z.string(),
  tokenId: z.string(),
  requestedPath: z.array(coordinateSchema),
  submittedBy: z.string(),
  submittedAtVersion: z.number().int().nonnegative(),
  result: actionResultSchema.default("pending"),
  rejectionReason: z.string().optional()
});

export const targetingTemplateSchema = z.object({
  actionId: z.string(),
  tokenId: z.string(),
  shape: targetingShapeSchema,
  originCell: coordinateSchema,
  anchorCell: coordinateSchema,
  /** Maximum reach from the origin, in grid cells (Chebyshev distance). */
  rangeCells: z.number().int().positive(),
  /** AoE radius / dimension, in grid cells. */
  sizeCells: z.number().int().positive(),
  affectedCells: z.array(coordinateSchema).default([]),
  result: actionResultSchema.default("pending"),
  rejectionReason: z.string().optional()
});

export const realtimeActionEventSchema = z.object({
  eventId: z.string(),
  eventType: z.string(),
  encounterId: z.string(),
  version: z.number().int().nonnegative(),
  actionId: z.string().optional(),
  payload: z.record(z.unknown()),
  replaySafe: z.boolean().default(true)
});

export type Coordinate = z.infer<typeof coordinateSchema>;
export type GridCalibration = z.infer<typeof gridCalibrationSchema>;
export type GridDimensions = z.infer<typeof gridDimensionsSchema>;
export type ControllerType = z.infer<typeof controllerTypeSchema>;
export type ObstacleCover = z.infer<typeof obstacleCoverSchema>;
export type ObstaclePaintMode = z.infer<typeof obstaclePaintModeSchema>;
export type EdgeDirection = z.infer<typeof edgeDirectionSchema>;
export type BattleMap = z.infer<typeof battleMapSchema>;
export type ObstacleStyle = z.infer<typeof obstacleStyleSchema>;
export type Obstacle = z.infer<typeof obstacleSchema>;
export type EdgeObstacle = z.infer<typeof edgeObstacleSchema>;
export type Token = z.infer<typeof tokenSchema>;
export type CombatState = z.infer<typeof combatStateSchema>;
export type MovementAction = z.infer<typeof movementActionSchema>;
export type TargetingTemplate = z.infer<typeof targetingTemplateSchema>;
export type RealtimeActionEvent = z.infer<typeof realtimeActionEventSchema>;
