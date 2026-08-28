import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: {
    outDir: fileURLToPath(new URL("../../assets/md-viewer", import.meta.url)),
    emptyOutDir: true,
  },
});
