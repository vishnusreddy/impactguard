import { defineConfig } from "vite";
export default defineConfig({
  root: "frontend",
  build: {
    outDir: "../dist",
    emptyOutDir: true,
    rollupOptions: { output: { manualChunks: { charts: ["recharts"] } } },
  },
  server: { proxy: { "/api": "http://127.0.0.1:8080" } },
});
