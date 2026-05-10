import { describe, expect, it } from "vitest";
import { createApp } from "../../src/app";
import { registerIntegrationRoutes } from "../../src/routes/integration-routes";

const anchorA = {
  id: "spell_anchor:a",
  sourceSpellKey: "spiritual_weapon",
  sourceSpellName: "Arma Espiritual",
  ownerParticipantId: "p1",
  createdByParticipantId: "p1",
  position: { x: 12, y: 10 },
  durationType: "rounds",
  remainingRounds: 10,
  expiresOn: "turn_start",
  expiresAtParticipantId: "p1",
  renderKind: "generic",
  metadata: {},
};

const anchorB = {
  id: "spell_anchor:b",
  sourceSpellKey: "moonbeam",
  sourceSpellName: "Moonbeam",
  ownerParticipantId: "p2",
  createdByParticipantId: "p2",
  position: { x: 7, y: 4 },
  durationType: "rounds",
  remainingRounds: 5,
  expiresOn: "turn_end",
  expiresAtParticipantId: "p2",
  renderKind: "generic",
  metadata: { debugLabel: "replacement" },
};

describe("spell anchor sync integration", () => {
  it("syncs spell anchors through the integration route", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);
    repository.ensureEncounter("session-123");

    const response = await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-123/spell-anchors",
      payload: {
        spellAnchors: [anchorA],
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json().spellAnchors).toHaveLength(1);
    expect(response.json().spellAnchors[0]).toMatchObject({
      id: "spell_anchor:a",
      sourceSpellKey: "spiritual_weapon",
      ownerParticipantId: "p1",
      position: { x: 12, y: 10 },
      renderKind: "generic",
    });

    const stateResponse = await app.inject({
      method: "GET",
      url: "/integration/sessions/session-123/state",
    });
    expect(stateResponse.statusCode).toBe(200);
    expect(stateResponse.json().spellAnchors).toEqual([anchorA]);

    await app.close();
  });

  it("replaces spell anchors authoritatively on later sync", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);
    repository.ensureEncounter("session-123");

    const firstResponse = await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-123/spell-anchors",
      payload: {
        spellAnchors: [anchorA],
      },
    });
    expect(firstResponse.statusCode).toBe(200);

    const secondResponse = await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-123/spell-anchors",
      payload: {
        spellAnchors: [anchorB],
      },
    });
    expect(secondResponse.statusCode).toBe(200);
    expect(secondResponse.json().spellAnchors).toEqual([anchorB]);

    const stateResponse = await app.inject({
      method: "GET",
      url: "/integration/sessions/session-123/state",
    });
    expect(stateResponse.statusCode).toBe(200);
    expect(stateResponse.json().spellAnchors).toEqual([anchorB]);

    await app.close();
  });

  it("clears spell anchors when synced with an empty collection", async () => {
    const { app, repository } = createApp();
    registerIntegrationRoutes(app, repository);
    repository.ensureEncounter("session-123");

    const firstResponse = await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-123/spell-anchors",
      payload: {
        spellAnchors: [anchorA],
      },
    });
    expect(firstResponse.statusCode).toBe(200);

    const clearResponse = await app.inject({
      method: "PUT",
      url: "/integration/sessions/session-123/spell-anchors",
      payload: {
        spellAnchors: [],
      },
    });
    expect(clearResponse.statusCode).toBe(200);
    expect(clearResponse.json().spellAnchors).toEqual([]);

    const stateResponse = await app.inject({
      method: "GET",
      url: "/integration/sessions/session-123/state",
    });
    expect(stateResponse.statusCode).toBe(200);
    expect(stateResponse.json().spellAnchors).toEqual([]);

    await app.close();
  });
});
