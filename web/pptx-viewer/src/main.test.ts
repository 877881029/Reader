import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("scaffold smoke", () => {
  it("keeps bootstrap local and offline-friendly", () => {
    const source = readFileSync("src/main.ts", "utf-8");
    expect(source).toContain('querySelector<HTMLDivElement>("#app")');
    expect(source).not.toMatch(/from\s+["']https?:\/\//);
    expect(source).not.toMatch(/import\s*\(\s*["']https?:\/\//);
  });
});
