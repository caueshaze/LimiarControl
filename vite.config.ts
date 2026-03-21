import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Isso expõe o projeto para a rede local (0.0.0.0)
    port: 5173, // Opcional: garante que sempre use essa porta
  },
});