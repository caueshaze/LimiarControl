import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  retries: 0,
  webServer: {
    command: "npx tsx ../../../apps/server/src/server.ts",
    port: 3000,
    reuseExistingServer: !process.env["CI"],
    timeout: 15_000
  }
});
