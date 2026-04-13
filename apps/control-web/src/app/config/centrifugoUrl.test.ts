import { describe, expect, it } from "vitest";
import { resolveCentrifugoUrl } from "./centrifugoUrl";

describe("resolveCentrifugoUrl", () => {
  it("normalizes localhost to 127.0.0.1 for local development", () => {
    expect(
      resolveCentrifugoUrl("ws://localhost:8001/connection/websocket", {
        hostname: "localhost",
        protocol: "http:",
      }),
    ).toBe("ws://127.0.0.1:8001/connection/websocket");
  });

  it("reuses the current host when the configured url points at loopback", () => {
    expect(
      resolveCentrifugoUrl("ws://localhost:8001/connection/websocket", {
        hostname: "192.168.0.10",
        protocol: "http:",
      }),
    ).toBe("ws://192.168.0.10:8001/connection/websocket");
  });

  it("preserves an explicit remote realtime endpoint", () => {
    expect(
      resolveCentrifugoUrl("wss://rt.example.com/connection/websocket", {
        hostname: "localhost",
        protocol: "http:",
      }),
    ).toBe("wss://rt.example.com/connection/websocket");
  });
});
