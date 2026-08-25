import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { startViewer } = vi.hoisted(() => ({ startViewer: vi.fn() }));

vi.mock("./viewer", () => ({
  startViewer,
}));

function installChannel(bridge: {
  sourceUrl: string;
  testFailSlide: number;
  viewerReady: ReturnType<typeof vi.fn>;
  viewerError: ReturnType<typeof vi.fn>;
  slideChanged: ReturnType<typeof vi.fn>;
}): void {
  Object.assign(window, {
    qt: { webChannelTransport: {} },
    QWebChannel: class {
      constructor(
        _transport: unknown,
        callback: (channel: { objects: { bridge: typeof bridge } }) => void,
      ) {
        callback({ objects: { bridge } });
      }
    },
  });
}

function makeBridge(sourceUrl: string) {
  return {
    sourceUrl,
    testFailSlide: -1,
    viewerReady: vi.fn(),
    viewerError: vi.fn(),
    slideChanged: vi.fn(),
  };
}

beforeEach(() => {
  vi.resetModules();
  startViewer.mockReset();
  document.body.innerHTML = '<main id="app"></main>';
  delete window.qt;
  delete window.QWebChannel;
});

afterEach(() => {
  vi.restoreAllMocks();
});

it("shows a fatal bootstrap error when WebChannel is unavailable", async () => {
  await import("./main");

  expect(document.querySelector("#app")?.textContent).toContain("Reader bridge unavailable");
  expect(document.querySelector("#app")?.classList).toContain("viewer-bootstrap-error");
});

it("reports and blocks a non-file source URL", async () => {
  const bridge = makeBridge("https://example.test/deck.pptx");
  installChannel(bridge);

  await import("./main");

  expect(startViewer).not.toHaveBeenCalled();
  expect(bridge.viewerError).toHaveBeenCalledOnce();
  expect(bridge.viewerError.mock.calls[0]?.[0]).toContain("local file URL");
});

it("starts from bridge.sourceUrl and forwards the bridge callbacks", async () => {
  const bridge = makeBridge("file:///C:/decks/visual-elements.pptx");
  installChannel(bridge);
  startViewer.mockResolvedValue({});

  await import("./main");

  expect(startViewer).toHaveBeenCalledWith(
    document.querySelector("#app"),
    bridge.sourceUrl,
    bridge,
    { testFailSlide: -1 },
  );
});

describe("scaffold smoke", () => {
  it("keeps bootstrap local and offline-friendly", () => {
    const source = readFileSync("src/main.ts", "utf-8");
    expect(source).toContain('querySelector<HTMLElement>("#app")');
    expect(source).not.toMatch(/from\s+["']https?:\/\//);
    expect(source).not.toMatch(/import\s*\(\s*["']https?:\/\//);
  });
});
