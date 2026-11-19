import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The console is a viewer: it reads out/report.json, produced by the Python gate.
// Keeping it a static build means the gate itself never depends on node.
export default defineConfig({
  plugins: [react()],
  base: "./",
});
