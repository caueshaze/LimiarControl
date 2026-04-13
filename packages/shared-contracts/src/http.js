import { z } from "zod";
import { battleMapSchema, combatStateSchema, obstacleSchema, tokenSchema } from "./domain";
export const encounterSnapshotResponseSchema = z.object({
    sessionId: z.string(),
    battleMap: battleMapSchema,
    combatState: combatStateSchema,
    tokens: z.array(tokenSchema),
    obstacles: z.array(obstacleSchema)
});
export const resyncRequestSchema = z.object({
    lastKnownVersion: z.number().int().nonnegative(),
    clientInstanceId: z.string()
});
export const resyncResponseSchema = z.object({
    resynced: z.boolean(),
    snapshotVersion: z.number().int().nonnegative()
});
