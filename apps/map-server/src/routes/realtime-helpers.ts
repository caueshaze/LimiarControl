import { createHmac } from "node:crypto";
import type { FastifyRequest } from "fastify";
import type { ControllerType } from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../modules/realtime/broadcast";
import { createRejectionPayload } from "../modules/realtime/rejection-events";

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

function getElevationPaintRejectionDetails(reason: string): string {
  switch (reason) {
    case "not_gm":
      return "Only the GM can paint elevation";
    case "outside_map":
      return "Elevation brush center must stay inside the map";
    case "invalid_elevation_brush":
      return "Elevation brush did not cover any valid map cells";
    case "duplicate_action":
      return "Elevation paint action was already processed";
    default:
      return "Elevation paint rejected";
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

export {
  LOG_PREFIX,
  DEFAULT_ACTOR,
  SUPPORTED_ACTOR_TYPES,
  err,
  getActor,
  base64UrlEncode,
  signJwt,
  buildDisplayName,
  getGridCalibrationRejectionDetails,
  getMovementRejectionDetails,
  getObstaclePaintRejectionDetails,
  getEdgeObstaclePaintRejectionDetails,
  getElevationPaintRejectionDetails,
  getTargetingRejectionDetails,
  emitRejection,
  ensureEncounter
};
export type {
  ActorType,
  ActorContext,
  RealtimeReply,
  ConnectionTokenRequest
};
