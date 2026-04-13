import { describe, expect, it, vi } from "vitest";
import { createApp } from "../../src/app";
import { registerRealtimeRoutes } from "../../src/routes/realtime-routes";

describe("realtime http actions", () => {
  it("issues a centrifugo connection token for the map web client", async () => {
    const { app, repository } = createApp();
    registerRealtimeRoutes(app, repository);

    const response = await app.inject({
      method: "POST",
      url: "/centrifugo/connection-token",
      payload: {
        actorId: "gm_1",
        actorType: "gm",
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual({
      token: expect.any(String),
    });

    await app.close();
  });

  it("accepts movement over HTTP and emits the authoritative event envelope", async () => {
    const { app, repository } = createApp();
    const broadcaster = { emit: vi.fn() };
    registerRealtimeRoutes(app, repository, broadcaster);

    const response = await app.inject({
      method: "POST",
      url: "/sessions/demo-session/actions/movement",
      headers: {
        "x-limiar-actor-id": "player_1",
        "x-limiar-actor-type": "player",
      },
      payload: {
        actionId: "move-http-1",
        sessionId: "demo-session",
        tokenId: "tok_player",
        path: [{ x: 5, y: 4 }],
        knownVersion: 1,
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      combatState: {
        version: 2,
      },
    });
    expect(broadcaster.emit).toHaveBeenCalledWith(
      "movement.applied",
      expect.objectContaining({
        eventType: "movement.applied",
        encounterId: "demo-session",
        actionId: "move-http-1",
      }),
    );

    await app.close();
  });

  it("accepts combat advance over HTTP using the existing limiarControl authority", async () => {
    const { app, repository } = createApp();
    const broadcaster = { emit: vi.fn() };
    registerRealtimeRoutes(app, repository, broadcaster);

    const response = await app.inject({
      method: "POST",
      url: "/sessions/demo-session/actions/combat/advance",
      payload: {
        actionId: "combat-http-1",
        sessionId: "demo-session",
        knownVersion: 1,
        requestedBy: "limiarControl",
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      combatState: {
        version: 2,
        turnIndex: 1,
      },
    });
    expect(broadcaster.emit).toHaveBeenCalledWith(
      "combat.advanced",
      expect.objectContaining({
        eventType: "combat.advanced",
        encounterId: "demo-session",
        actionId: "combat-http-1",
      }),
    );

    await app.close();
  });

  it("rejects realtime targeting when line of effect is blocked and emits a machine-readable reason", async () => {
    const { app, repository } = createApp();
    const broadcaster = { emit: vi.fn() };
    registerRealtimeRoutes(app, repository, broadcaster);

    const encounter = repository.createEncounter("session-target-http");
    encounter.combatState = {
      ...encounter.combatState,
      status: "active",
      roundNumber: 1,
      activeCombatantId: "cmb_1",
      initiativeOrder: ["cmb_1", "cmb_2"],
      version: 1,
    };
    encounter.obstacles = [
      {
        id: "effect-wall",
        battleMapId: encounter.battleMap.id,
        label: "Barreira de efeito",
        cells: [{ x: 1, y: 0 }],
        blocksMovement: false,
        blocksEffect: true,
        blocksVision: false,
        cover: "none",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1,
      },
    ];
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/sessions/session-target-http/actions/targeting",
      headers: {
        "x-limiar-actor-id": "player_1",
        "x-limiar-actor-type": "player",
      },
      payload: {
        actionId: "target-http-1",
        sessionId: "session-target-http",
        tokenId: "tok_player",
        shape: "line",
        originCell: { x: 0, y: 0 },
        anchorCell: { x: 3, y: 0 },
        rangeCells: 5,
        sizeCells: 1,
        knownVersion: 1,
        requiresEffect: true,
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      combatState: {
        version: 1,
      },
    });
    expect(broadcaster.emit).toHaveBeenCalledWith(
      "action.rejected",
      expect.objectContaining({
        eventType: "action.rejected",
        encounterId: "session-target-http",
        actionId: "target-http-1",
        payload: expect.objectContaining({
          reason: "no_line_of_effect",
        }),
      }),
    );

    await app.close();
  });
});
