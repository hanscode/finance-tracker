import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      // Allows importing with @/ instead of relative paths
      // Example: import { Button } from "@/components/ui/button"
      // Instead of: import { Button } from "../../../components/ui/button"
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0", // Required for Docker (accepts external connections)
    port: 5173,
    // Proxy: redirects /api/* to the backend automatically
    // This way the frontend doesn't need to know the backend URL
    proxy: {
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});
