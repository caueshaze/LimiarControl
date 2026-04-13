import { describe, expect, it } from "vitest";
import { resolveHomePath, resolveWorkspaceMode } from "./workspaceRouting";
import { routes } from "./routes";

describe("workspace routing helpers", () => {
  it("keeps system admins in their operational home", () => {
    expect(resolveHomePath({ role: "GM", isSystemAdmin: true })).toBe(routes.gmHome);
    expect(resolveHomePath({ role: "PLAYER", isSystemAdmin: true })).toBe(routes.home);
  });

  it("keeps non-admin users in their operational home", () => {
    expect(resolveHomePath({ role: "GM", isSystemAdmin: false })).toBe(routes.gmHome);
    expect(resolveHomePath({ role: "PLAYER", isSystemAdmin: false })).toBe(routes.home);
  });

  it("maps workspace mode by operational role", () => {
    expect(resolveWorkspaceMode("GM")).toBe("gm");
    expect(resolveWorkspaceMode("PLAYER")).toBe("player");
  });
});
