import { randomUUID } from "node:crypto";
import type { FastifyInstance } from "fastify";
import {
  chebyshevDistance,
  evaluateCover,
  hasLineOfEffect,
  hasLineOfSight,
  nextEncounterVersion,
  resolveCone,
  resolveCube,
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

export function registerTargetingRoutes(app: FastifyInstance, repository: InMemoryEncounterRepository, broadcaster?: BroadcastAdapter) {
  const initiativeService = new InitiativeService(repository, broadcaster);
  const combatService = new CombatService(repository);

  // Targeting — single-target range validation
  // -------------------------------------------------------------------------

  /**
   * POST /integration/sessions/:sessionId/targeting
   *
   * Validate a single-target attack or ability.
   *
   * LimiarMap checks:
   *  1. Both combatantIds are linked to tokens on the map
   *  2. Target is within range (if `range` is provided)
   *
   * This endpoint is turn-order agnostic: LimiarControl is trusted to call
   * it regardless of whose turn it is (e.g. reactions, opportunity attacks).
   *
   * Idempotent: repeated calls with the same actionId return the cached result.
   * Broadcasts `targeting.resolved` to all web clients.
   *
   * Body:
   *  {
   *    actionId: string,
   *    combatantId: string,        // attacker
   *    targetCombatantId: string,  // target
   *    range: number | null        // max Chebyshev distance; null = skip check
   *  }
   *
   * Response:
   *  {
   *    isValid: boolean,
   *    reason: string | null,      // null when valid
   *    sessionId: string,
   *    actionId: string,
   *    version: number,
   *    sourceTokenId: string | null,
   *    targetTokenId: string | null
   *  }
   *
   * Note: area/shape targeting (cone, line, sphere, cube) is intentionally
   * deferred to a future endpoint once the single-target flow is stable.
   */
  app.post("/integration/sessions/:sessionId/targeting", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };

    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = singleTargetRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    const { actionId, combatantId, targetCombatantId, rangeCells, requiresSight, requiresEffect } = parse.data;

    // Idempotent — return current version without re-applying
    if (encounter.actionTracker.has(actionId)) {
      request.log.info({ sessionId, actionId }, `${LOG_PREFIX} targeting duplicate_action`);
      return reply.status(200).send({
        isValid: true,
        reason: null,
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: null,
        targetTokenId: null
      });
    }

    // Resolve source token
    const sourceToken = encounter.tokens.find((t) => t.combatantId === combatantId);
    if (!sourceToken) {
      const unlinked = encounter.tokens.find((t) => t.id === combatantId);
      const reason = unlinked ? "token_not_linked" : "unknown_combatant";
      const message =
        unlinked
          ? `Token exists but has no combatantId assigned (tokenId=${combatantId})`
          : `No token is linked to combatantId=${combatantId}`;

      request.log.warn({ sessionId, combatantId, reason }, `${LOG_PREFIX} targeting rejected`);
      return reply.status(200).send({
        isValid: false,
        reason,
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: null,
        targetTokenId: null
      });
    }

    // Resolve target token
    const targetToken = encounter.tokens.find((t) => t.combatantId === targetCombatantId);
    if (!targetToken) {
      const unlinked = encounter.tokens.find((t) => t.id === targetCombatantId);
      const reason = unlinked ? "token_not_linked" : "unknown_combatant";
      const message =
        unlinked
          ? `Target token exists but has no combatantId assigned (tokenId=${targetCombatantId})`
          : `No token is linked to targetCombatantId=${targetCombatantId}`;

      request.log.warn(
        { sessionId, targetCombatantId, reason },
        `${LOG_PREFIX} targeting rejected`
      );
      return reply.status(200).send({
        isValid: false,
        reason,
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: null
      });
    }

    // Range validation (rangeCells is in grid cells, Chebyshev distance)
    if (rangeCells !== null) {
      const distance = chebyshevDistance(sourceToken.position, targetToken.position);
      if (distance > rangeCells) {
        request.log.info(
          { sessionId, combatantId, targetCombatantId, distance, rangeCells },
          `${LOG_PREFIX} targeting out_of_range`
        );
        return reply.status(200).send({
          isValid: false,
          reason: "out_of_range",
          sessionId,
          actionId,
          version: encounter.combatState.version,
          sourceTokenId: sourceToken.id,
          targetTokenId: targetToken.id
        });
      }
    }

    // Line of sight — obstacle with blocksVision between source and target
    if (requiresSight && !hasLineOfSight(encounter.obstacles, sourceToken.position, targetToken.position)) {
      request.log.info(
        { sessionId, combatantId, targetCombatantId },
        `${LOG_PREFIX} targeting no_line_of_sight`
      );
      return reply.status(200).send({
        isValid: false,
        reason: "no_line_of_sight",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id
      });
    }

    // Line of effect — obstacle with blocksEffect between source and target
    if (requiresEffect && !hasLineOfEffect(encounter.obstacles, sourceToken.position, targetToken.position)) {
      request.log.info(
        { sessionId, combatantId, targetCombatantId },
        `${LOG_PREFIX} targeting no_line_of_effect`
      );
      return reply.status(200).send({
        isValid: false,
        reason: "no_line_of_effect",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id
      });
    }

    // Cover evaluation — independent of LoS/LoE, evaluated after hard checks pass
    const cover = evaluateCover(encounter.obstacles, sourceToken.position, targetToken.position);

    // Full cover invalidates direct targeted attacks
    if (cover === "full") {
      request.log.info(
        { sessionId, combatantId, targetCombatantId, cover },
        `${LOG_PREFIX} targeting full_cover`
      );
      return reply.status(200).send({
        isValid: false,
        reason: "full_cover",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id,
        cover
      });
    }

    // Accept — record action and bump version
    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };
    repository.updateCombatState(sessionId, encounter.combatState);

    const newVersion = encounter.combatState.version;

    request.log.info(
      {
        sessionId,
        combatantId,
        targetCombatantId,
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id,
        rangeCells,
        cover,
        version: newVersion
      },
      `${LOG_PREFIX} targeting accepted`
    );

    broadcastAuthoritativeEvent(broadcaster, "targeting.resolved", {
      eventId: randomUUID(),
      eventType: "targeting.resolved",
      encounterId: sessionId,
      version: newVersion,
      actionId,
      payload: {
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id,
        isValid: true,
        reason: null,
        cover
      },
      replaySafe: true
    });

    return reply.status(200).send({
      isValid: true,
      reason: null,
      sessionId,
      actionId,
      version: newVersion,
      sourceTokenId: sourceToken.id,
      targetTokenId: targetToken.id,
      cover
    });
  });

  app.post("/integration/sessions/:sessionId/targeting/area", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };

    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = areaTargetRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    const { actionId, combatantId, shape, originCell, anchorCell, rangeCells, sizeCells, requiresSight, requiresEffect } = parse.data;
    const sourceToken = encounter.tokens.find((candidate) => candidate.combatantId === combatantId);
    if (!sourceToken) {
      const unlinked = encounter.tokens.find((candidate) => candidate.id === combatantId);
      const reason = unlinked ? "token_not_linked" : "unknown_combatant";
      request.log.warn({ sessionId, combatantId, reason }, `${LOG_PREFIX} area targeting rejected`);
      return reply.status(200).send({
        isValid: false,
        reason,
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: null,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    const gridWidth = encounter.battleMap.gridWidth;
    const gridHeight = encounter.battleMap.gridHeight;
    if (
      originCell.x >= gridWidth ||
      originCell.y >= gridHeight ||
      originCell.x < 0 ||
      originCell.y < 0
    ) {
      return reply.status(200).send({
        isValid: false,
        reason: "invalid_origin",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }
    if (
      anchorCell.x >= gridWidth ||
      anchorCell.y >= gridHeight ||
      anchorCell.x < 0 ||
      anchorCell.y < 0
    ) {
      return reply.status(200).send({
        isValid: false,
        reason: "invalid_anchor",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    // effectiveRange: falls back to distance between origin and anchor if rangeCells is null (line shape only)
    const effectiveRange = rangeCells ?? Math.max(chebyshevDistance(originCell, anchorCell), 1);
    if (rangeCells !== null && chebyshevDistance(originCell, anchorCell) > rangeCells) {
      request.log.info(
        { sessionId, combatantId, shape, rangeCells, originCell, anchorCell },
        `${LOG_PREFIX} area targeting out_of_range`
      );
      return reply.status(200).send({
        isValid: false,
        reason: "out_of_range",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    // Line of sight — obstacle with blocksVision between origin and anchor
    if (requiresSight && !hasLineOfSight(encounter.obstacles, originCell, anchorCell)) {
      return reply.status(200).send({
        isValid: false,
        reason: "no_line_of_sight",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    // Line of effect — obstacle with blocksEffect between origin and anchor
    if (requiresEffect && !hasLineOfEffect(encounter.obstacles, originCell, anchorCell)) {
      return reply.status(200).send({
        isValid: false,
        reason: "no_line_of_effect",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    // All dimensions here are in grid cells (already converted by LimiarControl at the boundary).
    const resolveAffectedCells = () => {
      switch (shape) {
        case "cone":
          return resolveCone(originCell, anchorCell, sizeCells, encounter.obstacles);
        case "line":
          return resolveLine(originCell, anchorCell, effectiveRange, encounter.obstacles);
        case "sphere":
          return resolveSphere(anchorCell, sizeCells, encounter.obstacles);
        case "cube":
          return resolveCube(anchorCell, sizeCells, encounter.obstacles);
      }
    };

    const affectedCells = resolveAffectedCells();
    const affectedCellKeySet = new Set(affectedCells.map((cell) => `${cell.x}:${cell.y}`));
    const affectedTokens = encounter.tokens.filter((token) =>
      affectedCellKeySet.has(`${token.position.x}:${token.position.y}`)
    );
    const affectedCombatantIds = [
      ...new Set(
        affectedTokens
          .map((token) => token.combatantId)
          .filter((combatantId): combatantId is string => typeof combatantId === "string" && combatantId.length > 0)
      ),
    ];

    if (encounter.actionTracker.has(actionId)) {
      request.log.info({ sessionId, actionId, shape }, `${LOG_PREFIX} area targeting duplicate_action`);
      return reply.status(200).send({
        isValid: true,
        reason: null,
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells,
        affectedTokenIds: affectedTokens.map((token) => token.id),
        affectedCombatantIds
      });
    }

    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version)
    };
    repository.updateCombatState(sessionId, encounter.combatState);

    request.log.info(
      {
        sessionId,
        actionId,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: affectedCells.length,
        affectedCombatants: affectedCombatantIds.length,
        version: encounter.combatState.version
      },
      `${LOG_PREFIX} area targeting accepted`
    );

    broadcastAuthoritativeEvent(broadcaster, "targeting.resolved", {
      eventId: randomUUID(),
      eventType: "targeting.resolved",
      encounterId: sessionId,
      version: encounter.combatState.version,
      actionId,
      payload: {
        tokenId: sourceToken.id,
        shape,
        affectedCells,
        affectedTokenIds: affectedTokens.map((token) => token.id),
        affectedCombatantIds,
        isValid: true,
        reason: null
      },
      replaySafe: true
    });

    return reply.status(200).send({
      isValid: true,
      reason: null,
      sessionId,
      actionId,
      version: encounter.combatState.version,
      shape,
      sourceTokenId: sourceToken.id,
      affectedCells,
      affectedTokenIds: affectedTokens.map((token) => token.id),
      affectedCombatantIds
    });
  });

  app.post("/integration/sessions/:sessionId/targeting/area/preview", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };

    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = areaTargetRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    const {
      actionId,
      combatantId,
      shape,
      originCell,
      anchorCell,
      rangeCells,
      sizeCells,
      requiresSight,
      requiresEffect
    } = parse.data;
    const sourceToken = encounter.tokens.find((candidate) => candidate.combatantId === combatantId);
    if (!sourceToken) {
      const unlinked = encounter.tokens.find((candidate) => candidate.id === combatantId);
      const reason = unlinked ? "token_not_linked" : "unknown_combatant";
      return reply.status(200).send({
        isValid: false,
        reason,
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: null,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    const gridWidth = encounter.battleMap.gridWidth;
    const gridHeight = encounter.battleMap.gridHeight;
    if (
      originCell.x >= gridWidth ||
      originCell.y >= gridHeight ||
      originCell.x < 0 ||
      originCell.y < 0
    ) {
      return reply.status(200).send({
        isValid: false,
        reason: "invalid_origin",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }
    if (
      anchorCell.x >= gridWidth ||
      anchorCell.y >= gridHeight ||
      anchorCell.x < 0 ||
      anchorCell.y < 0
    ) {
      return reply.status(200).send({
        isValid: false,
        reason: "invalid_anchor",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    const effectiveRange = rangeCells ?? Math.max(chebyshevDistance(originCell, anchorCell), 1);
    if (rangeCells !== null && chebyshevDistance(originCell, anchorCell) > rangeCells) {
      return reply.status(200).send({
        isValid: false,
        reason: "out_of_range",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    if (requiresSight && !hasLineOfSight(encounter.obstacles, originCell, anchorCell)) {
      return reply.status(200).send({
        isValid: false,
        reason: "no_line_of_sight",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    if (requiresEffect && !hasLineOfEffect(encounter.obstacles, originCell, anchorCell)) {
      return reply.status(200).send({
        isValid: false,
        reason: "no_line_of_effect",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: []
      });
    }

    // All dimensions here are in grid cells (already converted by LimiarControl at the boundary).
    const affectedCells =
      shape === "cone"
        ? resolveCone(originCell, anchorCell, sizeCells, encounter.obstacles)
        : shape === "line"
          ? resolveLine(originCell, anchorCell, effectiveRange, encounter.obstacles)
          : shape === "cube"
            ? resolveCube(anchorCell, sizeCells, encounter.obstacles)
            : resolveSphere(anchorCell, sizeCells, encounter.obstacles);
    const affectedCellKeySet = new Set(affectedCells.map((cell) => `${cell.x}:${cell.y}`));
    const affectedTokens = encounter.tokens.filter((token) =>
      affectedCellKeySet.has(`${token.position.x}:${token.position.y}`)
    );
    const affectedCombatantIds = [
      ...new Set(
        affectedTokens
          .map((token) => token.combatantId)
          .filter((combatantId): combatantId is string => typeof combatantId === "string" && combatantId.length > 0)
      ),
    ];

    request.log.info(
      {
        sessionId,
        actionId,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: affectedCells.length,
        affectedCombatants: affectedCombatantIds.length,
        version: encounter.combatState.version
      },
      `${LOG_PREFIX} area targeting preview`
    );

    return reply.status(200).send({
      isValid: true,
      reason: null,
      sessionId,
      actionId,
      version: encounter.combatState.version,
      shape,
      sourceTokenId: sourceToken.id,
      affectedCells,
      affectedTokenIds: affectedTokens.map((token) => token.id),
      affectedCombatantIds
    });

  });
}