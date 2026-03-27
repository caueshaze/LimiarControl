import { describe, expect, it } from "vitest";

import {
  reduceSessionRuntimeMessage,
} from "./sessionRuntime.reducer";
import {
  createInitialSessionRuntimeState,
} from "./sessionRuntime.types";

describe("sessionRuntime.reducer", () => {
  it("activates and clears combat runtime state", () => {
    const active = reduceSessionRuntimeMessage(createInitialSessionRuntimeState(), {
      type: "combat_started",
      payload: { sessionId: "sess-1" },
    });
    expect(active.combatActive).toBe(true);

    const ended = reduceSessionRuntimeMessage(active, {
      type: "combat_ended",
      payload: { sessionId: "sess-1" },
    });
    expect(ended.combatActive).toBe(false);
  });

  it("tracks shop commands and roll requests", () => {
    const withShop = reduceSessionRuntimeMessage(createInitialSessionRuntimeState(), {
      type: "shop_opened",
      payload: { sessionId: "sess-1", issuedBy: "gm" },
    });
    expect(withShop.shopOpen).toBe(true);
    expect(withShop.lastCommand?.command).toBe("open_shop");

    const withRoll = reduceSessionRuntimeMessage(withShop, {
      type: "roll_requested",
      payload: { expression: "d20" },
    });
    expect(withRoll.lastCommand?.command).toBe("request_roll");
  });

  it("resets runtime when the session ends", () => {
    const activeState = {
      ...createInitialSessionRuntimeState(),
      combatActive: true,
      shopOpen: true,
      restState: "short_rest" as const,
      lastCommand: {
        command: "request_roll" as const,
      },
    };

    const ended = reduceSessionRuntimeMessage(activeState, {
      type: "session_ended",
      payload: { endedAt: "2026-03-24T10:00:00.000Z" },
    });

    expect(ended.combatActive).toBe(false);
    expect(ended.shopOpen).toBe(false);
    expect(ended.restState).toBe("exploration");
    expect(ended.lastCommand).toBeNull();
    expect(ended.sessionEndedAt).toBe("2026-03-24T10:00:00.000Z");
  });
});
