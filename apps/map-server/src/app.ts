import Fastify from "fastify";
import { registerEncounterRoutes } from "./routes/encounter-routes";
import { registerDebugRoutes } from "./routes/debug-routes";
import { InMemoryEncounterRepository } from "./modules/encounters/encounter-repository";

export function createApp() {
  const app = Fastify({ logger: true });
  const repository = new InMemoryEncounterRepository();
  registerEncounterRoutes(app, repository);
  registerDebugRoutes(app, repository);
  return { app, repository };
}
