import { z } from "zod";
import { coordinateSchema, obstacleCoverSchema, tokenSchema } from "./domain";
import { areaTargetShapeSchema } from "./integration.targeting";

export * from "./integration.combat";
export * from "./integration.targeting";

export const integrationErrorResponseSchema = z.object({
  message: z.string(),
  reason: z.string(),
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
  "grid.calibration.updated",
  "elevation.updated",
]);

export const integrationSpatialEventEnvelopeSchema = z.object({
  eventId: z.string(),
  eventType: integrationSpatialEventTypeSchema,
  encounterId: z.string(),
  version: z.number().int().nonnegative(),
  actionId: z.string().optional(),
  payload: z.record(z.unknown()),
  replaySafe: z.boolean().default(true),
});

export const combatStartedPayloadSchema = z.object({
  roundNumber: z.number().int().nonnegative(),
  turnIndex: z.number().int().nonnegative(),
  activeCombatantId: z.string().nullable(),
  initiativeOrder: z.array(z.string()),
});

export const combatEndedPayloadSchema = z.object({
  roundNumber: z.number().int().nonnegative(),
});

export const initiativeUpdatedPayloadSchema = z.object({
  initiativeOrder: z.array(z.string()),
  activeCombatantId: z.string().nullable(),
  turnIndex: z.number().int().nonnegative(),
});

export const tokensSyncedPayloadSchema = z.object({
  tokens: z.array(tokenSchema),
});

export const singleTargetResolvedPayloadSchema = z.object({
  sourceTokenId: z.string(),
  targetTokenId: z.string(),
  isValid: z.boolean(),
  reason: z.string().nullable(),
  cover: obstacleCoverSchema.default("none"),
});

export const areaTargetResolvedPayloadSchema = z.object({
  sourceTokenId: z.string(),
  shape: areaTargetShapeSchema,
  affectedCells: z.array(coordinateSchema),
  affectedTokenIds: z.array(z.string()),
  affectedCombatantIds: z.array(z.string()),
  isValid: z.boolean(),
  reason: z.string().nullable(),
});

export type IntegrationErrorResponse = z.infer<typeof integrationErrorResponseSchema>;
export type IntegrationSpatialEventType = z.infer<typeof integrationSpatialEventTypeSchema>;
export type IntegrationSpatialEventEnvelope = z.infer<typeof integrationSpatialEventEnvelopeSchema>;
export type CombatStartedPayload = z.infer<typeof combatStartedPayloadSchema>;
export type CombatEndedPayload = z.infer<typeof combatEndedPayloadSchema>;
export type InitiativeUpdatedPayload = z.infer<typeof initiativeUpdatedPayloadSchema>;
export type TokensSyncedPayload = z.infer<typeof tokensSyncedPayloadSchema>;
export type SingleTargetResolvedPayload = z.infer<typeof singleTargetResolvedPayloadSchema>;
export type AreaTargetResolvedPayload = z.infer<typeof areaTargetResolvedPayloadSchema>;
