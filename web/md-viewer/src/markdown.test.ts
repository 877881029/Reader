import { describe, expect, it } from "vitest";
import { renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it("renders GFM structures, wikilinks, and rewrites relative images", () => {
    const { fragment, wikiLinks } = renderMarkdown(
      "# 文档地图\n\n| 文档 | 用途 |\n|---|---|\n| 本文 | 总览 |\n\n" +
        "[[linked-note|下一篇]]\n\n![diagram](diagram.png)\n\n" +
        "<script>globalThis.pwned=true</script>",
      "file:///C:/docs/index.md",
    );

    const host = document.createElement("div");
    host.append(fragment);

    expect(host.querySelector("table")).not.toBeNull();
    expect(host.querySelector(".table-scroll > table")).not.toBeNull();
    expect(host.querySelector("script")).toBeNull();
    expect(wikiLinks[0]?.target).toBe("linked-note");
    expect(wikiLinks[0]?.element.textContent).toBe("下一篇");
    expect(host.querySelector("img")?.src).toBe("file:///C:/docs/diagram.png");
  });

  it("does not transform wikilink text inside code", () => {
    const { wikiLinks } = renderMarkdown(
      "`[[inline]]`\n\n```\n[[fenced]]\n```",
      "file:///C:/docs/index.md",
    );

    expect(wikiLinks).toHaveLength(0);
  });
});
