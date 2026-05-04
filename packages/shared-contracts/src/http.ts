import { z } from "zod";
import {
  battleMapSchema,
  activeAreaEffectSchema,
  cellElevationSchema,
  combatStateSchema,
  edgeObstacleSchema,
  obstacleSchema,
  tokenSchema
} from "./domain";

export const encounterSnapshotResponseSchema = z.object({
  sessionId: z.string(),
  battleMap: battleMapSchema,
  combatState: combatStateSchema,
  tokens: z.array(tokenSchema),
  obstacles: z.array(obstacleSchema),
  edgeObstacles: z.array(edgeObstacleSchema).default([]),
  activeAreaEffects: z.array(activeAreaEffectSchema).default([]),
  cellElevations: z.array(cellElevationSchema).default([])
});

export const resyncRequestSchema = z.object({
  lastKnownVersion: z.number().int().nonnegative(),
  clientInstanceId: z.string()
});

export const resyncResponseSchema = z.object({
  resynced: z.boolean(),
  snapshotVersion: z.number().int().nonnegative()
});

export type EncounterSnapshotResponse = z.infer<
  typeof encounterSnapshotResponseSchema
>;
export type ResyncRequest = z.infer<typeof resyncRequestSchema>;
export type ResyncResponse = z.infer<typeof resyncResponseSchema>;
