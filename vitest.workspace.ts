import { defineWorkspace } from "vitest/config";

export default defineWorkspace([
  "apps/map-web/vitest.config.ts",
  "apps/map-server/tests/vitest.config.ts",
  "packages/tactical-engine/tests/vitest.config.ts",
  {
    test: {
      name: "control-web-unit",
      root: "./apps/control-web",
      environment: "node",
      include: ["src/**/*.test.ts"],
      exclude: ["**/*.spec.ts"]
    }
  }
]);
