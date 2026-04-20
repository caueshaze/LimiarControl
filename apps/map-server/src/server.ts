import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createApp } from "./app";
import { registerIntegrationRoutes } from "./routes/integration-routes";
import { registerRealtimeRoutes } from "./routes/realtime-routes";
import { registerRealtimePaintRoutes } from "./routes/realtime-paint-routes";

try {
  process.loadEnvFile(resolve(fileURLToPath(new URL("../../../.env", import.meta.url))));
} catch {
  // Local dev may run without a repo-root .env file; in that case rely on process env.
}

const { app, repository } = createApp();
registerRealtimeRoutes(app, repository);
registerRealtimePaintRoutes(app, repository);
registerIntegrationRoutes(app, repository);

export async function startServer(port = 3000): Promise<void> {
  await app.listen({ port, host: "0.0.0.0" });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  startServer().catch(console.error);
}
