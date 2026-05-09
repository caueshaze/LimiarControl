import { describe, expect, it } from "vitest";
import { consumeCampaignEvent } from "./campaignEventConsumption";

describe("consumeCampaignEvent", () => {
  it("consome apenas uma vez o mesmo evento versionado por escopo", () => {
    expect(
      consumeCampaignEvent({
        scope: "player-party-test",
        eventType: "session_started",
        sessionId: "sess-1",
        version: 7,
      }),
    ).toBe(true);

    expect(
      consumeCampaignEvent({
        scope: "player-party-test",
        eventType: "session_started",
        sessionId: "sess-1",
        version: 7,
      }),
    ).toBe(false);
  });

  it("aceita uma nova versão do mesmo evento", () => {
    expect(
      consumeCampaignEvent({
        scope: "player-board-test",
        eventType: "session_resumed",
        sessionId: "sess-1",
        version: 8,
      }),
    ).toBe(true);

    expect(
      consumeCampaignEvent({
        scope: "player-board-test",
        eventType: "session_resumed",
        sessionId: "sess-1",
        version: 9,
      }),
    ).toBe(true);
  });

  it("mantém escopos independentes", () => {
    expect(
      consumeCampaignEvent({
        scope: "player-party-scope-a",
        eventType: "session_started",
        sessionId: "sess-2",
        version: 3,
      }),
    ).toBe(true);

    expect(
      consumeCampaignEvent({
        scope: "player-party-scope-b",
        eventType: "session_started",
        sessionId: "sess-2",
        version: 3,
      }),
    ).toBe(true);
  });
});
