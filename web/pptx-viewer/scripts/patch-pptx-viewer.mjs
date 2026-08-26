import { readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const EXPECTED_VERSION = "0.2.2";
const UNSUPPORTED =
  "Unsupported pptx-viewer@0.2.2 source: expected one fuzzy relationship lookup";
const UNPATCHED_LOOKUP = `    getByType(i) {
      if (r.has(i))
        return r.get(i) || [];
      for (const [l, c] of r)
        if (l.includes(i) || i.includes(l))
          return c;
      return [];
    },`;
const PATCHED_LOOKUP = `    getByType(i) {
      const l = hn(i);
      return r.get(l) || [];
    },`;

export function patchRelationshipLookup(source) {
  if (source.includes(PATCHED_LOOKUP)) {
    if (source.includes(UNPATCHED_LOOKUP)) {
      throw new Error(UNSUPPORTED);
    }
    return source;
  }

  const occurrences = source.split(UNPATCHED_LOOKUP).length - 1;
  if (occurrences !== 1) {
    throw new Error(UNSUPPORTED);
  }
  return source.replace(UNPATCHED_LOOKUP, PATCHED_LOOKUP);
}

async function patchInstalledPackage() {
  const scriptDirectory = dirname(fileURLToPath(import.meta.url));
  const packageDirectory = resolve(scriptDirectory, "../node_modules/pptx-viewer");
  const packageJsonPath = join(packageDirectory, "package.json");
  const distributionPath = join(packageDirectory, "dist/pptx-viewer.js");
  const packageJson = JSON.parse(await readFile(packageJsonPath, "utf8"));
  if (packageJson.version !== EXPECTED_VERSION) {
    throw new Error(
      `Unsupported pptx-viewer version ${String(packageJson.version)}; expected ${EXPECTED_VERSION}`,
    );
  }

  const source = await readFile(distributionPath, "utf8");
  const patched = patchRelationshipLookup(source);
  if (patched !== source) {
    await writeFile(distributionPath, patched, "utf8");
    console.log(`Patched exact relationship matching: ${distributionPath}`);
  } else {
    console.log(`Exact relationship patch already applied: ${distributionPath}`);
  }
}

const invokedPath = process.argv[1]
  ? pathToFileURL(resolve(process.argv[1])).href
  : "";
if (invokedPath === import.meta.url) {
  await patchInstalledPackage();
}
