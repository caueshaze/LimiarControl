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

export function registerStateRoutes(app: FastifyInstance, repository: InMemoryEncounterRepository, broadcaster?: BroadcastAdapter) {
  const initiativeService = new InitiativeService(repository, broadcaster);
  const combatService = new CombatService(repository);

  // -------------------------------------------------------------------------
  // Read
  // -------------------------------------------------------------------------

  /**
   * GET /integration/sessions/:sessionId/state
   *
   * Returns the authoritative encounter snapshot.
   * Use this to bootstrap LimiarControl's local state or to verify sync.
   *
   * The `version` field at the top level is the primary sync indicator.
   * If your local version is behind this value, re-read the full state.
   */
  app.get("/integration/sessions/:sessionId/state", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    request.log.info({ sessionId }, `${LOG_PREFIX} GET state`);

    const encounter = repository.ensureEncounter(sessionId);
    return reply.send(toIntegrationSnapshot(encounter));
  });

  // -------------------------------------------------------------------------
  // Combat lifecycle
  // -------------------------------------------------------------------------

  /**
   * POST /integration/sessions/:sessionId/combat/start
   *
   * Begin combat. LimiarControl provides the combatants sorted by initiative
   * score (highest acts first). LimiarMap sets status → "active", round 1.
   *
   * Also valid after a "completed" combat — allows restarting an encounter.
   * Idempotent on same actionId.
   *
   * Body:   { actionId, combatants: [{ combatantId, initiativeScore }] }
   * Returns: IntegrationStateResponse (with top-level version)
   */
  app.post("/integration/sessions/:sessionId/combat/start", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };

    const parse = startCombatRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    const battleMapSeed = parse.data.battleMap
      ? {
          name: parse.data.battleMap.name,
          gridWidth: parse.data.battleMap.gridWidth,
          gridHeight: parse.data.battleMap.gridHeight,
          gridCalibration: parse.data.battleMap.gridCalibration,
          imageUrl: parse.data.battleMap.imageUrl,
          sourceImageUrl: parse.data.battleMap.sourceImageUrl ?? null
        }
      : undefined;
    const existingEncounter = repository.getEncounter(sessionId);
    const isDuplicateAction = existingEncounter?.actionTracker.has(parse.data.actionId) ?? false;
    const encounter = !existingEncounter
      ? repository.createEncounter(sessionId, battleMapSeed)
      : battleMapSeed && !isDuplicateAction
        ? repository.updateBattleMap(sessionId, battleMapSeed)
        : existingEncounter;

    if (battleMapSeed && !isDuplicateAction) {
      const { gridWidth, gridHeight } = parse.data.battleMap!;
      const seen = new Set<string>();

      if (parse.data.battleMap?.obstacles?.length) {
        // Canonical semantic path: each entry carries full tactical semantics.
        const battleMapId = encounter.battleMap.id;
        const campaignObstacles = parse.data.battleMap.obstacles
          .filter((obs) => {
            if (obs.x < 0 || obs.y < 0 || obs.x >= gridWidth || obs.y >= gridHeight) return false;
            const key = `${obs.x}:${obs.y}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          })
          .map((obs, index) => ({
            id: `campaign-obstacle-${index}`,
            battleMapId,
            cells: [{ x: obs.x, y: obs.y }],
            blocksMovement: obs.blocksMovement,
            blocksEffect: obs.blocksEffect,
            blocksVision: obs.blocksVision,
            cover: obs.cover,
            clipsDiagonalMovement: obs.clipsDiagonalMovement,
            movementCostMultiplier: obs.movementCostMultiplier
          }));
        repository.setObstacles(sessionId, campaignObstacles);
      } else if (parse.data.battleMap?.blockedCells?.length) {
        // Legacy path: movement-only blocked cells become solid obstacles.
        const validCells = parse.data.battleMap.blockedCells.filter((cell) => {
          if (cell.x < 0 || cell.y < 0 || cell.x >= gridWidth || cell.y >= gridHeight) return false;
          const key = `${cell.x}:${cell.y}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
        const battleMapId = encounter.battleMap.id;
        const campaignObstacles = validCells.map((cell, index) => ({
          id: `campaign-obstacle-${index}`,
          battleMapId,
          label: "Terreno bloqueado",
          cells: [cell],
          blocksMovement: true,
          blocksEffect: true,
          blocksVision: true,
          cover: "none" as const,
          clipsDiagonalMovement: false,
          movementCostMultiplier: 1
        }));
        repository.setObstacles(sessionId, campaignObstacles);
      }

      if (parse.data.battleMap?.edgeObstacles?.length) {
        const battleMapId = encounter.battleMap.id;
        const seenEdges = new Set<string>();
        const campaignEdgeObstacles = parse.data.battleMap.edgeObstacles
          .filter((edge) => {
            if (edge.x < 0 || edge.y < 0 || edge.x >= gridWidth || edge.y >= gridHeight) {
              return false;
            }
            const key = `${edge.x}:${edge.y}:${edge.direction}`;
            if (seenEdges.has(key)) return false;
            seenEdges.add(key);
            return true;
          })
          .map((edge, index) => ({
            id: `campaign-edge-obstacle-${index}`,
            battleMapId,
            x: edge.x,
            y: edge.y,
            direction: edge.direction,
            blocksMovement: edge.blocksMovement,
            blocksVision: edge.blocksVision,
            blocksEffect: edge.blocksEffect,
            cover: edge.cover
          }));
        repository.setEdgeObstacles(sessionId, campaignEdgeObstacles);
      } else {
        repository.setEdgeObstacles(sessionId, []);
      }
    }

    request.log.info(
      { sessionId, actionId: parse.data.actionId, combatants: parse.data.combatants.length },
      `${LOG_PREFIX} POST combat/start`
    );

    const result = initiativeService.startCombat(sessionId, parse.data.actionId, parse.data.combatants);

    if (!result.accepted) {
      // duplicate_action is idempotent — return current state as 200
      if (result.reason === "duplicate_action") {
        return reply.status(200).send(toIntegrationSnapshot(encounter));
      }
      return err(reply, 409, result.reason, `Cannot start combat: ${result.reason}`);
    }

    return reply.status(200).send(toIntegrationSnapshot(result.encounter));
  });

  /**
   * POST /integration/sessions/:sessionId/combat/advance
   *
   * Move to the next turn. Wraps the round counter when the last combatant
   * acts. Resets the new active token's movement budget.
   *
   * Broadcasts `combat.advanced` to all web clients via Centrifugo.
   *
   * Body:   { actionId }
   * Returns: IntegrationStateResponse
   */
  app.post("/integration/sessions/:sessionId/combat/advance", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };

    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = advanceTurnRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    request.log.info(
      { sessionId, actionId: parse.data.actionId },
      `${LOG_PREFIX} POST combat/advance`
    );

    const result = combatService.advance(sessionId, parse.data.actionId, "limiarControl");

    if (!result.accepted) {
      if (result.rejectionReason === "duplicate_action") {
        return reply.status(200).send(toIntegrationSnapshot(encounter));
      }
      request.log.warn(
        { sessionId, reason: result.rejectionReason },
        `${LOG_PREFIX} combat/advance rejected`
      );
      return err(
        reply,
        409,
        result.rejectionReason ?? "unknown",
        `Cannot advance combat: ${result.rejectionReason}`
      );
    }

    broadcastAuthoritativeEvent(broadcaster, "combat.advanced", {
      eventId: randomUUID(),
      eventType: "combat.advanced",
      encounterId: sessionId,
      version: result.encounter.combatState.version,
      actionId: parse.data.actionId,
      payload: {
        roundNumber: result.encounter.combatState.roundNumber,
        turnIndex: result.encounter.combatState.turnIndex,
        activeCombatantId: result.encounter.combatState.activeCombatantId
      },
      replaySafe: true
    });

    return reply.status(200).send(toIntegrationSnapshot(result.encounter));
  });

  /**
   * POST /integration/sessions/:sessionId/combat/end
   *
   * Conclude combat. Sets status → "completed" and clears the active combatant.
   * Broadcasts `combat.ended` to all web clients.
   *
   * Body:   { actionId }
   * Returns: IntegrationStateResponse
   */
  app.post("/integration/sessions/:sessionId/combat/end", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };

    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = endCombatRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    request.log.info({ sessionId, actionId: parse.data.actionId }, `${LOG_PREFIX} POST combat/end`);

    const result = initiativeService.endCombat(sessionId, parse.data.actionId);

    if (!result.accepted) {
      // endCombat only rejects on duplicate_action — return current state (idempotent)
      return reply.status(200).send(toIntegrationSnapshot(encounter));
    }

    return reply.status(200).send(toIntegrationSnapshot(result.encounter));
  });

}
