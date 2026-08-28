import { createHash } from "node:crypto";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const bundleDir = join(here, "..", "..", "..", "assets", "md-viewer");
const manifestPath = join(bundleDir, "manifest.sha256");

function walkFiles(root) {
  const files = [];
  const stack = [root];
  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const fullPath = join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(fullPath);
      } else if (entry.isFile() && fullPath !== manifestPath) {
        files.push(fullPath);
      }
    }
  }
  return files;
}

const lines = walkFiles(bundleDir)
  .sort((a, b) => {
    const relA = a.slice(bundleDir.length + 1).replaceAll("\\", "/");
    const relB = b.slice(bundleDir.length + 1).replaceAll("\\", "/");
    if (relA < relB) {
      return -1;
    }
    if (relA > relB) {
      return 1;
    }
    return 0;
  })
  .map((filePath) => {
    const digest = createHash("sha256").update(readFileSync(filePath)).digest("hex");
    const relative = filePath.slice(bundleDir.length + 1).replaceAll("\\", "/");
    return `${digest}  ${relative}`;
  });

writeFileSync(manifestPath, `${lines.join("\n")}\n`, "ascii");
