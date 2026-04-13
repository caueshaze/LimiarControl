import Fastify from "fastify";
import { registerEncounterRoutes } from "./routes/encounter-routes";
import { registerDebugRoutes } from "./routes/debug-routes";
import { InMemoryEncounterRepository } from "./modules/encounters/encounter-repository";

type CreateAppOptions = {
  logger?: boolean;
};

export function createApp(options: CreateAppOptions = {}) {
  const logger = options.logger ?? !process.env.VITEST;
  const app = Fastify({ logger });
  const repository = new InMemoryEncounterRepository();
  registerEncounterRoutes(app, repository);
  registerDebugRoutes(app, repository);
  return { app, repository };
}
