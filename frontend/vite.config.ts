import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/items": process.env.VITE_API_TARGET ?? "http://127.0.0.1:5000",
      "/locations": process.env.VITE_API_TARGET ?? "http://127.0.0.1:5000",
      "/health": process.env.VITE_API_TARGET ?? "http://127.0.0.1:5000",
    },
  },
});
