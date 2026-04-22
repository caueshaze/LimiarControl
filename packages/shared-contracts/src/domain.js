import { z } from "zod";
export const MAX_GRID_DIMENSION = 150;
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
export const battleMapSchema = z.object({
    id: z.string(),
    name: z.string(),
    gridWidth: gridDimensionSchema,
    gridHeight: gridDimensionSchema,
    terrainVersion: z.number().int().nonnegative(),
    gridCalibration: gridCalibrationSchema,
    activeEncounterId: z.string().optional()
});
const obstacleSemanticsInputSchema = z.object({
    blocksMovement: z.boolean(),
    blocksEffect: z.boolean().optional(),
    blocksTargeting: z.boolean().optional(),
    blocksSpell: z.boolean().optional(),
    blocksVision: z.boolean().default(false),
    cover: obstacleCoverSchema.default("none"),
    clipsDiagonalMovement: z.boolean().default(false),
    movementCostMultiplier: z.number().int().min(1).default(1)
});
function normalizeObstacleSemantics(value) {
    return {
        blocksMovement: value.blocksMovement,
        blocksEffect: value.blocksEffect ?? (value.blocksTargeting === true || value.blocksSpell === true),
        blocksVision: value.blocksVision ?? false,
        cover: value.cover ?? "none",
        clipsDiagonalMovement: value.clipsDiagonalMovement ?? false,
        movementCostMultiplier: value.movementCostMultiplier ?? 1
    };
}
export const edgeDirectionSchema = z.enum(["N", "E", "S", "W"]);
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
export const obstacleStyleSchema = obstacleSemanticsInputSchema.transform((value) => normalizeObstacleSemantics(value));
export const obstacleSchema = obstacleSemanticsInputSchema.extend({
    id: z.string(),
    battleMapId: z.string(),
    cells: z.array(coordinateSchema),
    label: z.string().optional()
}).transform((value) => ({
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
    movementSpeedCells: z.number().int().positive(),
    movementBudget: z.number().int().nonnegative(),
    combatantId: z.string().optional()
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
    rangeCells: z.number().int().positive(),
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
