import { describe, expect, it, vi } from "vitest";
import type { Coordinate, Obstacle } from "@limiarmap/shared-contracts";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

function createObstacle(
  battleMapId: string,
  id: string,
  cells: Coordinate[],
  overrides?: Partial<Obstacle>
): Obstacle {
  return {
    id,
    battleMapId,
    cells,
    blocksMovement: false,
    blocksEffect: false,
    blocksVision: false,
    cover: "none",
    clipsDiagonalMovement: false,
    movementCostMultiplier: 1,
    ...overrides
  };
}

describe("single-target targeting integration", () => {
  it("rejects actions that require sight when line of sight is blocked", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("session-los");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    encounter.obstacles = [
      createObstacle(encounter.battleMap.id, "vision-only", [{ x: 1, y: 0 }], { blocksVision: true })
    ];
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-los/targeting",
      payload: {
        actionId: "target-los-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5,
        requiresSight: true
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "no_line_of_sight",
      sourceTokenId: "tok_player",
      targetTokenId: "tok_enemy"
    });

    await app.close();
  });

  it("rejects actions that require effect when line of effect is blocked", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("session-loe");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    encounter.obstacles = [
      createObstacle(encounter.battleMap.id, "effect-only", [{ x: 1, y: 0 }], { blocksEffect: true })
    ];
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-loe/targeting",
      payload: {
        actionId: "target-loe-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5,
        requiresEffect: true
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "no_line_of_effect",
      sourceTokenId: "tok_player",
      targetTokenId: "tok_enemy"
    });

    await app.close();
  });

  it("still accepts actions that require effect but not sight behind a vision-only obstacle", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("session-effect-only");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    encounter.obstacles = [
      createObstacle(encounter.battleMap.id, "vision-only", [{ x: 1, y: 0 }], { blocksVision: true })
    ];
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-effect-only/targeting",
      payload: {
        actionId: "target-effect-only-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5,
        requiresEffect: true,
        requiresSight: false
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: true,
      reason: null,
      sourceTokenId: "tok_player",
      targetTokenId: "tok_enemy"
    });

    await app.close();
  });

  it("reports half cover when an obstacle with cover=half is between source and target", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("session-half-cover");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    encounter.obstacles = [
      createObstacle(encounter.battleMap.id, "barricade", [{ x: 2, y: 0 }], { cover: "half" })
    ];
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-half-cover/targeting",
      payload: {
        actionId: "target-half-cover-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: true,
      reason: null,
      cover: "half",
      sourceTokenId: "tok_player",
      targetTokenId: "tok_enemy"
    });

    await app.close();
  });

  it("reports threeQuarters cover when a 3/4-cover obstacle is between source and target", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("session-3q-cover");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    encounter.obstacles = [
      createObstacle(encounter.battleMap.id, "dense-cover", [{ x: 1, y: 0 }], { cover: "threeQuarters" })
    ];
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-3q-cover/targeting",
      payload: {
        actionId: "target-3q-cover-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: true,
      reason: null,
      cover: "threeQuarters",
      sourceTokenId: "tok_player",
      targetTokenId: "tok_enemy"
    });

    await app.close();
  });

  it("rejects a direct targeted attack with full cover", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("session-full-cover");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    encounter.obstacles = [
      createObstacle(encounter.battleMap.id, "full-wall", [{ x: 2, y: 0 }], { cover: "full" })
    ];
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-full-cover/targeting",
      payload: {
        actionId: "target-full-cover-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "full_cover",
      cover: "full",
      sourceTokenId: "tok_player",
      targetTokenId: "tok_enemy"
    });

    await app.close();
  });

  it("returns cover=none for backward compatibility when no cover obstacles exist", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("session-no-cover");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-no-cover/targeting",
      payload: {
        actionId: "target-no-cover-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5
      }
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      isValid: true,
      reason: null,
      cover: "none"
    });

    await app.close();
  });

  it("LoS hard block still prevails when cover is also present", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository, { emit: vi.fn() });

    const encounter = repository.createEncounter("session-los-cover");
    encounter.tokens = encounter.tokens.map((token) =>
      token.combatantId === "cmb_1"
        ? { ...token, position: { x: 0, y: 0 } }
        : token.combatantId === "cmb_2"
          ? { ...token, position: { x: 3, y: 0 } }
          : token
    );
    encounter.obstacles = [
      // This obstacle blocks vision AND has half cover. LoS should reject first.
      createObstacle(encounter.battleMap.id, "vision-cover", [{ x: 1, y: 0 }], {
        blocksVision: true,
        cover: "half"
      })
    ];
    repository.saveEncounter(encounter);

    const response = await app.inject({
      method: "POST",
      url: "/integration/sessions/session-los-cover/targeting",
      payload: {
        actionId: "target-los-cover-1",
        combatantId: "cmb_1",
        targetCombatantId: "cmb_2",
        rangeCells: 5,
        requiresSight: true
      }
    });

    expect(response.statusCode).toBe(200);
    // LoS rejection prevails — cover is not even evaluated
    expect(response.json()).toMatchObject({
      isValid: false,
      reason: "no_line_of_sight"
    });

    await app.close();
  });
});

