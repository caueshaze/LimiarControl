import type { FastifyInstance } from "fastify";
import type { InMemoryEncounterRepository } from "../modules/encounters/encounter-repository";

export function registerDebugRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository
): void {
  app.post("/debug/sessions/:sessionId/reset-budgets", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return reply.status(404).send({ message: "Encounter not found" });
    }

    for (const token of encounter.tokens) {
      repository.resetTokenBudget(sessionId, token.id);
    }

    return reply.send({ reset: true, sessionId });
  });
}
