import { describe, expect, it } from "vitest";
import { resolveHomePath } from "./workspaceRouting";
import { routes } from "./routes";

describe("workspace routing helpers", () => {
  it("always resolves to the unified home regardless of role", () => {
    expect(resolveHomePath()).toBe(routes.home);
  });
});
