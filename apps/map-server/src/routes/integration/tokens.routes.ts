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

export function registerTokensRoutes(app: FastifyInstance, repository: InMemoryEncounterRepository, broadcaster?: BroadcastAdapter) {
  const initiativeService = new InitiativeService(repository, broadcaster);
  const combatService = new CombatService(repository);

  // Token metadata
  // -------------------------------------------------------------------------

  /**
   * PUT /integration/sessions/:sessionId/tokens
   *
   * Patch token metadata owned by LimiarControl:
   *  - combatantId: links your character/creature ID to a map token
   *  - movementSpeedCells: speed in grid cells (also resets movementBudget to cells * 5)
   *  - controllerId / controllerType: who controls this token on the map
   *
   * All numeric speed values must be in grid cells, not meters.
   * LimiarControl is responsible for converting speedMeters → movementSpeedCells
   * before calling this endpoint (use METERS_PER_CELL = 1.5 as scale).
   *
   * Only provided fields are updated. Unknown tokenIds cause early rejection
   * with the offending ID in the response.
   *
   * Call at session start to link your combatantIds to the GM's map tokens,
   * and again whenever these properties change (e.g. speed bonus mid-combat).
   *
   * Body:   { tokens: [{ tokenId, combatantId?, movementSpeedCells?, ... }] }
   * Returns: IntegrationStateResponse
   */
  app.put("/integration/sessions/:sessionId/tokens", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };

    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = syncTokensRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    request.log.info(
      { sessionId, tokenCount: parse.data.tokens.length },
      `${LOG_PREFIX} PUT tokens`
    );

    const result = initiativeService.syncTokens(sessionId, parse.data.tokens);

    if (!result.accepted) {
      request.log.warn(
        { sessionId, reason: result.reason, tokenId: result.tokenId },
        `${LOG_PREFIX} PUT tokens rejected`
      );
      return reply.status(404).send({
        message: `Token not found: ${result.tokenId}`,
        reason: result.reason,
        tokenId: result.tokenId
      });
    }

    return reply.status(200).send(toIntegrationSnapshot(result.encounter));
  });

}
