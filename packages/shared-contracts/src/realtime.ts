import { z } from "zod";
import {
  cellElevationSchema,
  combatStateSchema,
  coordinateSchema,
  edgeDirectionSchema,
  edgeObstacleSchema,
  gridCalibrationSchema,
  gridDimensionsSchema,
  obstaclePaintModeSchema,
  obstacleSchema,
  obstacleStyleSchema,
  realtimeActionEventSchema,
  targetingShapeSchema
} from "./domain";

export const movementRequestSchema = z.object({
  actionId: z.string(),
  sessionId: z.string(),
  tokenId: z.string(),
  path: z.array(coordinateSchema),
  knownVersion: z.number().int().nonnegative()
});

export const combatAdvanceRequestSchema = z.object({
  actionId: z.string(),
  sessionId: z.string(),
  knownVersion: z.number().int().nonnegative(),
  requestedBy: z.literal("limiarControl")
});

export const targetingSubmitSchema = z.object({
  actionId: z.string(),
  sessionId: z.string(),
  tokenId: z.string(),
  shape: targetingShapeSchema,
  originCell: coordinateSchema,
  anchorCell: coordinateSchema,
  /** Maximum reach from origin, in grid cells. */
  rangeCells: z.number().int().positive(),
  /** AoE radius / dimension, in grid cells. */
  sizeCells: z.number().int().positive(),
  knownVersion: z.number().int().nonnegative(),
  /** When true, checks line of sight from origin to anchor. */
  requiresSight: z.boolean().default(false),
  /** When true, checks line of effect from origin to anchor. */
  requiresEffect: z.boolean().default(false)
});

export const gridCalibrationRequestSchema = z.object({
  actionId: z.string(),
  sessionId: z.string(),
  knownVersion: z.number().int().nonnegative(),
  gridCalibration: gridCalibrationSchema,
  gridWidth: gridDimensionsSchema.shape.gridWidth,
  gridHeight: gridDimensionsSchema.shape.gridHeight
});

export const obstaclePaintRequestSchema = z.object({
  actionId: z.string(),
  sessionId: z.string(),
  knownVersion: z.number().int().nonnegative(),
  mode: obstaclePaintModeSchema,
  centerCell: coordinateSchema,
  radius: z.number().int().nonnegative().max(12),
  style: obstacleStyleSchema.optional()
});

export const edgeObstaclePaintRequestSchema = z.object({
  actionId: z.string(),
  sessionId: z.string(),
  knownVersion: z.number().int().nonnegative(),
  mode: obstaclePaintModeSchema,
  cell: coordinateSchema,
  direction: edgeDirectionSchema,
  style: obstacleStyleSchema.optional()
});

export const elevationPaintRequestSchema = z.object({
  actionId: z.string(),
  sessionId: z.string(),
  knownVersion: z.number().int().nonnegative(),
  mode: obstaclePaintModeSchema,
  centerCell: coordinateSchema,
  radius: z.number().int().nonnegative().max(12),
  elevationMeters: z.number().finite().min(0).max(100).optional()
});

export const movementAppliedEventSchema = realtimeActionEventSchema.extend({
  payload: z.object({
    tokenId: z.string(),
    position: coordinateSchema,
    pathCostUnits: z.number().int().nonnegative(),
    remainingBudget: z.number().int().nonnegative()
  })
});

export const combatAdvancedEventSchema = realtimeActionEventSchema.extend({
  payload: combatStateSchema.pick({
    roundNumber: true,
    turnIndex: true,
    activeCombatantId: true
  })
});

export const targetingResolvedEventSchema = realtimeActionEventSchema.extend({
  payload: z.object({
    tokenId: z.string(),
    shape: targetingShapeSchema,
    affectedCells: z.array(coordinateSchema)
  })
});

export const gridCalibrationUpdatedEventSchema =
  realtimeActionEventSchema.extend({
    payload: z.object({
      battleMapId: z.string(),
      gridCalibration: gridCalibrationSchema,
      gridWidth: gridDimensionsSchema.shape.gridWidth,
      gridHeight: gridDimensionsSchema.shape.gridHeight
    })
  });

export const obstaclesUpdatedEventSchema = realtimeActionEventSchema.extend({
  payload: z.object({
    battleMapId: z.string(),
    obstacles: z.array(obstacleSchema)
  })
});

export const edgeObstaclesUpdatedEventSchema = realtimeActionEventSchema.extend(
  {
    payload: z.object({
      battleMapId: z.string(),
      edgeObstacles: z.array(edgeObstacleSchema)
    })
  }
);

export const elevationUpdatedEventSchema = realtimeActionEventSchema.extend({
  payload: z.object({
    battleMapId: z.string(),
    cellElevations: z.array(cellElevationSchema)
  })
});

export const actionRejectedEventSchema = realtimeActionEventSchema.extend({
  payload: z.object({
    reason: z.string(),
    message: z.string(),
    details: z.string().optional(),
    tokenId: z.string().optional(),
    pathCostUnits: z.number().int().nonnegative().optional(),
    movementBudget: z.number().int().nonnegative().optional(),
    exceededBy: z.number().int().nonnegative().optional()
  })
});

export type MovementRequest = z.infer<typeof movementRequestSchema>;
export type CombatAdvanceRequest = z.infer<typeof combatAdvanceRequestSchema>;
export type TargetingSubmitRequest = z.infer<typeof targetingSubmitSchema>;
export type GridCalibrationRequest = z.infer<
  typeof gridCalibrationRequestSchema
>;
export type ObstaclePaintRequest = z.infer<typeof obstaclePaintRequestSchema>;
export type EdgeObstaclePaintRequest = z.infer<
  typeof edgeObstaclePaintRequestSchema
>;
export type MovementAppliedEvent = z.infer<typeof movementAppliedEventSchema>;
export type CombatAdvancedEvent = z.infer<typeof combatAdvancedEventSchema>;
export type TargetingResolvedEvent = z.infer<
  typeof targetingResolvedEventSchema
>;
export type GridCalibrationUpdatedEvent = z.infer<
  typeof gridCalibrationUpdatedEventSchema
>;
export type ObstaclesUpdatedEvent = z.infer<typeof obstaclesUpdatedEventSchema>;
export type EdgeObstaclesUpdatedEvent = z.infer<
  typeof edgeObstaclesUpdatedEventSchema
>;
export type ElevationPaintRequest = z.infer<typeof elevationPaintRequestSchema>;
export type ElevationUpdatedEvent = z.infer<typeof elevationUpdatedEventSchema>;
export type ActionRejectedEvent = z.infer<typeof actionRejectedEventSchema>;
