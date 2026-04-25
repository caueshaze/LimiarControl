import { describe, expect, it } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

describe("active area effects integration", () => {
  it("stores synced persistent spell area effects and returns them in state", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);
    repository.ensureEncounter("session-123");

    const response = await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-123/area-effects",
      payload: {
        activeAreaEffects: [
          {
            id: "area_effect:1",
            sourceSpellCanonicalKey: "spike_growth",
            sourceSpellName: "Spike Growth",
            casterParticipantId: "p1",
            casterRefId: "player-123",
            originPoint: { x: 12, y: 12 },
            anchorCell: { x: 12, y: 12 },
            areaShape: "sphere",
            sizeMeters: 6,
            radiusMeters: 6,
            affectedCells: [{ x: 12, y: 12 }],
            effectKind: "hazard",
            terrainEffect: "difficult_terrain",
            movementDamageDice: "2d4",
            damageType: "Piercing",
            damagePerMeters: 1.5,
          },
        ],
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json().activeAreaEffects).toHaveLength(1);
    expect(response.json().activeAreaEffects[0]).toMatchObject({
      sourceSpellCanonicalKey: "spike_growth",
      effectKind: "hazard",
      terrainEffect: "difficult_terrain",
    });

    const stateResponse = await app.inject({
      method: "GET",
      url: "/integration/sessions/session-123/state",
    });
    expect(stateResponse.json().activeAreaEffects).toHaveLength(1);

    await app.close();
  });

  it("clears active area effects when combat ends", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);
    repository.ensureEncounter("session-123");
    repository.setActiveAreaEffects("session-123", [
      {
        id: "area_effect:1",
        sourceSpellCanonicalKey: "fog_cloud",
        sourceSpellName: "Fog Cloud",
        casterParticipantId: "p1",
        originPoint: { x: 10, y: 10 },
        anchorCell: { x: 10, y: 10 },
        areaShape: "sphere",
        sizeMeters: 6,
        radiusMeters: 6,
        affectedCells: [{ x: 10, y: 10 }],
        effectKind: "obscurement",
        obscurement: "heavily_obscured",
      },
    ]);

    await app.inject({
      method: "POST",
      url: "/integration/sessions/session-123/combat/start",
      payload: {
        actionId: "start-1",
        combatants: [{ combatantId: "player-123", initiativeScore: 18 }],
      },
    });
    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-123/combat/end",
      payload: { actionId: "end-1" },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json().activeAreaEffects).toEqual([]);

    await app.close();
  });
});
