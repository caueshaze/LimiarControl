import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    name: "server-contract-and-integration",
    root: ".",
    environment: "node",
    include: ["**/*.test.ts"]
  }
});
