import { describe, expect, it } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

describe("combat/end clears combat-scoped state", () => {
  it("clears tokens and initiative order but preserves battleMap and obstacles", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: () => {} });

    const before = repository.requireEncounter("demo-session");
    expect(before.tokens.length).toBeGreaterThan(0);
    expect(before.obstacles.length).toBeGreaterThan(0);
    const battleMapIdBefore = before.battleMap.id;
    const obstacleCountBefore = before.obstacles.length;

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/demo-session/combat/end",
      payload: { actionId: "end-1" },
    });

    expect(response.statusCode).toBe(200);

    const after = repository.requireEncounter("demo-session");
    expect(after.tokens).toEqual([]);
    expect(after.combatState.status).toBe("completed");
    expect(after.combatState.activeCombatantId).toBeNull();
    expect(after.combatState.initiativeOrder).toEqual([]);
    expect(after.combatState.turnIndex).toBe(0);
    // map-scoped state survives
    expect(after.battleMap.id).toBe(battleMapIdBefore);
    expect(after.obstacles.length).toBe(obstacleCountBefore);

    await app.close();
  });

  it("a new combat started after end does not inherit tokens from the previous encounter", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: () => {} });

    const endRes = await app.inject({
      method: "POST",
      url: "/integration/sessions/demo-session/combat/end",
      payload: { actionId: "end-2" },
    });
    expect(endRes.statusCode).toBe(200);
    expect(repository.requireEncounter("demo-session").tokens).toEqual([]);

    const startRes = await app.inject({
      method: "POST",
      url: "/integration/sessions/demo-session/combat/start",
      payload: {
        actionId: "start-after-end-1",
        combatants: [{ combatantId: "cmb_new", initiativeScore: 12 }],
      },
    });
    expect(startRes.statusCode).toBe(200);

    const tokens = repository.requireEncounter("demo-session").tokens;
    // Nothing has spawned yet — only syncTokens spawns. The key assertion is
    // that stale pre-end tokens (tok_player, tok_enemy) are gone.
    expect(tokens.find((t) => t.id === "tok_player")).toBeUndefined();
    expect(tokens.find((t) => t.id === "tok_enemy")).toBeUndefined();

    await app.close();
  });
});
