import { describe, expect, it, vi } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

function fogCloudPayload(cells: { x: number; y: number }[]) {
  return {
    activeAreaEffects: [
      {
        id: "area_effect:fog",
        sourceSpellCanonicalKey: "fog_cloud",
        sourceSpellName: "Fog Cloud",
        casterParticipantId: "p1",
        casterRefId: "player-123",
        originPoint: cells[0],
        anchorCell: cells[0],
        areaShape: "sphere",
        sizeMeters: 6,
        radiusMeters: 6,
        affectedCells: cells,
        effectKind: "obscurement",
        obscurement: "heavily_obscured"
      }
    ]
  };
}

async function syncFogCloud(
  app: ReturnType<typeof createApp>["app"],
  sessionId: string,
  cells: { x: number; y: number }[]
) {
  const r = await app.inject({
    method: "PUT",
    url: `/integration/sessions/${sessionId}/area-effects`,
    payload: fogCloudPayload(cells)
  });
  expect(r.statusCode).toBe(200);
}

describe("Fog Cloud targeting integration", () => {
  it("blocks single-target sight when target stands inside Fog Cloud", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("fog-target");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    repository.saveEncounter(encounter);

    await syncFogCloud(app, "fog-target", [{ x: 3, y: 0 }]);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/fog-target/targeting",
      payload: {
        actionId: "target-fog-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 10,
        requiresSight: true
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "target_heavily_obscured"
    });

    await app.close();
  });

  it("blocks single-target sight when caster stands inside Fog Cloud", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("fog-origin");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    repository.saveEncounter(encounter);

    await syncFogCloud(app, "fog-origin", [{ x: 0, y: 0 }]);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/fog-origin/targeting",
      payload: {
        actionId: "target-fog-2",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 10,
        requiresSight: true
      }
    });

    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "origin_heavily_obscured"
    });
    await app.close();
  });

  it("blocks single-target sight when LoS path crosses Fog Cloud", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("fog-cross");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 4, y: 0 } }
          : token
    );
    repository.saveEncounter(encounter);

    await syncFogCloud(app, "fog-cross", [{ x: 2, y: 0 }]);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/fog-cross/targeting",
      payload: {
        actionId: "target-fog-3",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 10,
        requiresSight: true
      }
    });

    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "line_of_sight_obscured"
    });
    await app.close();
  });

  it("does not block targeting when requiresSight is false", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("fog-nosight");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    repository.saveEncounter(encounter);

    await syncFogCloud(app, "fog-nosight", [{ x: 3, y: 0 }]);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/fog-nosight/targeting",
      payload: {
        actionId: "target-fog-4",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 10,
        requiresSight: false
      }
    });

    expect(response.json()).toMatchObject({ isValid: true, reason: null });
    await app.close();
  });

  it("blocks area preview point sight when anchor cell is inside Fog Cloud", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("fog-area");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token
    );
    repository.saveEncounter(encounter);

    await syncFogCloud(app, "fog-area", [{ x: 4, y: 0 }]);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/fog-area/targeting/area/preview",
      payload: {
        actionId: "preview-fog-area-1",
        combatantId: "cmb_1",
        shape: "sphere",
        originCell: { x: 0, y: 0 },
        anchorCell: { x: 4, y: 0 },
        rangeCells: 10,
        sizeCells: 2,
        requiresSight: true
      }
    });

    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "point_heavily_obscured"
    });
    await app.close();
  });

  it("does not affect targeting for Spike Growth (hazard, not obscurement)", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("spike-sight");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    repository.saveEncounter(encounter);

    await app.inject({
      method: "PUT",
      url: "/integration/sessions/spike-sight/area-effects",
      payload: {
        activeAreaEffects: [
          {
            id: "area_effect:spike",
            sourceSpellCanonicalKey: "spike_growth",
            sourceSpellName: "Spike Growth",
            casterParticipantId: "p1",
            casterRefId: "player-123",
            originPoint: { x: 2, y: 0 },
            anchorCell: { x: 2, y: 0 },
            areaShape: "sphere",
            sizeMeters: 6,
            radiusMeters: 6,
            affectedCells: [{ x: 2, y: 0 }],
            effectKind: "hazard",
            terrainEffect: "difficult_terrain",
            movementDamageDice: "2d4",
            damageType: "Piercing",
            damagePerMeters: 1.5
          }
        ]
      }
    });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/spike-sight/targeting",
      payload: {
        actionId: "target-spike-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 10,
        requiresSight: true
      }
    });

    expect(response.json()).toMatchObject({ isValid: true, reason: null });
    await app.close();
  });
});
