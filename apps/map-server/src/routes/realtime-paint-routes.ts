import type { FastifyInstance } from "fastify";
import {
  edgeObstaclePaintRequestSchema,
  elevationPaintRequestSchema,
  gridCalibrationRequestSchema,
  obstaclePaintRequestSchema
} from "@limiarmap/shared-contracts";
import type { InMemoryEncounterRepository } from "../modules/encounters/encounter-repository";
import type { BroadcastAdapter } from "../modules/realtime/broadcast";
import { broadcastAuthoritativeEvent } from "../modules/realtime/broadcast";
import { GridCalibrationService } from "../modules/encounters/grid-calibration-service";
import { ObstaclePaintService } from "../modules/encounters/obstacle-paint-service";
import { EdgeObstaclePaintService } from "../modules/encounters/edge-obstacle-paint-service";
import { ElevationPaintService } from "../modules/encounters/elevation-paint-service";
import { toEncounterSnapshot } from "../modules/encounters/encounter-snapshot";
import {
  LOG_PREFIX,
  err,
  getActor,
  getGridCalibrationRejectionDetails,
  getObstaclePaintRejectionDetails,
  getEdgeObstaclePaintRejectionDetails,
  getElevationPaintRejectionDetails,
  emitRejection,
  ensureEncounter
} from "./realtime-helpers";

export function registerRealtimePaintRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository,
  broadcaster?: BroadcastAdapter
): void {
  const gridCalibrationService = new GridCalibrationService(repository);
  const obstaclePaintService = new ObstaclePaintService(repository);
  const edgeObstaclePaintService = new EdgeObstaclePaintService(repository);
  const elevationPaintService = new ElevationPaintService(repository);

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

  app.post(
    "/sessions/:sessionId/actions/elevation",
    async (request, reply) => {
      const { sessionId } = request.params as { sessionId: string };
      const encounter = ensureEncounter(repository, sessionId, reply);
      if (!encounter) {
        return;
      }

      const parse = elevationPaintRequestSchema.safeParse(request.body);
      if (!parse.success) {
        return err(reply, 400, "Invalid elevation paint request body");
      }

      const actor = getActor(request);
      request.log.info(
        {
          sessionId,
          actionId: parse.data.actionId,
          actorId: actor.actorId,
          actorType: actor.actorType
        },
        `${LOG_PREFIX} POST elevation`
      );

      const result = elevationPaintService.paintElevation(
        sessionId,
        actor.actorType,
        parse.data.centerCell,
        parse.data.radius,
        parse.data.mode,
        parse.data.elevationMeters,
        parse.data.actionId
      );

      if (!result.accepted) {
        emitRejection(
          broadcaster,
          sessionId,
          result.encounter.combatState.version,
          parse.data.actionId,
          result.rejectionReason ?? "unknown",
          getElevationPaintRejectionDetails(result.rejectionReason ?? "unknown")
        );
        return reply.send(toEncounterSnapshot(result.encounter));
      }

      broadcastAuthoritativeEvent(broadcaster, "elevation.updated", {
        eventId: `elevation:${parse.data.actionId}`,
        eventType: "elevation.updated",
        encounterId: sessionId,
        version: result.encounter.combatState.version,
        actionId: parse.data.actionId,
        payload: {
          battleMapId: result.encounter.battleMap.id,
          cellElevations: result.encounter.cellElevations
        },
        replaySafe: true
      });

      return reply.send(toEncounterSnapshot(result.encounter));
    }
  );
}
