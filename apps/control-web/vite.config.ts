import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Allow overriding backend target without changing source code.
  // Default remains the local control-server.
  const env = process.env;
  const apiTarget =
    env.VITE_API_PROXY_TARGET ||
    env.API_PROXY_TARGET ||
    "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      host: true, // Isso expõe o projeto para a rede local (0.0.0.0)
      port: 5173, // Opcional: garante que sempre use essa porta
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
