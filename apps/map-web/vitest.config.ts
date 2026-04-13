import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    name: "map-web-unit",
    root: path.resolve(__dirname),
    environment: "node",
    include: ["src/**/*.test.ts"],
    exclude: ["tests/**", "**/*.spec.ts"]
  },
  resolve: {
    alias: {
      "@limiarmap/shared-contracts": path.resolve(
        __dirname,
        "../../../../packages/shared-contracts/src/index.ts"
      )
    }
  }
});
