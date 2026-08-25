import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  test: { environment: "jsdom" },
  build: {
    outDir: fileURLToPath(new URL("../../assets/pptx-viewer", import.meta.url)),
    emptyOutDir: true,
    assetsDir: "assets",
    sourcemap: false,
  },
});
