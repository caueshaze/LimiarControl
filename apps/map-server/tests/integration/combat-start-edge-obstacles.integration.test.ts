import { describe, expect, it, vi } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

const BASE_BATTLE_MAP = {
  name: "Dungeon Depths",
  gridWidth: 20,
  gridHeight: 14,
  gridCalibration: { x: 0, y: 0, width: 1, height: 1 },
  imageUrl: "/sessions/session-edge/battle-map/background",
  sourceImageUrl: "/api/assets/internal/campaigns/campaign-1/maps/asset123",
};

const EDGE_WALL = {
  x: 4,
  y: 4,
  direction: "E" as const,
  blocksMovement: true,
  blocksVision: true,
  blocksEffect: true,
  cover: "full" as const,
};

function alignTokensForEdgeTests(
  repository: ReturnType<typeof createApp>["repository"],
  sessionId: string,
) {
  const encounter = repository.requireEncounter(sessionId);
  encounter.tokens = encounter.tokens.map((token) =>
    token.combatantId === "cmb_1"
      ? { ...token, position: { x: 4, y: 4 } }
      : token.combatantId === "cmb_2"
        ? { ...token, position: { x: 5, y: 4 } }
        : token,
  );
  repository.saveEncounter(encounter);
}

describe("combat start: edge obstacle seeding", () => {
  it("seeds edge obstacles from battleMap.edgeObstacles", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-edge-seed/combat/start",
      payload: {
        actionId: "start-edge-seed-1",
        combatants: [
          { combatantId: "cmb_1", initiativeScore: 20 },
          { combatantId: "cmb_2", initiativeScore: 10 },
        ],
        battleMap: {
          ...BASE_BATTLE_MAP,
          edgeObstacles: [EDGE_WALL],
        },
      },
    });

    expect(response.statusCode).toBe(200);
    expect(repository.requireEncounter("session-edge-seed").edgeObstacles).toEqual([
      expect.objectContaining({
        x: 4,
        y: 4,
        direction: "E",
        blocksMovement: true,
        blocksVision: true,
        blocksEffect: true,
        cover: "full",
      }),
    ]);

    await app.close();
  });

  it("rejects movement across a seeded blocking edge", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });
    const { registerRealtimeRoutes } = await import("../../src/routes/realtime-routes");
    registerRealtimeRoutes(app, repository, { emit: vi.fn() });

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-edge-move/combat/start",
      payload: {
        actionId: "start-edge-move-1",
        combatants: [{ combatantId: "cmb_1", initiativeScore: 20 }],
        battleMap: {
          ...BASE_BATTLE_MAP,
          edgeObstacles: [EDGE_WALL],
        },
      },
    });

    const version = repository.requireEncounter("session-edge-move").combatState.version;
    const moveResp = await app.inject({
      method: "POST",
      url: "/sessions/session-edge-move/actions/movement",
      headers: {
        "x-limiar-actor-id": "player_1",
        "x-limiar-actor-type": "player",
      },
      payload: {
        actionId: "move-edge-1",
        sessionId: "session-edge-move",
        tokenId: "tok_player",
        path: [{ x: 5, y: 4 }],
        knownVersion: version,
      },
    });

    expect(moveResp.statusCode).toBe(200);
    const token = repository
      .requireEncounter("session-edge-move")
      .tokens.find((entry) => entry.id === "tok_player");
    expect(token?.position).toEqual({ x: 4, y: 4 });

    await app.close();
  });

  it("rejects single-target actions that require sight across a seeded edge wall", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-edge-los/combat/start",
      payload: {
        actionId: "start-edge-los-1",
        combatants: [
          { combatantId: "cmb_1", initiativeScore: 20 },
          { combatantId: "cmb_2", initiativeScore: 10 },
        ],
        battleMap: {
          ...BASE_BATTLE_MAP,
          edgeObstacles: [EDGE_WALL],
        },
      },
    });
    alignTokensForEdgeTests(repository, "session-edge-los");

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-edge-los/targeting",
      payload: {
        actionId: "target-edge-los-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5,
        requiresSight: true,
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "no_line_of_sight",
    });

    await app.close();
  });

  it("reports full cover across a seeded edge wall", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-edge-cover/combat/start",
      payload: {
        actionId: "start-edge-cover-1",
        combatants: [
          { combatantId: "cmb_1", initiativeScore: 20 },
          { combatantId: "cmb_2", initiativeScore: 10 },
        ],
        battleMap: {
          ...BASE_BATTLE_MAP,
          edgeObstacles: [EDGE_WALL],
        },
      },
    });
    alignTokensForEdgeTests(repository, "session-edge-cover");

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-edge-cover/targeting",
      payload: {
        actionId: "target-edge-cover-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5,
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "full_cover",
      cover: "full",
    });

    await app.close();
  });

  it("rejects area targeting when a seeded edge obstacle blocks line of effect", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-edge-loe/combat/start",
      payload: {
        actionId: "start-edge-loe-1",
        combatants: [{ combatantId: "cmb_1", initiativeScore: 20 }],
        battleMap: {
          ...BASE_BATTLE_MAP,
          edgeObstacles: [
            {
              x: 4,
              y: 4,
              direction: "E" as const,
              blocksMovement: false,
              blocksVision: false,
              blocksEffect: true,
              cover: "none" as const,
            },
          ],
        },
      },
    });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-edge-loe/targeting/area",
      payload: {
        actionId: "area-edge-loe-1",
        combatantId: "cmb_1",
        shape: "sphere",
        originCell: { x: 4, y: 4 },
        anchorCell: { x: 5, y: 4 },
        rangeCells: 5,
        sizeCells: 1,
        requiresEffect: true,
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "no_line_of_effect",
    });

    await app.close();
  });
});
