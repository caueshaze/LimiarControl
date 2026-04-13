import { describe, expect, it, vi } from "vitest";
import {
  MAP_LEGACY_EVENTS_CHANNEL,
  MAP_SYSTEM_EVENTS_CHANNEL,
  broadcastAuthoritativeEvent,
  getSpatialEventChannels
} from "../../src/modules/realtime/broadcast";

describe("realtime authoritative broadcast", () => {
  it("publishes authoritative events to Centrifugo channels", () => {
    const broadcaster = { emit: vi.fn() };
    const publisher = { publish: vi.fn().mockResolvedValue(undefined) };
    const envelope = {
      eventId: "evt-1",
      eventType: "combat.started",
      encounterId: "session-123",
      version: 4,
      actionId: "control-combat-start:combat-123",
      payload: {
        roundNumber: 1,
        turnIndex: 0,
        activeCombatantId: "player-123",
        initiativeOrder: ["player-123", "enemy-123"]
      },
      replaySafe: true
    };

    broadcastAuthoritativeEvent(broadcaster, "combat.started", envelope, publisher);

    expect(broadcaster.emit).toHaveBeenCalledWith("combat.started", envelope);
    expect(publisher.publish).toHaveBeenCalledTimes(3);
    expect(publisher.publish).toHaveBeenNthCalledWith(1, "session:session-123", envelope);
    expect(publisher.publish).toHaveBeenNthCalledWith(2, MAP_SYSTEM_EVENTS_CHANNEL, envelope);
    expect(publisher.publish).toHaveBeenNthCalledWith(3, MAP_LEGACY_EVENTS_CHANNEL, envelope);
  });

  it("skips Centrifugo publication when the payload is not a valid authoritative envelope", () => {
    const broadcaster = { emit: vi.fn() };
    const publisher = { publish: vi.fn().mockResolvedValue(undefined) };

    broadcastAuthoritativeEvent(
      broadcaster,
      "combat.started",
      {
        encounterId: "session-123",
        payload: {}
      },
      publisher
    );

    expect(broadcaster.emit).toHaveBeenCalledWith("combat.started", {
      encounterId: "session-123",
      payload: {}
    });
    expect(publisher.publish).not.toHaveBeenCalled();
  });

  it("exposes the phased channel model explicitly", () => {
    expect(getSpatialEventChannels("session-123")).toEqual([
      "session:session-123",
      MAP_SYSTEM_EVENTS_CHANNEL,
      MAP_LEGACY_EVENTS_CHANNEL
    ]);
  });
});
