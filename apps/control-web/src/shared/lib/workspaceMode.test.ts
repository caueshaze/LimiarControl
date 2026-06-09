import { describe, expect, it } from "vitest";
import {
  getWorkspaceModeButtonOrder,
  resolveEffectiveWorkspaceMode,
} from "./workspaceMode";

describe("workspaceMode", () => {
  it("prioritizes the persisted user preference", () => {
    expect(
      resolveEffectiveWorkspaceMode({
        preferredWorkspaceMode: "PLAYER",
        legacyWorkspaceMode: "GM",
        hasGmCampaign: true,
      }),
    ).toBe("PLAYER");
  });

  it("falls back to the legacy local preference when the profile has none", () => {
    expect(
      resolveEffectiveWorkspaceMode({
        preferredWorkspaceMode: null,
        legacyWorkspaceMode: "GM",
        hasGmCampaign: false,
      }),
    ).toBe("GM");
  });

  it("defaults to GM when the user has at least one GM campaign", () => {
    expect(
      resolveEffectiveWorkspaceMode({
        preferredWorkspaceMode: null,
        legacyWorkspaceMode: null,
        hasGmCampaign: true,
      }),
    ).toBe("GM");
  });

  it("defaults to PLAYER when the user has no GM campaigns", () => {
    expect(
      resolveEffectiveWorkspaceMode({
        preferredWorkspaceMode: null,
        legacyWorkspaceMode: null,
        hasGmCampaign: false,
      }),
    ).toBe("PLAYER");
  });

  it("keeps the active mode on the left side of the switch", () => {
    expect(getWorkspaceModeButtonOrder("GM")).toEqual(["GM", "PLAYER"]);
    expect(getWorkspaceModeButtonOrder("PLAYER")).toEqual(["PLAYER", "GM"]);
  });
});
