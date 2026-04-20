import { randomUUID } from "node:crypto";
import type { FastifyInstance } from "fastify";
import {
  chebyshevDistance,
  evaluateCover,
  hasLineOfEffect,
  hasLineOfSight,
  nextEncounterVersion,
} from "@limiarmap/tactical-engine";
import { singleTargetRequestSchema } from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../../modules/realtime/broadcast";
import { err } from "./targeting.helpers";

const LOG_PREFIX = "[integration]";

export function registerSingleTargetingRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository,
  broadcaster?: BroadcastAdapter,
) {
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
    if (encounter.actionTracker.has(actionId)) {
      request.log.info({ sessionId, actionId }, `${LOG_PREFIX} targeting duplicate_action`);
      return reply.status(200).send({
        isValid: true,
        reason: null,
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: null,
        targetTokenId: null,
        distanceCells: null,
      });
    }

    const sourceToken = encounter.tokens.find((token) => token.combatantId === combatantId);
    if (!sourceToken) {
      const unlinked = encounter.tokens.find((token) => token.id === combatantId);
      return reply.status(200).send({
        isValid: false,
        reason: unlinked ? "token_not_linked" : "unknown_combatant",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: null,
        targetTokenId: null,
        distanceCells: null,
      });
    }

    const targetToken = encounter.tokens.find((token) => token.combatantId === targetCombatantId);
    if (!targetToken) {
      const unlinked = encounter.tokens.find((token) => token.id === targetCombatantId);
      return reply.status(200).send({
        isValid: false,
        reason: unlinked ? "token_not_linked" : "unknown_combatant",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: null,
        distanceCells: null,
      });
    }

    const distance = chebyshevDistance(sourceToken.position, targetToken.position);
    if (rangeCells !== null && distance > rangeCells) {
      return reply.status(200).send({
        isValid: false,
        reason: "out_of_range",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id,
        distanceCells: distance,
      });
    }
    if (requiresSight && !hasLineOfSight(encounter.obstacles, sourceToken.position, targetToken.position, encounter.edgeObstacles)) {
      return reply.status(200).send({
        isValid: false,
        reason: "no_line_of_sight",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id,
        distanceCells: distance,
      });
    }
    if (requiresEffect && !hasLineOfEffect(encounter.obstacles, sourceToken.position, targetToken.position, encounter.edgeObstacles)) {
      return reply.status(200).send({
        isValid: false,
        reason: "no_line_of_effect",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id,
        distanceCells: distance,
      });
    }

    const cover = evaluateCover(encounter.obstacles, sourceToken.position, targetToken.position, encounter.edgeObstacles);
    if (cover === "full") {
      return reply.status(200).send({
        isValid: false,
        reason: "full_cover",
        sessionId,
        actionId,
        version: encounter.combatState.version,
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id,
        distanceCells: distance,
        cover,
      });
    }

    encounter.actionTracker.record(actionId);
    encounter.combatState = {
      ...encounter.combatState,
      version: nextEncounterVersion(encounter.combatState.version),
    };
    repository.updateCombatState(sessionId, encounter.combatState);

    broadcastAuthoritativeEvent(broadcaster, "targeting.resolved", {
      eventId: randomUUID(),
      eventType: "targeting.resolved",
      encounterId: sessionId,
      version: encounter.combatState.version,
      actionId,
      payload: {
        sourceTokenId: sourceToken.id,
        targetTokenId: targetToken.id,
        isValid: true,
        reason: null,
        cover,
      },
      replaySafe: true,
    });

    return reply.status(200).send({
      isValid: true,
      reason: null,
      sessionId,
      actionId,
      version: encounter.combatState.version,
      sourceTokenId: sourceToken.id,
      targetTokenId: targetToken.id,
      distanceCells: distance,
      cover,
    });
  });
}
