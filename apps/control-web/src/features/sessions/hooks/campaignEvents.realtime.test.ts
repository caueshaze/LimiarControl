import { describe, expect, it } from "vitest";

import {
  getCampaignEventVersionKey,
  isSupportedCampaignEventType,
} from "./campaignEvents.realtime";

describe("campaignEvents.realtime", () => {
  it("supports XP, rest, and level-up events", () => {
    expect(isSupportedCampaignEventType("gm_granted_xp")).toBe(true);
    expect(isSupportedCampaignEventType("rest_started")).toBe(true);
    expect(isSupportedCampaignEventType("rest_ended")).toBe(true);
    expect(isSupportedCampaignEventType("hit_dice_used")).toBe(true);
    expect(isSupportedCampaignEventType("level_up_requested")).toBe(true);
    expect(isSupportedCampaignEventType("level_up_approved")).toBe(true);
    expect(isSupportedCampaignEventType("level_up_denied")).toBe(true);
  });

  it("builds stable version keys for progression and rest events", () => {
    expect(
      getCampaignEventVersionKey("camp-1", {
        type: "gm_granted_xp",
        payload: { sessionId: "sess-1", playerUserId: "player-1" },
      }),
    ).toBe("gm_granted_xp:sess-1:player-1");

    expect(
      getCampaignEventVersionKey("camp-1", {
        type: "level_up_approved",
        payload: { partyId: "party-1", playerUserId: "player-1" },
      }),
    ).toBe("level_up_approved:party-1:player-1");

    expect(
      getCampaignEventVersionKey("camp-1", {
        type: "rest_started",
        payload: { sessionId: "sess-1" },
      }),
    ).toBe("rest_started:sess-1");

    expect(
      getCampaignEventVersionKey("camp-1", {
        type: "hit_dice_used",
        payload: { sessionId: "sess-1", playerUserId: "player-1" },
      }),
    ).toBe("hit_dice_used:sess-1:player-1");
  });
});
