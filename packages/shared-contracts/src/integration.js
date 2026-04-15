import { z } from "zod";
import {
    battleMapSchema,
    combatStateSchema,
    coordinateSchema,
    controllerTypeSchema,
    obstacleSchema,
    tokenSchema
} from "./domain";
export const initiativeEntrySchema = z.object({
    combatantId: z.string(),
    initiativeScore: z.number()
});
export const integrationBattleMapSchema = z.object({
    name: z.string(),
    gridWidth: z.number().int().positive().max(150),
    gridHeight: z.number().int().positive().max(150),
    gridCalibration: battleMapSchema.shape.gridCalibration,
    imageUrl: z.string(),
    sourceImageUrl: z.string().nullable().optional(),
    blockedCells: z.array(coordinateSchema).optional()
});
export const startCombatRequestSchema = z.object({
    actionId: z.string(),
    combatants: z.array(initiativeEntrySchema).min(1),
    battleMap: integrationBattleMapSchema.optional()
});
export const setInitiativeRequestSchema = z.object({
    actionId: z.string(),
    combatants: z.array(initiativeEntrySchema).min(1)
});
export const advanceTurnRequestSchema = z.object({
    actionId: z.string()
});
export const endCombatRequestSchema = z.object({
    actionId: z.string()
});
export const tokenSyncEntrySchema = z.object({
    tokenId: z.string(),
    combatantId: z.string().optional(),
    movementSpeedCells: z.number().int().positive().optional(),
    label: z.string().min(1).optional(),
    controllerId: z.string().optional(),
    controllerType: controllerTypeSchema.optional()
});
export const syncTokensRequestSchema = z.object({
    tokens: z.array(tokenSyncEntrySchema).min(1)
});
export const singleTargetRequestSchema = z.object({
    actionId: z.string(),
    combatantId: z.string(),
    targetCombatantId: z.string(),
    rangeCells: z.number().int().positive().nullable(),
    requiresSight: z.boolean().default(false),
    requiresEffect: z.boolean().default(false)
});
export const areaTargetShapeSchema = z.enum(["sphere", "cone", "line"]);
export const areaTargetRequestSchema = z.object({
    actionId: z.string(),
    combatantId: z.string(),
    shape: areaTargetShapeSchema,
    originCell: coordinateSchema,
    anchorCell: coordinateSchema,
    rangeCells: z.number().int().positive().nullable(),
    sizeCells: z.number().int().positive(),
    requiresSight: z.boolean().default(false),
    requiresEffect: z.boolean().default(false)
});
export const integrationStateResponseSchema = z.object({
    sessionId: z.string(),
    version: z.number().int().nonnegative(),
    battleMap: battleMapSchema,
    combatState: combatStateSchema,
    tokens: z.array(tokenSchema),
    obstacles: z.array(obstacleSchema)
});
export const singleTargetResponseSchema = z.object({
    isValid: z.boolean(),
    reason: z.string().nullable(),
    sessionId: z.string(),
    actionId: z.string(),
    version: z.number().int().nonnegative(),
    sourceTokenId: z.string().nullable(),
    targetTokenId: z.string().nullable(),
    distanceCells: z.number().int().nonnegative().nullable().optional()
});
export const areaTargetResponseSchema = z.object({
    isValid: z.boolean(),
    reason: z.string().nullable(),
    sessionId: z.string(),
    actionId: z.string(),
    version: z.number().int().nonnegative(),
    shape: areaTargetShapeSchema,
    sourceTokenId: z.string().nullable(),
    affectedCells: z.array(coordinateSchema),
    affectedTokenIds: z.array(z.string()),
    affectedCombatantIds: z.array(z.string())
});
export const areaTargetPreviewResponseSchema = areaTargetResponseSchema;
export const movementPreviewRequestSchema = z.object({
    actionId: z.string(),
    combatantId: z.string(),
    destinationCell: coordinateSchema
});
export const movementPreviewResponseSchema = z.object({
    isValid: z.boolean(),
    reason: z.string().nullable(),
    sessionId: z.string(),
    actionId: z.string(),
    version: z.number().int().nonnegative(),
    tokenId: z.string().nullable(),
    combatantId: z.string().nullable(),
    sourceCell: coordinateSchema.nullable(),
    destinationCell: coordinateSchema,
    path: z.array(coordinateSchema),
    pathCostUnits: z.number().int().nonnegative(),
    movementBudget: z.number().int().nonnegative(),
    movementSpeedCells: z.number().int().positive(),
    remainingBudget: z.number().int().nonnegative()
});
export const integrationErrorResponseSchema = z.object({
    message: z.string(),
    reason: z.string()
});
export const integrationSpatialEventTypeSchema = z.enum([
    "movement.applied",
    "tokens.synced",
    "combat.started",
    "combat.advanced",
    "combat.ended",
    "initiative.updated",
    "targeting.resolved",
    "action.rejected",
    "obstacles.updated",
    "edge_obstacles.updated",
    "grid.calibration.updated"
]);
export const integrationSpatialEventEnvelopeSchema = z.object({
    eventId: z.string(),
    eventType: integrationSpatialEventTypeSchema,
    encounterId: z.string(),
    version: z.number().int().nonnegative(),
    actionId: z.string().optional(),
    payload: z.record(z.unknown()),
    replaySafe: z.boolean().default(true)
});
export const combatStartedPayloadSchema = z.object({
    roundNumber: z.number().int().nonnegative(),
    turnIndex: z.number().int().nonnegative(),
    activeCombatantId: z.string().nullable(),
    initiativeOrder: z.array(z.string())
});
export const combatEndedPayloadSchema = z.object({
    roundNumber: z.number().int().nonnegative()
});
export const initiativeUpdatedPayloadSchema = z.object({
    initiativeOrder: z.array(z.string()),
    activeCombatantId: z.string().nullable(),
    turnIndex: z.number().int().nonnegative()
});
export const tokensSyncedPayloadSchema = z.object({
    tokens: z.array(tokenSchema)
});
export const singleTargetResolvedPayloadSchema = z.object({
    sourceTokenId: z.string(),
    targetTokenId: z.string(),
    isValid: z.boolean(),
    reason: z.string().nullable()
});
export const areaTargetResolvedPayloadSchema = z.object({
    sourceTokenId: z.string(),
    shape: areaTargetShapeSchema,
    affectedCells: z.array(coordinateSchema),
    affectedTokenIds: z.array(z.string()),
    affectedCombatantIds: z.array(z.string()),
    isValid: z.boolean(),
    reason: z.string().nullable()
});
