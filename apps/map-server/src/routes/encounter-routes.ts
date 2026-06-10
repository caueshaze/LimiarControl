import type { FastifyInstance, FastifyReply } from "fastify";
import type { InMemoryEncounterRepository } from "../modules/encounters/encounter-repository";
import { toEncounterSnapshot } from "../modules/encounters/encounter-snapshot";

/** Path prefixes the map server is allowed to proxy (no SSRF / open proxy). */
const PROXYABLE_ASSET_PREFIXES = ["/api/assets/", "/onboarding/"];

function controlServerBaseUrl(): string {
  return (process.env.CONTROL_SERVER_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
}

/**
 * Pick the upstream origin for a proxied asset. Uploaded assets (`/api/assets`)
 * live on the control server. Frontend static assets (onboarding token presets)
 * are served by the control server's SPA in production, but by the control web
 * dev server locally — set CONTROL_WEB_BASE_URL=http://localhost:5173 for dev.
 */
function assetUpstreamBaseUrl(sourcePath: string): string {
  if (sourcePath.startsWith("/onboarding/")) {
    return (process.env.CONTROL_WEB_BASE_URL ?? controlServerBaseUrl()).replace(/\/$/, "");
  }
  return controlServerBaseUrl();
}

/**
 * Stream a control-hosted asset back through the map server, forwarding the
 * internal key and cache headers. Shared by the battle-map background and the
 * per-token portrait proxy so both load same-origin from the map web app.
 */
async function proxyControlServerAsset(
  reply: FastifyReply,
  sourcePath: string,
  notFoundMessage: string,
  baseUrl: string
): Promise<FastifyReply> {
  const internalKey = process.env.LIMIAR_MAP_INTERNAL_KEY ?? "dev-map-internal-key";
  const upstream = await fetch(`${baseUrl}${sourcePath}`, {
    headers: {
      "X-Limiar-Map-Internal-Key": internalKey
    }
  });
  if (!upstream.ok) {
    return reply.status(upstream.status).send({ message: notFoundMessage });
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
}

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

    return proxyControlServerAsset(reply, sourceImageUrl, "Failed to load battle map background", controlServerBaseUrl());
  });

  // Proxy a token portrait (onboarding preset or uploaded asset) that lives on
  // the control server, so the map web app can load it same-origin without CORS.
  app.get("/sessions/:sessionId/asset", async (request, reply) => {
    const { sessionId } = request.params as { sessionId: string };
    const { src } = request.query as { src?: string };
    const encounter = repository.getEncounter(sessionId);
    if (!encounter) {
      return reply.status(404).send({ message: "Encounter not found" });
    }
    if (typeof src !== "string" || src.length === 0) {
      return reply.status(400).send({ message: "Missing asset src" });
    }
    // Only relative control-server paths with allow-listed prefixes — no absolute
    // URLs, protocol-relative URLs, or path traversal (guards against SSRF).
    const isAllowed =
      src.startsWith("/") &&
      !src.startsWith("//") &&
      !src.includes("..") &&
      PROXYABLE_ASSET_PREFIXES.some((prefix) => src.startsWith(prefix));
    if (!isAllowed) {
      return reply.status(403).send({ message: "Asset path not allowed" });
    }

    return proxyControlServerAsset(reply, src, "Failed to load token asset", assetUpstreamBaseUrl(src));
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
