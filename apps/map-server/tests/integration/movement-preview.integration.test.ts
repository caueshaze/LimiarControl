import { describe, expect, it } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";
import { MovementService } from "../../src/modules/encounters/movement-service";

const BASE_BATTLE_MAP = {
  name: "Dungeon Depths",
  gridWidth: 20,
  gridHeight: 14,
  gridCalibration: { x: 0, y: 0, width: 1, height: 1 },
  imageUrl: "/sessions/session-preview/battle-map/background",
  sourceImageUrl: "/api/assets/internal/campaigns/campaign-1/maps/asset123"
};

describe("integration movement preview", () => {
  it("returns a valid path with cost and remaining budget", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-preview/combat/start",
      payload: {
        actionId: "start-preview-1",
        combatants: [{ combatantId: "cmb_1", initiativeScore: 20 }],
        battleMap: BASE_BATTLE_MAP
      }
    });
    await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-preview/tokens",
      payload: { tokens: [{ tokenId: "tok_player", combatantId: "cmb_1" }] }
    });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-preview/movement/preview",
      payload: {
        actionId: "preview-move-1",
        combatantId: "cmb_1",
        destinationCell: { x: 6, y: 4 }
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: true,
      pathCostUnits: 10,
      movementBudget: 30,
      remainingBudget: 20,
      destinationCell: { x: 6, y: 4 },
      path: [
        { x: 5, y: 4 },
        { x: 6, y: 4 }
      ]
    });

    await app.close();
  });

  it("returns a clear invalid reason when the path exceeds budget", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-preview-budget/combat/start",
      payload: {
        actionId: "start-preview-2",
        combatants: [{ combatantId: "cmb_1", initiativeScore: 20 }],
        battleMap: BASE_BATTLE_MAP
      }
    });
    await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-preview-budget/tokens",
      payload: {
        tokens: [
          { tokenId: "tok_player", combatantId: "cmb_1", movementSpeedCells: 2 }
        ]
      }
    });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-preview-budget/movement/preview",
      payload: {
        actionId: "preview-move-2",
        combatantId: "cmb_1",
        destinationCell: { x: 7, y: 4 }
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "movement_budget_exceeded",
      pathCostUnits: 15,
      movementBudget: 10,
      remainingBudget: 0
    });

    await app.close();
  });

  it("rejects initial placement onto occupied, blocked, or out-of-bounds cells", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);

    const encounter = repository.createEncounter("session-placement");
    encounter.tokens = encounter.tokens.map((token) =>
      token.id === "tok_player"
        ? { ...token, position: { x: 1, y: 1 } }
        : token.id === "tok_enemy"
          ? { ...token, position: { x: 3, y: 3 } }
          : token
    );
    encounter.obstacles = [
      {
        id: "wall",
        battleMapId: encounter.battleMap.id,
        cells: [{ x: 2, y: 2 }],
        blocksMovement: true,
        blocksEffect: true,
        blocksVision: true,
        cover: "full",
        clipsDiagonalMovement: false,
        movementCostMultiplier: 1
      }
    ];
    repository.saveEncounter(encounter);

    const service = new MovementService(repository);

    expect(
      service.placeToken(
        "session-placement",
        "tok_player",
        { x: 3, y: 3 },
        "place-occupied"
      )
    ).toMatchObject({
      accepted: false,
      rejectionReason: "destination_occupied"
    });
    expect(
      service.placeToken(
        "session-placement",
        "tok_player",
        { x: 2, y: 2 },
        "place-blocked"
      )
    ).toMatchObject({ accepted: false, rejectionReason: "movement_blocked" });
    expect(
      service.placeToken(
        "session-placement",
        "tok_player",
        { x: 999, y: 3 },
        "place-oob"
      )
    ).toMatchObject({
      accepted: false,
      rejectionReason: "invalid_destination"
    });

    await app.close();
  });
});
