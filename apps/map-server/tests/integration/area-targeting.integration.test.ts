import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

describe("area targeting integration", () => {
  afterEach(async () => {
    vi.restoreAllMocks();
  });

  it("resolves a sphere area and returns affected tokens and combatants", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/demo-session/targeting/area",
      payload: {
        actionId: "area-1",
        combatantId: "cmb_1",
        shape: "sphere",
        originCell: { x: 4, y: 4 },
        anchorCell: { x: 10, y: 10 },
        rangeCells: 45,
        sizeCells: 1
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: true,
      shape: "sphere",
      sourceTokenId: "tok_player",
      affectedTokenIds: ["tok_enemy"],
      affectedCombatantIds: ["cmb_2"]
    });

    await app.close();
  });

  it("rejects out-of-range area targeting without mutating combat state", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const beforeVersion = repository.requireEncounter("demo-session").combatState.version;
    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/demo-session/targeting/area",
      payload: {
        actionId: "area-2",
        combatantId: "cmb_1",
        shape: "sphere",
        originCell: { x: 4, y: 4 },
        anchorCell: { x: 10, y: 10 },
        rangeCells: 2,
        sizeCells: 1
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "out_of_range",
      affectedTokenIds: [],
      affectedCombatantIds: []
    });
    expect(repository.requireEncounter("demo-session").combatState.version).toBe(beforeVersion);

    await app.close();
  });

  it("previews a sphere area without mutating combat state", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const beforeVersion = repository.requireEncounter("demo-session").combatState.version;
    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/demo-session/targeting/area/preview",
      payload: {
        actionId: "area-preview-1",
        combatantId: "cmb_1",
        shape: "sphere",
        originCell: { x: 4, y: 4 },
        anchorCell: { x: 10, y: 10 },
        rangeCells: 45,
        sizeCells: 1
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: true,
      shape: "sphere",
      sourceTokenId: "tok_player",
      affectedTokenIds: ["tok_enemy"],
      affectedCombatantIds: ["cmb_2"]
    });
    expect(repository.requireEncounter("demo-session").combatState.version).toBe(beforeVersion);

    await app.close();
  });

  it("rejects area targeting when line of effect to the anchor is blocked", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/demo-session/targeting/area",
      payload: {
        actionId: "area-loe-1",
        combatantId: "cmb_1",
        shape: "sphere",
        originCell: { x: 4, y: 4 },
        anchorCell: { x: 10, y: 10 },
        rangeCells: 45,
        sizeCells: 1,
        requiresEffect: true
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "no_line_of_effect",
      affectedCells: [],
      affectedTokenIds: [],
      affectedCombatantIds: []
    });

    await app.close();
  });

  it("rejects preview when line of effect to the anchor is blocked", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/demo-session/targeting/area/preview",
      payload: {
        actionId: "area-preview-loe-1",
        combatantId: "cmb_1",
        shape: "sphere",
        originCell: { x: 4, y: 4 },
        anchorCell: { x: 10, y: 10 },
        rangeCells: 45,
        sizeCells: 1,
        requiresEffect: true
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "no_line_of_effect",
      affectedCells: [],
      affectedTokenIds: [],
      affectedCombatantIds: []
    });

    await app.close();
  });
});
