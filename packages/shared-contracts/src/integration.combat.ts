import { z } from "zod";
import {
  battleMapSchema,
  activeAreaEffectSchema,
  cellElevationSchema,
  combatStateSchema,
  coordinateSchema,
  controllerTypeSchema,
  edgeObstacleSchema,
  obstacleCoverSchema,
  obstacleSchema,
  tokenSchema,
} from "./domain";

export const initiativeEntrySchema = z.object({
  combatantId: z.string(),
  initiativeScore: z.number(),
});

export const campaignObstacleInputSchema = z.object({
  x: z.number().int().min(0),
  y: z.number().int().min(0),
  blocksMovement: z.boolean(),
  blocksEffect: z.boolean().default(false),
  blocksVision: z.boolean().default(false),
  cover: obstacleCoverSchema.default("none"),
  clipsDiagonalMovement: z.boolean().default(false),
  movementCostMultiplier: z.number().int().min(1).default(1),
});

export type CampaignObstacleInput = z.infer<typeof campaignObstacleInputSchema>;

export const campaignEdgeObstacleInputSchema = z.object({
  x: z.number().int().min(0),
  y: z.number().int().min(0),
  direction: z.enum(["N", "E", "S", "W"]),
  blocksMovement: z.boolean(),
  blocksVision: z.boolean().default(false),
  blocksEffect: z.boolean().default(false),
  cover: obstacleCoverSchema.default("none"),
});

export type CampaignEdgeObstacleInput = z.infer<typeof campaignEdgeObstacleInputSchema>;

export const integrationBattleMapSchema = z.object({
  name: z.string(),
  gridWidth: z.number().int().positive().max(150),
  gridHeight: z.number().int().positive().max(150),
  gridCalibration: battleMapSchema.shape.gridCalibration,
  imageUrl: z.string(),
  sourceImageUrl: z.string().nullable().optional(),
  obstacles: z.array(campaignObstacleInputSchema).optional(),
  edgeObstacles: z.array(campaignEdgeObstacleInputSchema).optional(),
  blockedCells: z.array(coordinateSchema).optional(),
  cellElevations: z.array(cellElevationSchema).optional(),
});

export const startCombatRequestSchema = z.object({
  actionId: z.string(),
  combatants: z.array(initiativeEntrySchema).min(1),
  battleMap: integrationBattleMapSchema.optional(),
});

export const setInitiativeRequestSchema = z.object({
  actionId: z.string(),
  combatants: z.array(initiativeEntrySchema).min(1),
});

export const advanceTurnRequestSchema = z.object({
  actionId: z.string(),
});

export const endCombatRequestSchema = z.object({
  actionId: z.string(),
});

export const tokenSyncEntrySchema = z.object({
  tokenId: z.string().optional(),
  combatantId: z.string().optional(),
  kind: tokenSchema.shape.kind.optional(),
  movementSpeedCells: z.number().int().positive().optional(),
  label: z.string().min(1).optional(),
  controllerId: z.string().optional(),
  controllerType: controllerTypeSchema.optional(),
  conditions: z.array(z.string()).optional(),
  sizeCategory: z.string().optional(),
});

export const syncTokensRequestSchema = z.object({
  tokens: z.array(tokenSyncEntrySchema).min(1),
});

export const syncActiveAreaEffectsRequestSchema = z.object({
  activeAreaEffects: z.array(activeAreaEffectSchema),
});

export const integrationStateResponseSchema = z.object({
  sessionId: z.string(),
  version: z.number().int().nonnegative(),
  battleMap: battleMapSchema,
  combatState: combatStateSchema,
  tokens: z.array(tokenSchema),
  obstacles: z.array(obstacleSchema),
  edgeObstacles: z.array(edgeObstacleSchema).default([]),
  activeAreaEffects: z.array(activeAreaEffectSchema).default([]),
  cellElevations: z.array(cellElevationSchema).default([]),
});

export const movementPreviewRequestSchema = z.object({
  actionId: z.string(),
  combatantId: z.string(),
  destinationCell: coordinateSchema,
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
  remainingBudget: z.number().int().nonnegative(),
  sourceElevationMeters: z.number().nullable().optional(),
  destinationElevationMeters: z.number().nullable().optional(),
});

export type InitiativeEntry = z.infer<typeof initiativeEntrySchema>;
export type StartCombatRequest = z.infer<typeof startCombatRequestSchema>;
export type SetInitiativeRequest = z.infer<typeof setInitiativeRequestSchema>;
export type AdvanceTurnRequest = z.infer<typeof advanceTurnRequestSchema>;
export type EndCombatRequest = z.infer<typeof endCombatRequestSchema>;
export type TokenSyncEntry = z.infer<typeof tokenSyncEntrySchema>;
export type SyncTokensRequest = z.infer<typeof syncTokensRequestSchema>;
export type SyncActiveAreaEffectsRequest = z.infer<typeof syncActiveAreaEffectsRequestSchema>;
export type IntegrationStateResponse = z.infer<typeof integrationStateResponseSchema>;
export type MovementPreviewRequest = z.infer<typeof movementPreviewRequestSchema>;
export type MovementPreviewResponse = z.infer<typeof movementPreviewResponseSchema>;
