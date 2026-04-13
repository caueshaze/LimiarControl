import type { FastifyInstance } from "fastify";
import type { InMemoryEncounterRepository } from "../modules/encounters/encounter-repository";
import { toEncounterSnapshot } from "../modules/encounters/encounter-snapshot";

export function registerEncounterRoutes(
  app: FastifyInstance,
  repository: InMemoryEncounterRepository
): void {
  app.get("/sessions/:sessionId/encounter", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return reply.status(404).send({ message: "Encounter not found" });
    }

    return reply.send(toEncounterSnapshot(encounter));
  });

  app.get("/sessions/:sessionId/battle-map/background", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return reply.status(404).send({ message: "Encounter not found" });
    }
    const sourceImageUrl = encounter.battleMapSourceImageUrl;
    if (!sourceImageUrl) {
      return reply.status(404).send({ message: "Battle map background not configured" });
    }

    const controlBaseUrl = (process.env.CONTROL_SERVER_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
    const internalKey = process.env.LIMIAR_MAP_INTERNAL_KEY ?? "dev-map-internal-key";
    const upstream = await fetch(`${controlBaseUrl}${sourceImageUrl}`, {
      headers: {
        "X-Limiar-Map-Internal-Key": internalKey
      }
    });
    if (!upstream.ok) {
      return reply.status(upstream.status).send({ message: "Failed to load battle map background" });
    }

    const contentType = upstream.headers.get("content-type");
    const contentLength = upstream.headers.get("content-length");
    const cacheControl = upstream.headers.get("cache-control");
    const etag = upstream.headers.get("etag");
    const lastModified = upstream.headers.get("last-modified");
    if (contentType) reply.header("Content-Type", contentType);
    if (contentLength) reply.header("Content-Length", contentLength);
    if (cacheControl) reply.header("Cache-Control", cacheControl);
    if (etag) reply.header("ETag", etag);
    if (lastModified) reply.header("Last-Modified", lastModified);

    const payload = Buffer.from(await upstream.arrayBuffer());
    return reply.send(payload);
  });

  app.post("/sessions/:sessionId/resync", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return reply.status(404).send({ message: "Encounter not found" });
    }

    return reply.send({
      resynced: true,
      snapshotVersion: encounter.combatState.version
    });
  });
}
