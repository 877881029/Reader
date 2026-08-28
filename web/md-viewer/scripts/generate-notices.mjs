import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { init } from "license-checker-rseidelsohn";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = dirname(here);
const sourceNoticePath = join(webRoot, "THIRD_PARTY_NOTICES.txt");
const bundleDir = join(webRoot, "..", "..", "assets", "md-viewer");
const bundledNoticePath = join(bundleDir, "THIRD_PARTY_NOTICES.txt");

function collectPackages() {
  return new Promise((resolve, reject) => {
    init(
      {
        start: webRoot,
        production: true,
        customFormat: {
          licenses: "",
          licenseFile: "",
        },
      },
      (error, packages) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(packages);
      },
    );
  });
}

function buildNotice(packages) {
  const entries = Object.entries(packages)
    .filter(([id]) => !id.startsWith("reader-md-viewer@"))
    .sort(([a], [b]) => a.localeCompare(b));
  if (entries.length === 0) {
    throw new Error("No production dependencies were reported by license checker");
  }

  const sections = entries.map(([id, info]) => {
    const split = id.lastIndexOf("@");
    const name = split > 0 ? id.slice(0, split) : id;
    const version = split > 0 ? id.slice(split + 1) : "unknown";
    const licenseFile = info.licenseFile;
    if (typeof licenseFile !== "string" || !licenseFile.trim()) {
      throw new Error(`Missing license file for ${id}`);
    }

    const licenseText = readFileSync(licenseFile, "utf-8").trim();
    if (!licenseText) {
      throw new Error(`Empty license text for ${id}`);
    }

    const licenses = info.licenses ?? "UNKNOWN";
    return [
      `## ${name} ${version}`,
      `SPDX: ${licenses}`,
      `License file: ${licenseFile}`,
      "",
      licenseText,
    ].join("\n");
  });

  return `${sections.join("\n\n")}\n`;
}

const packages = await collectPackages();
const notice = buildNotice(packages);
writeFileSync(sourceNoticePath, notice, "utf-8");
mkdirSync(bundleDir, { recursive: true });
writeFileSync(bundledNoticePath, notice, "utf-8");
