import type { FastifyInstance } from "fastify";
import {
  movementAppliedEventSchema,
  movementPreviewRequestSchema,
  movementPreviewResponseSchema
} from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../../modules/realtime/broadcast";
import { MovementService } from "../../modules/encounters/movement-service";

const LOG_PREFIX = "[integration]";

type Reply = {
  status(code: number): { send(payload: unknown): unknown };
};

function err(reply: Reply, status: number, reason: string, message: string) {
  return reply.status(status).send({ message, reason });
}

function toMovementResponse(
  sessionId: string,
  actionId: string,
  version: number,
  result: {
    accepted: boolean;
    rejectionReason?: string;
    tokenId?: string;
    combatantId?: string;
    source?: { x: number; y: number };
    destination?: { x: number; y: number };
    path?: Array<{ x: number; y: number }>;
    pathCostUnits?: number;
    movementBudget?: number;
    movementSpeedCells?: number;
    remainingBudget?: number;
  }
) {
  return movementPreviewResponseSchema.parse({
    isValid: result.accepted,
    reason: result.accepted ? null : (result.rejectionReason ?? "unknown"),
    sessionId,
    actionId,
    version,
    tokenId: result.tokenId ?? null,
    combatantId: result.combatantId ?? null,
    sourceCell: result.source ?? null,
    destinationCell: result.destination,
    path: result.path ?? [],
    pathCostUnits: result.pathCostUnits ?? 0,
    movementBudget: result.movementBudget ?? 0,
    movementSpeedCells: result.movementSpeedCells ?? 1,
    remainingBudget: result.remainingBudget ?? result.movementBudget ?? 0
  });
}

export function registerMovementRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository,
  broadcaster?: BroadcastAdapter
) {
  const movementService = new MovementService(repository);

  app.post("/integration/sessions/:sessionId/movement/preview", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = movementPreviewRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    const { actionId, combatantId, destinationCell } = parse.data;
    request.log.info(
      { sessionId, actionId, combatantId, destinationCell },
      `${LOG_PREFIX} movement preview`
    );

    const result = movementService.previewMovement(sessionId, combatantId, destinationCell);
    return reply.status(200).send(
      toMovementResponse(sessionId, actionId, encounter.combatState.version, result)
    );
  });

  app.post("/integration/sessions/:sessionId/movement", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return err(reply, 404, "session_not_found", "Session not found");
    }

    const parse = movementPreviewRequestSchema.safeParse(request.body);
    if (!parse.success) {
      return reply.status(400).send({ message: "Invalid request body", errors: parse.error.errors });
    }

    const { actionId, combatantId, destinationCell } = parse.data;
    request.log.info(
      { sessionId, actionId, combatantId, destinationCell },
      `${LOG_PREFIX} movement apply`
    );

    const result = movementService.moveCombatant(sessionId, combatantId, destinationCell, actionId);
    const currentEncounter = "encounter" in result ? result.encounter : encounter;
    const response = toMovementResponse(sessionId, actionId, currentEncounter.combatState.version, {
      accepted: result.accepted,
      rejectionReason: result.rejectionReason,
      tokenId: "tokenId" in result ? result.tokenId : undefined,
      combatantId,
      source: "source" in result ? result.source : currentEncounter.tokens.find((token) => token.combatantId === combatantId)?.position,
      destination: destinationCell,
      path: "path" in result ? result.path : undefined,
      pathCostUnits: result.pathCostUnits,
      movementBudget: result.movementBudget,
      movementSpeedCells:
        "movementSpeedCells" in result
          ? result.movementSpeedCells
          : currentEncounter.tokens.find((token) => token.combatantId === combatantId)?.movementSpeedCells,
      remainingBudget: result.remainingBudget
    });

    if (result.accepted && broadcaster && response.tokenId && response.sourceCell) {
      const appliedEvent = movementAppliedEventSchema.parse({
        eventId: `move:${actionId}`,
        eventType: "movement.applied",
        encounterId: sessionId,
        version: currentEncounter.combatState.version,
        actionId,
        payload: {
          tokenId: response.tokenId,
          position: response.destinationCell,
          pathCostUnits: response.pathCostUnits,
          remainingBudget: response.remainingBudget
        },
        replaySafe: true
      });
      broadcastAuthoritativeEvent(broadcaster, "movement.applied", appliedEvent);
    }

    return reply.status(200).send(response);
  });
}
