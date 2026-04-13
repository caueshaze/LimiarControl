import { z } from "zod";
import { combatStateSchema, coordinateSchema, gridCalibrationSchema, gridDimensionsSchema, obstaclePaintModeSchema, obstacleSchema, obstacleStyleSchema, realtimeActionEventSchema, targetingShapeSchema } from "./domain";
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
    rangeCells: z.number().int().positive(),
    sizeCells: z.number().int().positive(),
    knownVersion: z.number().int().nonnegative(),
    requiresSight: z.boolean().default(false),
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
export const gridCalibrationUpdatedEventSchema = realtimeActionEventSchema.extend({
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
