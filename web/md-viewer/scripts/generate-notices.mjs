import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = dirname(here);
const sourceNoticePath = join(webRoot, "THIRD_PARTY_NOTICES.txt");
const bundleDir = join(webRoot, "..", "..", "assets", "md-viewer");
const bundledNoticePath = join(bundleDir, "THIRD_PARTY_NOTICES.txt");
const licenseNamePriority = [
  "LICENSE",
  "LICENSE.md",
  "LICENSE.txt",
  "LICENCE",
  "LICENCE.md",
  "LICENCE.txt",
  "COPYING",
  "COPYING.md",
  "COPYING.txt",
];

function findProductionPackageIdsFromNpmLs() {
  const npmLsCommand = "npm ls --omit=dev --all --json";
  const windowsCommand = npmLsCommand.replace("npm ", "npm.cmd ");
  const treeJson = execFileSync("cmd.exe", ["/d", "/s", "/c", windowsCommand], {
    cwd: webRoot,
    encoding: "utf-8",
  });
  const tree = JSON.parse(treeJson);
  const ids = new Set();
  const walk = (node) => {
    const dependencies = node?.dependencies ?? {};
    for (const [name, child] of Object.entries(dependencies)) {
      if (typeof child?.version === "string" && child.version) {
        ids.add(`${name}@${child.version}`);
      }
      walk(child);
    }
  };
  walk(tree);
  return ids;
}

function findProductionPackagePathsFromLock() {
  const lock = JSON.parse(readFileSync(join(webRoot, "package-lock.json"), "utf-8"));
  return Object.entries(lock.packages)
    .filter(([pathKey, meta]) => pathKey.startsWith("node_modules/") && meta && meta.dev !== true)
    .map(([pathKey]) => join(webRoot, pathKey));
}

function resolveLicenseMaterial(packageDir, packageId) {
  const filesUpperMap = new Map();
  for (const name of readdirSync(packageDir)) {
    filesUpperMap.set(name.toUpperCase(), name);
  }
  for (const preferredName of licenseNamePriority) {
    const actual = filesUpperMap.get(preferredName.toUpperCase());
    if (!actual) {
      continue;
    }
    const full = join(packageDir, actual);
    const text = readFileSync(full, "utf-8").trim();
    if (!text) {
      throw new Error(`Missing license text for ${packageId}`);
    }
    return { sourceLabel: resolve(full), text };
  }
  const readmeName = filesUpperMap.get("README.MD") ?? filesUpperMap.get("README");
  if (readmeName) {
    const readmePath = join(packageDir, readmeName);
    const readmeText = readFileSync(readmePath, "utf-8").trim();
    if (readmeText) {
      return { sourceLabel: `${resolve(readmePath)} (README fallback)`, text: readmeText };
    }
  }
  throw new Error(`Missing license text for ${packageId}`);
}

function collectNotices() {
  const expectedIds = findProductionPackageIdsFromNpmLs();
  const byId = new Map();
  for (const packageDir of findProductionPackagePathsFromLock()) {
    const packageJsonPath = join(packageDir, "package.json");
    if (!existsSync(packageJsonPath)) {
      continue;
    }
    const pkg = JSON.parse(readFileSync(packageJsonPath, "utf-8"));
    if (typeof pkg.name !== "string" || typeof pkg.version !== "string") {
      continue;
    }
    const id = `${pkg.name}@${pkg.version}`;
    if (!expectedIds.has(id) || byId.has(id)) {
      continue;
    }
    const { sourceLabel, text } = resolveLicenseMaterial(packageDir, id);
    byId.set(id, {
      name: pkg.name,
      version: pkg.version,
      licenses: pkg.license ?? "UNKNOWN",
      licenseFile: sourceLabel,
      licenseText: text,
    });
  }

  for (const id of expectedIds) {
    if (!byId.has(id)) {
      throw new Error(`Missing notice entry for production package ${id}`);
    }
  }
  return Array.from(byId.values()).sort((a, b) => `${a.name}@${a.version}`.localeCompare(`${b.name}@${b.version}`));
}

const sections = collectNotices().map((entry) =>
  [`## ${entry.name} ${entry.version}`, `SPDX: ${entry.licenses}`, `License file: ${entry.licenseFile}`, "", entry.licenseText].join(
    "\n",
  ),
);
const notice = `${sections.join("\n\n")}\n`;
writeFileSync(sourceNoticePath, notice, "utf-8");
mkdirSync(bundleDir, { recursive: true });
writeFileSync(bundledNoticePath, notice, "utf-8");
