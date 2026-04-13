import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    name: "tactical-engine-unit",
    root: ".",
    environment: "node",
    include: ["**/*.test.ts"]
  }
});
