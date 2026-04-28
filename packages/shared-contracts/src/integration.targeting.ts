import { z } from "zod";
import { coordinateSchema, obstacleCoverSchema } from "./domain";

export const singleTargetRequestSchema = z.object({
  actionId: z.string(),
  combatantId: z.string(),
  targetCombatantId: z.string(),
  rangeCells: z.number().int().positive().nullable(),
  requiresSight: z.boolean().default(false),
  requiresEffect: z.boolean().default(false),
});

export const areaTargetShapeSchema = z.enum(["sphere", "cone", "line", "cube", "cylinder"]);

export const areaTargetRequestSchema = z.object({
  actionId: z.string(),
  combatantId: z.string(),
  shape: areaTargetShapeSchema,
  originCell: coordinateSchema,
  anchorCell: coordinateSchema,
  rangeCells: z.number().int().positive().nullable(),
  sizeCells: z.number().int().positive(),
  requiresSight: z.boolean().default(false),
  requiresEffect: z.boolean().default(false),
});

export const singleTargetResponseSchema = z.object({
  isValid: z.boolean(),
  reason: z.string().nullable(),
  sessionId: z.string(),
  actionId: z.string(),
  version: z.number().int().nonnegative(),
  sourceTokenId: z.string().nullable(),
  targetTokenId: z.string().nullable(),
  distanceCells: z.number().int().nonnegative().nullable().optional(),
  cover: obstacleCoverSchema.default("none"),
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
  affectedCombatantIds: z.array(z.string()),
});

export const areaTargetPreviewResponseSchema = areaTargetResponseSchema;

export const batchTargetingRequestSchema = z.object({
  actionId: z.string(),
  combatantId: z.string(),
  targetCombatantIds: z.array(z.string()),
});

export const batchTargetingResultSchema = z.object({
  targetCombatantId: z.string(),
  cover: obstacleCoverSchema.nullable(),
});

export const batchTargetingResponseSchema = z.object({
  sessionId: z.string(),
  actionId: z.string(),
  version: z.number().int().nonnegative(),
  results: z.array(batchTargetingResultSchema),
});

export type SingleTargetRequest = z.infer<typeof singleTargetRequestSchema>;
export type AreaTargetShape = z.infer<typeof areaTargetShapeSchema>;
export type AreaTargetRequest = z.infer<typeof areaTargetRequestSchema>;
export type SingleTargetResponse = z.infer<typeof singleTargetResponseSchema>;
export type AreaTargetResponse = z.infer<typeof areaTargetResponseSchema>;
export type AreaTargetPreviewResponse = z.infer<typeof areaTargetPreviewResponseSchema>;
export type BatchTargetingRequest = z.infer<typeof batchTargetingRequestSchema>;
export type BatchTargetingResult = z.infer<typeof batchTargetingResultSchema>;
export type BatchTargetingResponse = z.infer<typeof batchTargetingResponseSchema>;
