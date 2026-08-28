import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderMermaidBlocks } from "./mermaid";

const { renderMock, initializeMock } = vi.hoisted(() => ({
  renderMock: vi.fn(),
  initializeMock: vi.fn(),
}));

vi.mock("mermaid", () => ({
  default: {
    initialize: initializeMock,
    render: renderMock,
  },
}));

describe("renderMermaidBlocks", () => {
  beforeEach(() => {
    renderMock.mockReset();
    initializeMock.mockReset();
  });

  it("renders each mermaid block independently and isolates failures", async () => {
    renderMock.mockImplementation(async (_id: string, source: string) => {
      if (source.includes("ok graph")) {
        return { svg: "<svg><text>ok</text></svg>" };
      }
      throw new Error("bad diagram");
    });

    const root = document.createElement("div");
    root.innerHTML = `
      <p>intro</p>
      <pre><code class="language-mermaid">ok graph</code></pre>
      <table><tr><td>tab</td></tr></table>
      <pre><code class="language-mermaid">broken graph</code></pre>
    `;

    await renderMermaidBlocks(root);

    expect(initializeMock).toHaveBeenCalledTimes(1);
    expect(root.querySelectorAll(".mermaid-rendered svg")).toHaveLength(1);
    expect(root.querySelectorAll(".mermaid-error pre")).toHaveLength(1);
    expect(root.querySelector("p")?.textContent).toBe("intro");
    expect(root.querySelector("table")).not.toBeNull();
    expect(root.querySelector(".mermaid-error code")?.textContent).toContain("broken graph");
  });
});
