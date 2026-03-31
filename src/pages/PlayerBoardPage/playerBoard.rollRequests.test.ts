import { describe, expect, it } from "vitest";
import type {
  ActivityEvent,
  RollRequestActivityEvent,
} from "../../shared/api/sessionsRepo";
import {
  buildActivityRollRequestKey,
  findLatestPendingRollRequest,
  isActivityRequestAlreadyResolved,
} from "./playerBoard.rollRequests";

const requestEvent: RollRequestActivityEvent = {
  type: "roll_request",
  expression: "1d20",
  reason: "Teste legado",
  mode: null,
  targetUserId: "player-1",
  timestamp: "2026-03-30T22:00:00Z",
  sessionOffsetSeconds: 10,
};

describe("playerBoard.rollRequests", () => {
  it("treats legacy free-form requests as resolved after a later player roll", () => {
    const activity: ActivityEvent[] = [
      requestEvent,
      {
        type: "roll",
        userId: "player-1",
        expression: "1d20",
        results: [17],
        total: 17,
        label: "Teste legado",
        timestamp: "2026-03-30T22:00:03Z",
        sessionOffsetSeconds: 13,
      },
    ];

    expect(isActivityRequestAlreadyResolved(activity, requestEvent, "player-1")).toBe(true);
    expect(findLatestPendingRollRequest(activity, "player-1")).toBeNull();
  });

  it("keeps a request pending when the only roll happened before the request", () => {
    const activity: ActivityEvent[] = [
      {
        type: "roll",
        userId: "player-1",
        expression: "1d20",
        results: [12],
        total: 12,
        label: "Teste legado",
        timestamp: "2026-03-30T21:59:59Z",
        sessionOffsetSeconds: 9,
      },
      requestEvent,
    ];

    expect(isActivityRequestAlreadyResolved(activity, requestEvent, "player-1")).toBe(false);
    expect(findLatestPendingRollRequest(activity, "player-1")).toEqual(requestEvent);
  });

  it("builds a stable handled key for activity-backed requests", () => {
    expect(buildActivityRollRequestKey(requestEvent, "session-1")).toBe(
      "session-1:2026-03-30T22:00:00Z:1d20:Teste legado::player-1",
    );
  });
});
