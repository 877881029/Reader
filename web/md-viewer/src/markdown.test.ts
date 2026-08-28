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

  it("does not transform wikilinks inside markdown links", () => {
    const { fragment, wikiLinks } = renderMarkdown(
      "[see [[note]]](target.md)",
      "file:///C:/docs/index.md",
    );
    const host = document.createElement("div");
    host.append(fragment);

    const anchors = host.querySelectorAll("a");
    expect(wikiLinks).toHaveLength(0);
    expect(anchors).toHaveLength(1);
    expect(anchors[0]?.getAttribute("href")).toBe("target.md");
    expect(anchors[0]?.textContent).toBe("see [[note]]");
  });

  it("keeps invalid wikilink source text unchanged", () => {
    const { fragment, wikiLinks } = renderMarkdown(
      "[[|alias]] [[target|]]",
      "file:///C:/docs/index.md",
    );
    const host = document.createElement("div");
    host.append(fragment);

    expect(wikiLinks).toHaveLength(0);
    expect(host.textContent).toContain("[[|alias]]");
    expect(host.textContent).toContain("[[target|]]");
  });

  it("does not rewrite absolute or special image sources", () => {
    const { fragment } = renderMarkdown(
      "![http](http://example.com/a.png)\n\n![data](data:image/png;base64,AAAA)\n\n![hash](#local-img)\n\n![cdn](//cdn.example.com/x.png)",
      "file:///C:/docs/index.md",
    );
    const host = document.createElement("div");
    host.append(fragment);

    const sources = Array.from(host.querySelectorAll("img")).map((img) => img.getAttribute("src"));
    expect(sources).toEqual([
      "http://example.com/a.png",
      "data:image/png;base64,AAAA",
      "#local-img",
      "//cdn.example.com/x.png",
    ]);
  });
});
