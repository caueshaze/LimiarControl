import { createHmac } from "node:crypto";
import type { FastifyInstance, FastifyRequest } from "fastify";
import type { ControllerType } from "@limiarmap/shared-contracts";
import {
  combatAdvanceRequestSchema,
  edgeObstaclePaintRequestSchema,
  gridCalibrationRequestSchema,
  movementRequestSchema,
  obstaclePaintRequestSchema,
  targetingSubmitSchema
} from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../modules/realtime/broadcast";
import { createRejectionPayload } from "../modules/realtime/rejection-events";
import { MovementService } from "../modules/encounters/movement-service";
import { CombatService } from "../modules/combat/combat-service";
import { TargetingService } from "../modules/encounters/targeting-service";
import { GridCalibrationService } from "../modules/encounters/grid-calibration-service";
import { ObstaclePaintService } from "../modules/encounters/obstacle-paint-service";
import { EdgeObstaclePaintService } from "../modules/encounters/edge-obstacle-paint-service";
import { toEncounterSnapshot } from "../modules/encounters/encounter-snapshot";

type ActorType = Extract<ControllerType, "player" | "gm" | "limiarControl">;

type ActorContext = {
  actorId: string;
  actorType: ActorType;
};

type RealtimeReply = {
  status(code: number): { send(payload: unknown): unknown };
  send(payload: unknown): unknown;
};

type ConnectionTokenRequest = {
  actorId?: string;
  actorType?: ActorType;
};

const LOG_PREFIX = "[realtime-http]";
const DEFAULT_ACTOR: ActorContext = {
  actorId: "player_1",
  actorType: "player"
};
const SUPPORTED_ACTOR_TYPES = new Set<ActorType>([
  "player",
  "gm",
  "limiarControl"
]);

function err(reply: RealtimeReply, status: number, message: string) {
  return reply.status(status).send({ message });
}

function getActor(request: FastifyRequest): ActorContext {
  const actorIdHeader = request.headers["x-limiar-actor-id"];
  const actorTypeHeader = request.headers["x-limiar-actor-type"];
  const actorId =
    typeof actorIdHeader === "string" && actorIdHeader.trim().length > 0
      ? actorIdHeader
      : DEFAULT_ACTOR.actorId;
  const actorType =
    typeof actorTypeHeader === "string" &&
    SUPPORTED_ACTOR_TYPES.has(actorTypeHeader as ActorType)
      ? (actorTypeHeader as ActorType)
      : DEFAULT_ACTOR.actorType;
  return { actorId, actorType };
}

function base64UrlEncode(data: string): string {
  return Buffer.from(data)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function signJwt(payload: Record<string, unknown>): string {
  const secret =
    process.env.CENTRIFUGO_TOKEN_HMAC_SECRET_KEY ?? "dev-secret-change-me";
  const header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = base64UrlEncode(JSON.stringify(payload));
  const signature = createHmac("sha256", secret)
    .update(`${header}.${body}`)
    .digest("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
  return `${header}.${body}.${signature}`;
}

function buildDisplayName(actor: ActorContext): string {
  if (actor.actorType === "gm") {
    return `GM ${actor.actorId}`;
  }
  if (actor.actorType === "limiarControl") {
    return "LimiarControl";
  }
  return `Player ${actor.actorId}`;
}

function getGridCalibrationRejectionDetails(reason: string): string {
  switch (reason) {
    case "not_gm":
      return "Only the GM can update grid calibration";
    case "invalid_grid_calibration":
      return "Grid calibration must stay within image bounds";
    case "invalid_grid_dimensions":
      return "Grid dimensions must be positive and stay within the supported range";
    case "grid_dimensions_too_small":
      return "Grid dimensions cannot hide existing tokens or obstacles";
    case "duplicate_action":
      return "Grid calibration action was already processed";
    default:
      return "Grid calibration rejected";
  }
}

function getMovementRejectionDetails(reason: string): string {
  switch (reason) {
    case "movement_budget_exceeded":
      return "Movimento rejeitado: limite de deslocamento excedido";
    case "blocked_path":
      return "Caminho bloqueado por obstáculo";
    case "not_your_turn":
      return "Não é o turno deste combatente";
    case "token_not_found":
      return "Token não encontrado";
    case "duplicate_action":
      return "Ação de movimento já processada";
    default:
      return "Movimento rejeitado";
  }
}

function getObstaclePaintRejectionDetails(reason: string): string {
  switch (reason) {
    case "not_gm":
      return "Only the GM can paint obstacles";
    case "outside_map":
      return "Obstacle brush center must stay inside the map";
    case "invalid_obstacle_brush":
      return "Obstacle brush did not cover any valid map cells";
    case "invalid_obstacle_style":
      return "Obstacle style payload is invalid";
    case "duplicate_action":
      return "Obstacle paint action was already processed";
    default:
      return "Obstacle paint rejected";
  }
}

function getEdgeObstaclePaintRejectionDetails(reason: string): string {
  switch (reason) {
    case "not_gm":
      return "Only the GM can paint edge obstacles";
    case "outside_map":
      return "Edge cell must stay inside the map";
    case "invalid_direction":
      return "Edge direction must be N, E, S, or W";
    case "invalid_edge_style":
      return "Edge obstacle style payload is invalid";
    case "duplicate_action":
      return "Edge obstacle paint action was already processed";
    default:
      return "Edge obstacle paint rejected";
  }
}

function getTargetingRejectionDetails(reason: string): string {
  switch (reason) {
    case "no_line_of_sight":
      return "Linha de visao bloqueada por obstaculo";
    case "no_line_of_effect":
      return "Linha de efeito bloqueada por obstaculo";
    case "out_of_range":
      return "Alvo fora do alcance";
    case "unknown_token":
      return "Token nao encontrado";
    case "unauthorized_action":
      return "Acao de targeting nao autorizada";
    case "duplicate_action":
      return "Acao de targeting ja processada";
    default:
      return "Targeting rejeitado";
  }
}

function emitRejection(
  broadcaster: BroadcastAdapter | undefined,
  sessionId: string,
  version: number,
  actionId: string,
  reason: string,
  message: string,
  extra?: {
    details?: string;
    tokenId?: string;
    pathCostUnits?: number;
    movementBudget?: number;
    exceededBy?: number;
  }
): void {
  broadcastAuthoritativeEvent(broadcaster, "action.rejected", {
    eventId: `reject:${actionId}`,
    eventType: "action.rejected",
    encounterId: sessionId,
    version,
    actionId,
    payload: createRejectionPayload(reason, message, extra),
    replaySafe: true
  });
}

function ensureEncounter(
  repository: InMemoryEncounterRepository,
  sessionId: string,
  reply: RealtimeReply
): ReturnType<InMemoryEncounterRepository["getEncounter"]> {
  const encounter = repository.getEncounter(sessionId);
  if (!encounter) {
    err(reply, 404, "Encounter not found");
    return undefined;
  }
  return encounter;
}

export function registerRealtimeRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository,
  broadcaster?: BroadcastAdapter
): void {
  const movementService = new MovementService(repository);
  const combatService = new CombatService(repository);
  const targetingService = new TargetingService(repository);
  const gridCalibrationService = new GridCalibrationService(repository);
  const obstaclePaintService = new ObstaclePaintService(repository);
  const edgeObstaclePaintService = new EdgeObstaclePaintService(repository);

  app.post("/centrifugo/connection-token", async (request, reply) => {
    const body = (request.body as ConnectionTokenRequest | undefined) ?? {};
    const actorType = SUPPORTED_ACTOR_TYPES.has(
      body.actorType ?? DEFAULT_ACTOR.actorType
    )
      ? (body.actorType ?? DEFAULT_ACTOR.actorType)
      : DEFAULT_ACTOR.actorType;
    const actor: ActorContext = {
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

  app.post(
    "/sessions/:sessionId/actions/grid-calibration",
    async (request, reply) => {
      const { sessionId } = request.params as { sessionId: string };
      const encounter = ensureEncounter(repository, sessionId, reply);
      if (!encounter) {
        return;
      }

      const parse = gridCalibrationRequestSchema.safeParse(request.body);
      if (!parse.success) {
        return err(reply, 400, "Invalid grid calibration request body");
      }

      const actor = getActor(request);
      request.log.info(
        {
          sessionId,
          actionId: parse.data.actionId,
          actorId: actor.actorId,
          actorType: actor.actorType
        },
        `${LOG_PREFIX} POST grid-calibration`
      );

      const result = gridCalibrationService.updateGridCalibration(
        sessionId,
        actor.actorType,
        parse.data.gridCalibration,
        parse.data.gridWidth,
        parse.data.gridHeight,
        parse.data.actionId
      );

      if (!result.accepted) {
        emitRejection(
          broadcaster,
          sessionId,
          result.encounter.combatState.version,
          parse.data.actionId,
          result.rejectionReason ?? "unknown",
          getGridCalibrationRejectionDetails(
            result.rejectionReason ?? "unknown"
          )
        );
        return reply.send(toEncounterSnapshot(result.encounter));
      }

      broadcastAuthoritativeEvent(broadcaster, "grid.calibration.updated", {
        eventId: `grid-calibration:${parse.data.actionId}`,
        eventType: "grid.calibration.updated",
        encounterId: sessionId,
        version: result.encounter.combatState.version,
        actionId: parse.data.actionId,
        payload: {
          battleMapId: result.encounter.battleMap.id,
          gridCalibration: result.encounter.battleMap.gridCalibration,
          gridWidth: result.encounter.battleMap.gridWidth,
          gridHeight: result.encounter.battleMap.gridHeight
        },
        replaySafe: true
      });

      return reply.send(toEncounterSnapshot(result.encounter));
    }
  );

  app.post("/sessions/:sessionId/actions/obstacles", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = ensureEncounter(repository, sessionId, reply);
    if (!encounter) {
      return;
    }

    const parse = obstaclePaintRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return err(reply, 400, "Invalid obstacle paint request body");
    }

    const actor = getActor(request);
    request.log.info(
      {
        sessionId,
        actionId: parse.data.actionId,
        actorId: actor.actorId,
        actorType: actor.actorType
      },
      `${LOG_PREFIX} POST obstacles`
    );

    const result = obstaclePaintService.paintObstacle(
      sessionId,
      actor.actorType,
      parse.data.centerCell,
      parse.data.radius,
      parse.data.mode,
      parse.data.style,
      parse.data.actionId
    );

    if (!result.accepted) {
      emitRejection(
        broadcaster,
        sessionId,
        result.encounter.combatState.version,
        parse.data.actionId,
        result.rejectionReason ?? "unknown",
        getObstaclePaintRejectionDetails(result.rejectionReason ?? "unknown")
      );
      return reply.send(toEncounterSnapshot(result.encounter));
    }

    broadcastAuthoritativeEvent(broadcaster, "obstacles.updated", {
      eventId: `obstacles:${parse.data.actionId}`,
      eventType: "obstacles.updated",
      encounterId: sessionId,
      version: result.encounter.combatState.version,
      actionId: parse.data.actionId,
      payload: {
        battleMapId: result.encounter.battleMap.id,
        obstacles: result.encounter.obstacles
      },
      replaySafe: true
    });

    return reply.send(toEncounterSnapshot(result.encounter));
  });

  app.post(
    "/sessions/:sessionId/actions/edge-obstacles",
    async (request, reply) => {
      const { sessionId } = request.params as { sessionId: string };
      const encounter = ensureEncounter(repository, sessionId, reply);
      if (!encounter) {
        return;
      }

      const parse = edgeObstaclePaintRequestSchema.safeParse(request.body);
      if (!parse.success) {
        return err(reply, 400, "Invalid edge obstacle paint request body");
      }

      const actor = getActor(request);
      request.log.info(
        {
          sessionId,
          actionId: parse.data.actionId,
          actorId: actor.actorId,
          actorType: actor.actorType
        },
        `${LOG_PREFIX} POST edge-obstacles`
      );

      const result = edgeObstaclePaintService.paintEdgeObstacle(
        sessionId,
        actor.actorType,
        parse.data.cell,
        parse.data.direction,
        parse.data.mode,
        parse.data.style,
        parse.data.actionId
      );

      if (!result.accepted) {
        emitRejection(
          broadcaster,
          sessionId,
          result.encounter.combatState.version,
          parse.data.actionId,
          result.rejectionReason ?? "unknown",
          getEdgeObstaclePaintRejectionDetails(
            result.rejectionReason ?? "unknown"
          )
        );
        return reply.send(toEncounterSnapshot(result.encounter));
      }

      broadcastAuthoritativeEvent(broadcaster, "edge_obstacles.updated", {
        eventId: `edge-obstacles:${parse.data.actionId}`,
        eventType: "edge_obstacles.updated",
        encounterId: sessionId,
        version: result.encounter.combatState.version,
        actionId: parse.data.actionId,
        payload: {
          battleMapId: result.encounter.battleMap.id,
          edgeObstacles: result.encounter.edgeObstacles
        },
        replaySafe: true
      });

      return reply.send(toEncounterSnapshot(result.encounter));
    }
  );
}
