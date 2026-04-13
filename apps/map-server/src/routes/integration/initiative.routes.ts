import { randomUUID } from "node:crypto";
import type { FastifyInstance } from "fastify";
import {
  chebyshevDistance,
  hasLineOfEffect,
  hasLineOfSight,
  nextEncounterVersion,
  resolveCone,
  resolveLine,
  resolveSphere
} from "@limiarmap/tactical-engine";
import {
  areaTargetRequestSchema,
  advanceTurnRequestSchema,
  endCombatRequestSchema,
  setInitiativeRequestSchema,
  singleTargetRequestSchema,
  startCombatRequestSchema,
  syncTokensRequestSchema
} from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../../modules/realtime/broadcast";
import { CombatService } from "../../modules/combat/combat-service";
import { InitiativeService } from "../../modules/integration/initiative-service";
import {
  toEncounterSnapshot,
  toIntegrationSnapshot
} from "../../modules/encounters/encounter-snapshot";

const LOG_PREFIX = "[integration]";

// ---------------------------------------------------------------------------
// Error helper
// ---------------------------------------------------------------------------

type Reply = {
  status(code: number): { send(payload: unknown): unknown };
};

/** Uniform error shape: { message, reason }.  Used by every integration endpoint. */
function err(reply: Reply, status: number, reason: string, message: string) {
  return reply.status(status).send({ message, reason });
}

// ---------------------------------------------------------------------------
// Route handler injection
// ---------------------------------------------------------------------------

export function registerInitiativeRoutes(app: FastifyInstance, repository: InMemoryEncounterRepository, broadcaster?: BroadcastAdapter) {
  const initiativeService = new InitiativeService(repository, broadcaster);
  const combatService = new CombatService(repository);

  // -------------------------------------------------------------------------
  // Initiative management
  // -------------------------------------------------------------------------

  /**
   * PUT /integration/sessions/:sessionId/initiative
   *
   * Replace the full initiative order at any point (before or during combat).
   * Safe mid-combat: the current active combatant's position is preserved
   * when possible; otherwise the highest-scoring combatant becomes active.
   *
   * Use this when initiative is rerolled, a surprise round ends, or new
   * combatants join mid-encounter.
   *
   * Body:   { actionId, combatants: [{ combatantId, initiativeScore }] }
   * Returns: IntegrationStateResponse
   */
  app.put("/integration/sessions/:sessionId/initiative", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };

    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = setInitiativeRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    request.log.info(
      { sessionId, actionId: parse.data.actionId, combatants: parse.data.combatants.length },
      `${LOG_PREFIX} PUT initiative`
    );

    const result = initiativeService.setInitiative(
      sessionId,
      parse.data.actionId,
      parse.data.combatants
    );

    if (!result.accepted) {
      // setInitiative only rejects on duplicate_action — return current state (idempotent)
      return reply.status(200).send(toIntegrationSnapshot(encounter));
    }

    return reply.status(200).send(toIntegrationSnapshot(result.encounter));
  });


}
