import { describe, expect, it } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

describe("combat start battle map integration", () => {
  it("bootstraps a new encounter and persists the selected battle map", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-123/combat/start",
      payload: {
        actionId: "control-combat-start:combat-123",
        combatants: [{ combatantId: "player-123", initiativeScore: 18 }],
        battleMap: {
          name: "Dungeon Depths",
          gridWidth: 32,
          gridHeight: 24,
          gridCalibration: {
            x: 0.1,
            y: 0.2,
            width: 0.7,
            height: 0.6,
          },
          imageUrl: "/sessions/session-123/battle-map/background",
          sourceImageUrl: "/api/assets/internal/campaigns/campaign-123/maps/asset123",
        },
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      sessionId: "session-123",
      battleMap: {
        name: "Dungeon Depths",
        gridWidth: 32,
        gridHeight: 24,
        imageUrl: "/sessions/session-123/battle-map/background",
      },
      combatState: {
        status: "active",
        initiativeOrder: ["player-123"],
      },
    });

    const encounter = repository.requireEncounter("session-123");
    expect(encounter.battleMap.imageUrl).toBe("/sessions/session-123/battle-map/background");
    expect(encounter.battleMapSourceImageUrl).toBe(
      "/api/assets/internal/campaigns/campaign-123/maps/asset123",
    );

    await app.close();
  });
});
