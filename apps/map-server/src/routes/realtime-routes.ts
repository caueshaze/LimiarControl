import type { FastifyInstance } from "fastify";
import {
  combatAdvanceRequestSchema,
  movementRequestSchema,
  targetingSubmitSchema
} from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../modules/realtime/broadcast";
import { MovementService } from "../modules/encounters/movement-service";
import { CombatService } from "../modules/combat/combat-service";
import { TargetingService } from "../modules/encounters/targeting-service";
import { toEncounterSnapshot } from "../modules/encounters/encounter-snapshot";
import {
  LOG_PREFIX,
  DEFAULT_ACTOR,
  SUPPORTED_ACTOR_TYPES,
  err,
  getActor,
  signJwt,
  buildDisplayName,
  getMovementRejectionDetails,
  getTargetingRejectionDetails,
  emitRejection,
  ensureEncounter
} from "./realtime-helpers";
import type { ConnectionTokenRequest } from "./realtime-helpers";

export function registerRealtimeRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository,
  broadcaster?: BroadcastAdapter
): void {
  const movementService = new MovementService(repository);
  const combatService = new CombatService(repository);
  const targetingService = new TargetingService(repository);

  app.post("/centrifugo/connection-token", async (request, reply) => {
    const body = (request.body as ConnectionTokenRequest | undefined) ?? {};
    const actorType = SUPPORTED_ACTOR_TYPES.has(
      body.actorType ?? DEFAULT_ACTOR.actorType
    )
      ? (body.actorType ?? DEFAULT_ACTOR.actorType)
      : DEFAULT_ACTOR.actorType;
    const actor = {
      actorId:
        typeof body.actorId === "string" && body.actorId.trim().length > 0
          ? body.actorId
          : DEFAULT_ACTOR.actorId,
      actorType
    };
    request.log.info(
      { actorId: actor.actorId, actorType: actor.actorType },
      `${LOG_PREFIX} POST centrifugo/connection-token`
    );
    return reply.send({
      token: signJwt({
        sub: `${actor.actorType}:${actor.actorId}`,
        exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24,
        info: {
          actorId: actor.actorId,
          actorType: actor.actorType,
          displayName: buildDisplayName(actor)
        }
      })
    });
  });

  app.post("/sessions/:sessionId/actions/movement", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = ensureEncounter(repository, sessionId, reply);
    if (!encounter) {
      return;
    }

    const parse = movementRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return err(reply, 400, "Invalid movement request body");
    }

    const actor = getActor(request);
    request.log.info(
      {
        sessionId,
        actionId: parse.data.actionId,
        actorId: actor.actorId,
        actorType: actor.actorType
      },
      `${LOG_PREFIX} POST movement`
    );

    const result = movementService.moveToken(
      sessionId,
      parse.data.tokenId,
      actor.actorId,
      actor.actorType,
      parse.data.path,
      parse.data.actionId
    );

    if (!result.accepted) {
      const movementReason = result.rejectionReason ?? "unknown";
      emitRejection(
        broadcaster,
        sessionId,
        result.encounter.combatState.version,
        parse.data.actionId,
        movementReason,
        getMovementRejectionDetails(movementReason),
        {
          tokenId: result.tokenId,
          pathCostUnits: result.pathCostUnits,
          movementBudget: result.movementBudget,
          exceededBy: result.exceededBy
        }
      );
      return reply.send(toEncounterSnapshot(result.encounter));
    }

    const movedToken = result.encounter.tokens.find(
      (token) => token.id === parse.data.tokenId
    );
    broadcastAuthoritativeEvent(broadcaster, "movement.applied", {
      eventId: `move:${parse.data.actionId}`,
      eventType: "movement.applied",
      encounterId: sessionId,
      version: result.encounter.combatState.version,
      actionId: parse.data.actionId,
      payload: {
        tokenId: parse.data.tokenId,
        position: movedToken?.position,
        pathCostUnits: result.pathCostUnits,
        remainingBudget: result.remainingBudget
      },
      replaySafe: true
    });

    return reply.send(toEncounterSnapshot(result.encounter));
  });

  app.post("/sessions/:sessionId/actions/place-token", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = ensureEncounter(repository, sessionId, reply);
    if (!encounter) return;

    const body = request.body as {
      actionId?: string;
      tokenId?: string;
      position?: { x?: number; y?: number };
    };
    if (
      typeof body.actionId !== "string" ||
      typeof body.tokenId !== "string" ||
      typeof body.position?.x !== "number" ||
      typeof body.position?.y !== "number"
    ) {
      return err(reply, 400, "Invalid placement request body");
    }

    request.log.info(
      { sessionId, actionId: body.actionId, tokenId: body.tokenId, position: body.position },
      `${LOG_PREFIX} POST place-token`
    );

    const result = movementService.placeToken(
      sessionId,
      body.tokenId,
      body.position as { x: number; y: number },
      body.actionId
    );

    if (!result.accepted) {
      return reply.send(toEncounterSnapshot(result.encounter));
    }

    broadcastAuthoritativeEvent(broadcaster, "movement.applied", {
      eventId: `place:${body.actionId}`,
      eventType: "movement.applied",
      encounterId: sessionId,
      version: result.encounter.combatState.version,
      actionId: body.actionId,
      payload: {
        tokenId: body.tokenId,
        position: result.position,
        pathCostUnits: 0,
        remainingBudget: result.remainingBudget
      },
      replaySafe: true
    });

    return reply.send(toEncounterSnapshot(result.encounter));
  });

  app.post(
    "/sessions/:sessionId/actions/combat/advance",
    async (request, reply) => {
      const { sessionId } = request.params as { sessionId: string };
      const encounter = ensureEncounter(repository, sessionId, reply);
      if (!encounter) {
        return;
      }

      const parse = combatAdvanceRequestSchema.safeParse(request.body);
      if (!parse.success) {
        return err(reply, 400, "Invalid combat advance request body");
      }

      request.log.info(
        {
          sessionId,
          actionId: parse.data.actionId,
          requestedBy: parse.data.requestedBy
        },
        `${LOG_PREFIX} POST combat/advance`
      );

      const result = combatService.advance(
        sessionId,
        parse.data.actionId,
        parse.data.requestedBy
      );
      if (!result.accepted) {
        emitRejection(
          broadcaster,
          sessionId,
          result.encounter.combatState.version,
          parse.data.actionId,
          result.rejectionReason ?? "unknown",
          "Combat rejected"
        );
        return reply.send(toEncounterSnapshot(result.encounter));
      }

      broadcastAuthoritativeEvent(broadcaster, "combat.advanced", {
        eventId: `combat:${parse.data.actionId}`,
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

      return reply.send(toEncounterSnapshot(result.encounter));
    }
  );

  app.post("/sessions/:sessionId/actions/targeting", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = ensureEncounter(repository, sessionId, reply);
    if (!encounter) {
      return;
    }

    const parse = targetingSubmitSchema.safeParse(request.body);
    if (!parse.success) {
      return err(reply, 400, "Invalid targeting request body");
    }

    const actor = getActor(request);
    request.log.info(
      {
        sessionId,
        actionId: parse.data.actionId,
        actorId: actor.actorId,
        actorType: actor.actorType
      },
      `${LOG_PREFIX} POST targeting`
    );

    const result = targetingService.resolveTargeting(
      sessionId,
      {
        actionId: parse.data.actionId,
        tokenId: parse.data.tokenId,
        shape: parse.data.shape,
        originCell: parse.data.originCell,
        anchorCell: parse.data.anchorCell,
        rangeCells: parse.data.rangeCells,
        sizeCells: parse.data.sizeCells,
        affectedCells: [],
        result: "pending"
      },
      actor.actorId,
      actor.actorType,
      {
        requiresSight: parse.data.requiresSight,
        requiresEffect: parse.data.requiresEffect
      }
    );

    if (!result.accepted) {
      const targetingReason = result.rejectionReason ?? "unknown";
      emitRejection(
        broadcaster,
        sessionId,
        result.encounter.combatState.version,
        parse.data.actionId,
        targetingReason,
        getTargetingRejectionDetails(targetingReason)
      );
      return reply.send(toEncounterSnapshot(result.encounter));
    }

    broadcastAuthoritativeEvent(broadcaster, "targeting.resolved", {
      eventId: `target:${parse.data.actionId}`,
      eventType: "targeting.resolved",
      encounterId: sessionId,
      version: result.encounter.combatState.version,
      actionId: parse.data.actionId,
      payload: {
        tokenId: parse.data.tokenId,
        shape: parse.data.shape,
        affectedCells: result.affectedCells
      },
      replaySafe: true
    });

    return reply.send(toEncounterSnapshot(result.encounter));
  });
}
