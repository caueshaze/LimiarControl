import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      "/sessions": "http://localhost:3000",
      "/debug": "http://localhost:3000",
      "/centrifugo": "http://localhost:3000"
    }
  }
});
