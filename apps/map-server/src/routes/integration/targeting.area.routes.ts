import { randomUUID } from "node:crypto";
import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import {
  chebyshevDistance,
  evaluateLineOfSight,
  hasLineOfEffect,
  nextEncounterVersion
} from "@limiarmap/tactical-engine";
import { areaTargetRequestSchema } from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../../modules/realtime/broadcast";
import {
  buildAreaRejection,
  err,
  isCellInsideMap,
  resolveAreaTargeting
} from "./targeting.helpers";

const LOG_PREFIX = "[integration]";

async function handleAreaRoute(
  request: FastifyRequest,
  reply: FastifyReply,
  repository: InMemoryEncounterRepository,
  broadcaster: BroadcastAdapter | undefined,
  mutateState: boolean
) {
  const { sessionId } = request.params as { sessionId: string };
  const encounter = repository.getEncounter(sessionId);
  if (!encounter) {
    return err(reply, 404, "session_not_found", "Session not found");
  }

  const parse = areaTargetRequestSchema.safeParse(request.body);
  if (!parse.success) {
    return reply
      .status(400)
      .send({ message: "Invalid request body", errors: parse.error.errors });
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
  const sourceToken = encounter.tokens.find(
    (candidate) => candidate.combatantId === combatantId
  );
  if (!sourceToken) {
    const unlinked = encounter.tokens.find(
      (candidate) => candidate.id === combatantId
    );
    return reply
      .status(200)
      .send(
        buildAreaRejection(
          encounter,
          sessionId,
          actionId,
          shape,
          unlinked ? "token_not_linked" : "unknown_combatant",
          null
        )
      );
  }
  if (!isCellInsideMap(encounter, originCell)) {
    return reply
      .status(200)
      .send(
        buildAreaRejection(
          encounter,
          sessionId,
          actionId,
          shape,
          "invalid_origin",
          sourceToken.id
        )
      );
  }
  if (!isCellInsideMap(encounter, anchorCell)) {
    return reply
      .status(200)
      .send(
        buildAreaRejection(
          encounter,
          sessionId,
          actionId,
          shape,
          "invalid_anchor",
          sourceToken.id
        )
      );
  }
  if (
    rangeCells !== null &&
    chebyshevDistance(originCell, anchorCell) > rangeCells
  ) {
    return reply
      .status(200)
      .send(
        buildAreaRejection(
          encounter,
          sessionId,
          actionId,
          shape,
          "out_of_range",
          sourceToken.id
        )
      );
  }
  if (requiresSight) {
    const sight = evaluateLineOfSight(
      encounter.obstacles,
      originCell,
      anchorCell,
      encounter.edgeObstacles,
      encounter.activeAreaEffects
    );
    if (!sight.ok) {
      // Area targeting selects a point, not a creature: remap target reason.
      const reason =
        sight.reason === "target_heavily_obscured"
          ? "point_heavily_obscured"
          : sight.reason;
      return reply
        .status(200)
        .send(
          buildAreaRejection(
            encounter,
            sessionId,
            actionId,
            shape,
            reason,
            sourceToken.id
          )
        );
    }
  }
  if (
    requiresEffect &&
    !hasLineOfEffect(
      encounter.obstacles,
      originCell,
      anchorCell,
      encounter.edgeObstacles
    )
  ) {
    return reply
      .status(200)
      .send(
        buildAreaRejection(
          encounter,
          sessionId,
          actionId,
          shape,
          "no_line_of_effect",
          sourceToken.id
        )
      );
  }

  const resolved = resolveAreaTargeting(encounter, {
    anchorCell,
    originCell,
    rangeCells,
    shape,
    sizeCells
  });

  if (!mutateState) {
    request.log.info(
      {
        sessionId,
        actionId,
        shape,
        sourceTokenId: sourceToken.id,
        affectedCells: resolved.affectedCells.length,
        affectedCombatants: resolved.affectedCombatantIds.length,
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
      affectedCells: resolved.affectedCells,
      affectedTokenIds: resolved.affectedTokenIds,
      affectedCombatantIds: resolved.affectedCombatantIds
    });
  }

  if (encounter.actionTracker.has(actionId)) {
    request.log.info(
      { sessionId, actionId, shape },
      `${LOG_PREFIX} area targeting duplicate_action`
    );
    return reply.status(200).send({
      isValid: true,
      reason: null,
      sessionId,
      actionId,
      version: encounter.combatState.version,
      shape,
      sourceTokenId: sourceToken.id,
      affectedCells: resolved.affectedCells,
      affectedTokenIds: resolved.affectedTokenIds,
      affectedCombatantIds: resolved.affectedCombatantIds
    });
  }

  encounter.actionTracker.record(actionId);
  encounter.combatState = {
    ...encounter.combatState,
    version: nextEncounterVersion(encounter.combatState.version)
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
      shape,
      affectedCells: resolved.affectedCells,
      affectedTokenIds: resolved.affectedTokenIds,
      affectedCombatantIds: resolved.affectedCombatantIds,
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
    affectedCells: resolved.affectedCells,
    affectedTokenIds: resolved.affectedTokenIds,
    affectedCombatantIds: resolved.affectedCombatantIds
  });
}

export function registerAreaTargetingRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository,
  broadcaster?: BroadcastAdapter
) {
  app.post(
    "/integration/sessions/:sessionId/targeting/area",
    (request, reply) =>
      handleAreaRoute(request, reply, repository, broadcaster, true)
  );
  app.post(
    "/integration/sessions/:sessionId/targeting/area/preview",
    (request, reply) =>
      handleAreaRoute(request, reply, repository, broadcaster, false)
  );
}
