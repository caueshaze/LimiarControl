import { describe, expect, it } from "vitest";

import type { ActiveSession } from "../../../shared/api/sessionsRepo";
import {
  beginActiveSessionRefresh,
  createInitialActiveSessionQueryState,
  resolveActiveSessionView,
} from "./useActiveSession.state";

const session = (id: string): ActiveSession =>
  ({
    id,
    campaignId: "camp-1",
    title: "Session",
    status: "ACTIVE",
    createdAt: "2026-04-19T00:00:00.000Z",
    activatedAt: "2026-04-19T00:00:00.000Z",
    partyId: "party-1",
  }) as ActiveSession;

describe("useActiveSession.state", () => {
  it("starts in loading state when a campaign is already known", () => {
    expect(createInitialActiveSessionQueryState("camp-1").loading).toBe(true);
    expect(createInitialActiveSessionQueryState(null).loading).toBe(false);
  });

  it("marks a new campaign as pending immediately and hides stale session data", () => {
    const current = {
      campaignId: "camp-1",
      activeSession: session("session-1"),
      loading: false,
      error: "stale error",
    };

    const nextView = resolveActiveSessionView(current, "camp-2");

    expect(nextView.loading).toBe(true);
    expect(nextView.activeSession).toBeNull();
    expect(nextView.error).toBeNull();
  });

  it("preserves the current session while refreshing the same campaign", () => {
    const current = {
      campaignId: "camp-1",
      activeSession: session("session-1"),
      loading: false,
      error: "old error",
    };

    const pending = beginActiveSessionRefresh(current, "camp-1");
    const pendingView = resolveActiveSessionView(pending, "camp-1");

    expect(pending.loading).toBe(true);
    expect(pending.error).toBeNull();
    expect(pendingView.activeSession?.id).toBe("session-1");
    expect(pendingView.loading).toBe(true);
  });
});
