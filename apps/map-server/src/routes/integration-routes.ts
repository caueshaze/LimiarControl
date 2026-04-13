import { registerStateRoutes } from "./integration/state.routes";
import { registerInitiativeRoutes } from "./integration/initiative.routes";
import { registerTokensRoutes } from "./integration/tokens.routes";
import { registerTargetingRoutes } from "./integration/targeting.routes";
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
import type { InMemoryEncounterRepository } from "../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../modules/realtime/broadcast";
import { CombatService } from "../modules/combat/combat-service";
import { InitiativeService } from "../modules/integration/initiative-service";
import {
  toEncounterSnapshot,
  toIntegrationSnapshot
} from "../modules/encounters/encounter-snapshot";

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
// Route registration
// ---------------------------------------------------------------------------

/**
 * Integration API — all routes under /integration/
 *
 * Designed for server-to-server communication with LimiarControl.
 * Authentication is delegated to LimiarControl's layer (reverse-proxy or
 * API gateway). These endpoints MUST NOT be publicly exposed.
 *
 * Contract guarantees:
 *  - Every request body is validated with Zod; invalid bodies → 400
 *  - Every mutating action is idempotent via actionId → repeated calls → 200
 *  - Every state-mutating response includes `version` at the top level
 *  - Every HTTP error follows { message: string, reason: string }
 *  - Every Centrifugo event triggered by these endpoints carries `version`
 *
 * Error `reason` codes:
 *  session_not_found        | Session / encounter does not exist
 *  duplicate_action         | actionId was already processed (idempotent 200)
 *  combat_already_active    | Cannot start; combat is already running
 *  combat_not_active        | Cannot advance/end; combat is not active
 *  unknown_token            | tokenId not found in this session
 *  unknown_combatant        | No token linked to that combatantId
 *  token_not_linked         | Token exists but has no combatantId assigned
 *  out_of_range             | Target is beyond the provided range
 *  unauthorized_action      | Action not permitted (e.g. non-limiarControl advance)
 */
export function registerIntegrationRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository,
  broadcaster?: BroadcastAdapter
): void {
  const initiativeService = new InitiativeService(repository, broadcaster);
  const combatService = new CombatService(repository);


  registerStateRoutes(app, repository, broadcaster);
  registerInitiativeRoutes(app, repository, broadcaster);
  registerTokensRoutes(app, repository, broadcaster);
  registerTargetingRoutes(app, repository, broadcaster);
}
