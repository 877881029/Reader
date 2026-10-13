import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: {
    outDir: fileURLToPath(new URL("../../assets/terminal-viewer", import.meta.url)),
    emptyOutDir: true,
    // xterm.js ships pre-minified; esbuild re-minifying it rewrites
    // `requestMode`'s `let r;(...)(r||={})` into an assignment to an
    // undeclared variable, which throws on every DECRQM query (ESC[?N$p).
    minify: false,
  },
});