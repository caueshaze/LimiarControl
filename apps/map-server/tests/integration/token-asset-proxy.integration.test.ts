import { describe, expect, it } from "vitest";
import { createApp } from "../../src/app";

describe("token asset proxy route", () => {
  it("rejects an unknown session with 404", async () => {
    const { app } = createApp();
    const response = await app.inject({
      method: "GET",
      url: "/sessions/missing-session/asset?src=%2Fapi%2Fassets%2Fusers%2Fu1%2Ftoken%2Fx.png"
    });
    expect(response.statusCode).toBe(404);
  });

  it("requires a src query parameter", async () => {
    const { app } = createApp();
    const response = await app.inject({
      method: "GET",
      url: "/sessions/demo-session/asset"
    });
    expect(response.statusCode).toBe(400);
  });

  it("rejects absolute URLs (SSRF guard)", async () => {
    const { app } = createApp();
    const response = await app.inject({
      method: "GET",
      url: `/sessions/demo-session/asset?src=${encodeURIComponent("https://evil.example.com/x.png")}`
    });
    expect(response.statusCode).toBe(403);
  });

  it("rejects protocol-relative URLs", async () => {
    const { app } = createApp();
    const response = await app.inject({
      method: "GET",
      url: `/sessions/demo-session/asset?src=${encodeURIComponent("//evil.example.com/x.png")}`
    });
    expect(response.statusCode).toBe(403);
  });

  it("rejects path traversal", async () => {
    const { app } = createApp();
    const response = await app.inject({
      method: "GET",
      url: `/sessions/demo-session/asset?src=${encodeURIComponent("/api/assets/../../etc/passwd")}`
    });
    expect(response.statusCode).toBe(403);
  });

  it("rejects paths outside the allow-list", async () => {
    const { app } = createApp();
    const response = await app.inject({
      method: "GET",
      url: `/sessions/demo-session/asset?src=${encodeURIComponent("/sessions/demo-session/encounter")}`
    });
    expect(response.statusCode).toBe(403);
  });
});
