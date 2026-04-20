import type { FastifyInstance } from "fastify";
import type { InMemoryEncounterRepository } from "../../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../../modules/realtime/broadcast";
import { registerAreaTargetingRoutes } from "./targeting.area.routes";
import { registerSingleTargetingRoutes } from "./targeting.single.routes";

export function registerTargetingRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository,
  broadcaster?: BroadcastAdapter,
) {
  registerSingleTargetingRoutes(app, repository, broadcaster);
  registerAreaTargetingRoutes(app, repository, broadcaster);
}
