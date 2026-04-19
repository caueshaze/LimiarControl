import { beforeEach, describe, expect, it, vi } from "vitest";

const { broadcastAuthoritativeEvent } = vi.hoisted(() => ({
  broadcastAuthoritativeEvent: vi.fn(),
}));

vi.mock("../../src/modules/realtime/broadcast", async () => {
  const actual = await vi.importActual<typeof import("../../src/modules/realtime/broadcast")>(
    "../../src/modules/realtime/broadcast"
  );

  return {
    ...actual,
    broadcastAuthoritativeEvent,
  };
});

import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

describe("integration movement broadcast", () => {
  beforeEach(() => {
    broadcastAuthoritativeEvent.mockClear();
  });

  it("emits movement.applied for control-server movement confirms even without a broadcaster", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-move-broadcast/combat/start",
      payload: {
        actionId: "start-move-broadcast-1",
        combatants: [{ combatantId: "cmb_1", initiativeScore: 20 }],
        battleMap: {
          name: "Dungeon Depths",
          gridWidth: 20,
          gridHeight: 14,
          gridCalibration: { x: 0, y: 0, width: 1, height: 1 },
          imageUrl: "/sessions/session-move-broadcast/battle-map/background",
          sourceImageUrl: "/api/assets/internal/campaigns/campaign-1/maps/asset123",
        },
      },
    });

    await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-move-broadcast/tokens",
      payload: { tokens: [{ tokenId: "tok_player", combatantId: "cmb_1" }] },
    });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-move-broadcast/movement",
      payload: {
        actionId: "move-broadcast-1",
        combatantId: "cmb_1",
        destinationCell: { x: 5, y: 4 },
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: true,
      destinationCell: { x: 5, y: 4 },
    });
    expect(broadcastAuthoritativeEvent).toHaveBeenCalledWith(
      undefined,
      "movement.applied",
      expect.objectContaining({
        eventType: "movement.applied",
        encounterId: "session-move-broadcast",
        actionId: "move-broadcast-1",
        payload: expect.objectContaining({
          tokenId: "tok_player",
          position: { x: 5, y: 4 },
        }),
      }),
    );

    await app.close();
  });
});
