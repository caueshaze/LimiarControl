import { describe, expect, it } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

const BASE_BATTLE_MAP = {
  name: "Dungeon Depths",
  gridWidth: 20,
  gridHeight: 14,
  gridCalibration: { x: 0, y: 0, width: 1, height: 1 },
  imageUrl: "/sessions/session-bc/battle-map/background",
  sourceImageUrl: "/api/assets/internal/campaigns/campaign-1/maps/asset123",
};

describe("combat start: blocked cells seeding", () => {
  it("seeds solid obstacles from battleMap.blockedCells", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-bc/combat/start",
      payload: {
        actionId: "start-bc-1",
        combatants: [{ combatantId: "player-1", initiativeScore: 15 }],
        battleMap: {
          ...BASE_BATTLE_MAP,
          blockedCells: [
            { x: 3, y: 5 },
            { x: 4, y: 5 },
            { x: 5, y: 5 },
          ],
        },
      },
    });

    expect(response.statusCode).toBe(200);

    const encounter = repository.requireEncounter("session-bc");
    const blockedObstacles = encounter.obstacles.filter((o) => o.blocksMovement);
    const blockedPositions = blockedObstacles.flatMap((o) => o.cells);

    expect(blockedPositions).toContainEqual({ x: 3, y: 5 });
    expect(blockedPositions).toContainEqual({ x: 4, y: 5 });
    expect(blockedPositions).toContainEqual({ x: 5, y: 5 });
    expect(blockedObstacles.every((obstacle) => obstacle.blocksVision && obstacle.blocksEffect)).toBe(true);

    await app.close();
  });

  it("movement into a blocked cell is rejected server-side", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);
    const { registerRealtimeRoutes } = await import("../../src/routes/realtime-routes");
    registerRealtimeRoutes(app, repository);

    // Seed encounter with a blocked cell at (5, 4) — one step ahead of the token at (4, 4)
    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-mv/combat/start",
      payload: {
        actionId: "start-mv-1",
        combatants: [{ combatantId: "cmb_1", initiativeScore: 20 }],
        battleMap: {
          ...BASE_BATTLE_MAP,
          blockedCells: [{ x: 5, y: 4 }],
        },
      },
    });

    // Place a token and link it
    const encounter = repository.requireEncounter("session-mv");
    // Ensure we have a token to move — use the demo token (tok_player) already created
    // Link tok_player to cmb_1
    await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-mv/tokens",
      payload: {
        tokens: [{ tokenId: "tok_player", combatantId: "cmb_1" }],
      },
    });

    // Attempt to move tok_player into the blocked cell (5, 4)
    const encounterVersion = repository.requireEncounter("session-mv").combatState.version;
    const moveResp = await app.inject({
      method: "POST",
      url: "/sessions/session-mv/actions/movement",
      headers: {
        "x-limiar-actor-id": "player_1",
        "x-limiar-actor-type": "player",
      },
      payload: {
        actionId: "move-blocked-1",
        sessionId: "session-mv",
        tokenId: "tok_player",
        path: [{ x: 5, y: 4 }],
        knownVersion: encounterVersion,
      },
    });

    expect(moveResp.statusCode).toBe(200);
    // Rejection is communicated via the response snapshot — token position unchanged
    const after = repository.requireEncounter("session-mv");
    const token = after.tokens.find((t) => t.id === "tok_player");
    expect(token?.position).not.toEqual({ x: 5, y: 4 });

    await app.close();
  });

  it("movement through a blocked intermediate cell is rejected", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);
    const { registerRealtimeRoutes } = await import("../../src/routes/realtime-routes");
    registerRealtimeRoutes(app, repository);

    // Block cell (5, 4) — token at (4, 4) will try to move through it to (6, 4)
    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-thru/combat/start",
      payload: {
        actionId: "start-thru-1",
        combatants: [{ combatantId: "cmb_1", initiativeScore: 20 }],
        battleMap: {
          ...BASE_BATTLE_MAP,
          blockedCells: [{ x: 5, y: 4 }],
        },
      },
    });
    await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-thru/tokens",
      payload: { tokens: [{ tokenId: "tok_player", combatantId: "cmb_1" }] },
    });

    const versionThru = repository.requireEncounter("session-thru").combatState.version;
    const moveResp = await app.inject({
      method: "POST",
      url: "/sessions/session-thru/actions/movement",
      headers: { "x-limiar-actor-id": "player_1", "x-limiar-actor-type": "player" },
      payload: {
        actionId: "move-thru-1",
        sessionId: "session-thru",
        tokenId: "tok_player",
        // path goes through blocked (5,4) en route to (6,4)
        path: [{ x: 5, y: 4 }, { x: 6, y: 4 }],
        knownVersion: versionThru,
      },
    });

    expect(moveResp.statusCode).toBe(200);
    const after = repository.requireEncounter("session-thru");
    const token = after.tokens.find((t) => t.id === "tok_player");
    // Token must not have moved to (6, 4) — original position (4, 4) retained
    expect(token?.position).not.toEqual({ x: 6, y: 4 });
    expect(token?.position).not.toEqual({ x: 5, y: 4 });

    await app.close();
  });

  it("valid movement around blocked cells still works", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);
    const { registerRealtimeRoutes } = await import("../../src/routes/realtime-routes");
    registerRealtimeRoutes(app, repository);

    // Block (5, 4) but move token from (4, 4) to (4, 5) — a clear orthogonal step
    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-valid/combat/start",
      payload: {
        actionId: "start-valid-1",
        combatants: [{ combatantId: "cmb_1", initiativeScore: 20 }],
        battleMap: {
          ...BASE_BATTLE_MAP,
          blockedCells: [{ x: 5, y: 4 }],
        },
      },
    });
    await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-valid/tokens",
      payload: { tokens: [{ tokenId: "tok_player", combatantId: "cmb_1" }] },
    });

    const versionValid = repository.requireEncounter("session-valid").combatState.version;
    const moveResp = await app.inject({
      method: "POST",
      url: "/sessions/session-valid/actions/movement",
      headers: { "x-limiar-actor-id": "player_1", "x-limiar-actor-type": "player" },
      payload: {
        actionId: "move-valid-1",
        sessionId: "session-valid",
        tokenId: "tok_player",
        path: [{ x: 4, y: 5 }],
        knownVersion: versionValid,
      },
    });

    expect(moveResp.statusCode).toBe(200);
    const after = repository.requireEncounter("session-valid");
    const token = after.tokens.find((t) => t.id === "tok_player");
    expect(token?.position).toEqual({ x: 4, y: 5 });

    await app.close();
  });

  it("out-of-bounds and duplicate cells are silently discarded", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);

    // gridWidth=20 gridHeight=14; cells (25,0), (0,20), (-1,3) are out-of-bounds; (3,5) is duplicate
    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-oob/combat/start",
      payload: {
        actionId: "start-oob-1",
        combatants: [{ combatantId: "player-1", initiativeScore: 10 }],
        battleMap: {
          ...BASE_BATTLE_MAP,
          blockedCells: [
            { x: 3, y: 5 },   // valid
            { x: 3, y: 5 },   // duplicate — discarded
            { x: 25, y: 0 },  // x >= gridWidth — discarded
            { x: 0, y: 20 },  // y >= gridHeight — discarded
          ],
        },
      },
    });

    const encounter = repository.requireEncounter("session-oob");
    const campaignObstacles = encounter.obstacles.filter((o) => o.id.startsWith("campaign-obstacle-"));
    // Only the single valid, non-duplicate cell survives
    expect(campaignObstacles).toHaveLength(1);
    expect(campaignObstacles[0].cells[0]).toEqual({ x: 3, y: 5 });

    await app.close();
  });

  it("combat start without blockedCells creates no campaign obstacles", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-nocells/combat/start",
      payload: {
        actionId: "start-nocells-1",
        combatants: [{ combatantId: "player-1", initiativeScore: 10 }],
        battleMap: BASE_BATTLE_MAP,
      },
    });

    const encounter = repository.requireEncounter("session-nocells");
    // No campaign-seeded obstacles (demo encounter already has obs_1, but this is a new encounter)
    const campaignObstacles = encounter.obstacles.filter((o) =>
      o.id.startsWith("campaign-obstacle-"),
    );
    expect(campaignObstacles).toHaveLength(0);

    await app.close();
  });
});
