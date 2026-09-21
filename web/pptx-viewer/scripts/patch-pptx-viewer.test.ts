import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { patchRelationshipLookup, patchTableRunCssQuotes } from "./patch-pptx-viewer.mjs";

const unpatched = `before
    getByType(i) {
      if (r.has(i))
        return r.get(i) || [];
      for (const [l, c] of r)
        if (l.includes(i) || i.includes(l))
          return c;
      return [];
    },
after`;

const patched = `before
    getByType(i) {
      const l = hn(i);
      return r.get(l) || [];
    },
after`;

describe("pptx-viewer dependency patch", () => {
  it("replaces fuzzy relationship matching with exact terminal-name lookup", () => {
    expect(patchRelationshipLookup(unpatched)).toBe(patched);
  });

  it("is idempotent when npm invokes the patch twice", () => {
    expect(patchRelationshipLookup(patched)).toBe(patched);
  });

  it("fails fast when pinned upstream source drifts", () => {
    expect(() => patchRelationshipLookup("unexpected source")).toThrow(
      "Unsupported pptx-viewer@0.2.2 source",
    );
  });

  it("is present in the installed ESM distribution", async () => {
    const distribution = await readFile(
      resolve("node_modules/pptx-viewer/dist/pptx-viewer.js"),
      "utf8",
    );
    expect(distribution).toContain("const l = hn(i);");
    expect(distribution).not.toContain("l.includes(i) || i.includes(l)");
  });
});

const unpatchedFont = 'i.fontFamily && c.push(`font-family: "${i.fontFamily}", sans-serif`)';
const patchedFont = "i.fontFamily && c.push(`font-family: '${i.fontFamily}', sans-serif`)";

describe("pptx-viewer table run CSS quotes", () => {
  it("uses single quotes so HTML style attributes keep color", () => {
    expect(patchTableRunCssQuotes(`before ${unpatchedFont} after`)).toBe(
      `before ${patchedFont} after`,
    );
  });

  it("is idempotent when npm invokes the patch twice", () => {
    expect(patchTableRunCssQuotes(`before ${patchedFont} after`)).toBe(
      `before ${patchedFont} after`,
    );
  });

  it("fails fast when pinned table HTML source drifts", () => {
    expect(() => patchTableRunCssQuotes("unexpected source")).toThrow(
      "Unsupported pptx-viewer@0.2.2 table run CSS",
    );
  });

  it("is present in the installed ESM distribution", async () => {
    const distribution = await readFile(
      resolve("node_modules/pptx-viewer/dist/pptx-viewer.js"),
      "utf8",
    );
    expect(distribution).toContain("font-family: '${i.fontFamily}', sans-serif");
    expect(distribution).not.toContain('font-family: "${i.fontFamily}", sans-serif');
  });
});
