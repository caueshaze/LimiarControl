import { describe, expect, it } from "vitest";
import { resolveCharacterSheetPageContext } from "./characterSheetPageContext";

describe("resolveCharacterSheetPageContext", () => {
  it("treats another player in play mode as GM-managed even when global role is PLAYER", () => {
    const result = resolveCharacterSheetPageContext({
      requestedMode: "play",
      requestedPlayerId: "player-2",
      requestedCampaignId: "campaign-1",
      requestedReturnTo: null,
      requestedPlayerName: "Mage",
      viewerUserId: "gm-1",
      viewerRole: "PLAYER",
      partyId: "party-1",
      backToBoardLabel: "Back to board",
      backToPartyLabel: "Back to party",
    });

    expect(result.playPlayerUserId).toBe("player-2");
    expect(result.creationPlayerUserId).toBeNull();
    expect(result.canEditPlay).toBe(true);
    expect(result.playContextLabel).toBe("Mage");
    expect(result.backHref).toBe("/gm/campaigns/campaign-1/dashboard?partyId=party-1");
  });

  it("keeps the authenticated player on their own play sheet", () => {
    const result = resolveCharacterSheetPageContext({
      requestedMode: "play",
      requestedPlayerId: null,
      requestedCampaignId: null,
      requestedReturnTo: "board",
      requestedPlayerName: null,
      viewerUserId: "player-1",
      viewerRole: "PLAYER",
      partyId: "party-1",
      backToBoardLabel: "Back to board",
      backToPartyLabel: "Back to party",
    });

    expect(result.playPlayerUserId).toBe("player-1");
    expect(result.canEditPlay).toBe(false);
    expect(result.backHref).toBe("/board/party-1");
    expect(result.backLabel).toBe("Back to board");
  });

  it("routes creation inspection to the selected player", () => {
    const result = resolveCharacterSheetPageContext({
      requestedMode: "creation",
      requestedPlayerId: "player-2",
      requestedCampaignId: "campaign-1",
      requestedReturnTo: null,
      requestedPlayerName: null,
      viewerUserId: "gm-1",
      viewerRole: "PLAYER",
      partyId: "party-1",
      backToBoardLabel: "Back to board",
      backToPartyLabel: "Back to party",
    });

    expect(result.creationPlayerUserId).toBe("player-2");
    expect(result.playPlayerUserId).toBeNull();
    expect(result.canEditPlay).toBe(false);
    expect(result.backHref).toBe("/gm/campaigns/campaign-1/dashboard?partyId=party-1");
  });
});
