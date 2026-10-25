import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El frontend consume la API FastAPI local. La base se configura por entorno
// (VITE_API_BASE); por defecto apunta al backend en el puerto 8077.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
