import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

type Shape = "sphere" | "cone" | "line" | "cube" | "cylinder";

const BASE_PAYLOAD = {
  combatantId: "cmb_1",
  originCell: { x: 4, y: 4 },
  anchorCell: { x: 10, y: 10 },
  rangeCells: 45,
  sizeCells: 3,
};

async function postArea(app: ReturnType<typeof createApp>["app"], path: "area" | "area/preview", payload: Record<string, unknown>) {
  return app.inject({
    method: "POST",
    url: `/integration/sessions/demo-session/targeting/${path}`,
    payload,
  });
}

describe("area targeting preview/cast parity", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  for (const shape of ["sphere", "cone", "line", "cube", "cylinder"] satisfies Shape[]) {
    it(`${shape}: preview affected_cells match final cast`, async () => {
      const { app, repository } = createApp();
      registerIntegrationRoutes(app, repository, { emit: vi.fn() });

      const beforeVersion = repository.requireEncounter("demo-session").combatState.version;

      const previewRes = await postArea(app, "area/preview", {
        ...BASE_PAYLOAD,
        actionId: `parity-${shape}-preview`,
        shape,
      });
      expect(previewRes.statusCode).toBe(200);
      const previewBody = previewRes.json();
      expect(previewBody.isValid).toBe(true);
      expect(repository.requireEncounter("demo-session").combatState.version).toBe(beforeVersion);

      const castRes = await postArea(app, "area", {
        ...BASE_PAYLOAD,
        actionId: `parity-${shape}-cast`,
        shape,
      });
      expect(castRes.statusCode).toBe(200);
      const castBody = castRes.json();
      expect(castBody.isValid).toBe(true);

      expect(castBody.affectedCells).toEqual(previewBody.affectedCells);
      expect(castBody.affectedTokenIds).toEqual(previewBody.affectedTokenIds);
      expect(castBody.affectedCombatantIds).toEqual(previewBody.affectedCombatantIds);

      await app.close();
    });

    it(`${shape}: consecutive previews are stable and do not mutate state`, async () => {
      const { app, repository } = createApp();
      registerIntegrationRoutes(app, repository, { emit: vi.fn() });

      const beforeVersion = repository.requireEncounter("demo-session").combatState.version;

      const first = await postArea(app, "area/preview", {
        ...BASE_PAYLOAD,
        actionId: `stable-${shape}-1`,
        shape,
      });
      const second = await postArea(app, "area/preview", {
        ...BASE_PAYLOAD,
        actionId: `stable-${shape}-2`,
        shape,
      });

      expect(first.json().affectedCells).toEqual(second.json().affectedCells);
      expect(first.json().affectedTokenIds).toEqual(second.json().affectedTokenIds);
      expect(repository.requireEncounter("demo-session").combatState.version).toBe(beforeVersion);

      await app.close();
    });

    it(`${shape}: out-of-range preview is invalid with a reason and no affected cells`, async () => {
      const { app, repository } = createApp();
      registerIntegrationRoutes(app, repository, { emit: vi.fn() });

      const response = await postArea(app, "area/preview", {
        ...BASE_PAYLOAD,
        actionId: `oor-${shape}`,
        shape,
        rangeCells: 2,
      });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toMatchObject({
        isValid: false,
        reason: "out_of_range",
        shape,
        affectedCells: [],
        affectedTokenIds: [],
        affectedCombatantIds: [],
      });

      await app.close();
    });
  }
});
