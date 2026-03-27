import { describe, expect, it } from "vitest";
import type { ActivityEvent } from "../../../shared/api/sessionsRepo";
import { buildSessionActivityDisplayItems } from "./sessionActivity.utils";

describe("sessionActivity.utils", () => {
  it("groups events inside combat windows into a combat module", () => {
    const events: ActivityEvent[] = [
      {
        action: "opened",
        displayName: "GM",
        sessionOffsetSeconds: 10,
        timestamp: "2026-03-24T10:00:10Z",
        type: "shop",
      },
      {
        action: "started",
        displayName: "GM",
        sessionOffsetSeconds: 20,
        timestamp: "2026-03-24T10:00:20Z",
        type: "combat",
      },
      {
        action: "damaged",
        displayName: "GM",
        entityName: "Goblin",
        sessionOffsetSeconds: 25,
        timestamp: "2026-03-24T10:00:25Z",
        type: "entity",
      },
      {
        action: "ended",
        displayName: "GM",
        sessionOffsetSeconds: 40,
        timestamp: "2026-03-24T10:00:40Z",
        type: "combat",
      },
    ];

    const items = buildSessionActivityDisplayItems(events);

    expect(items).toHaveLength(2);
    expect(items[0]?.type).toBe("combat-module");
    expect(items[0]?.type === "combat-module" ? items[0].events : []).toHaveLength(3);
    expect(items[1]?.type).toBe("event");
  });
});
