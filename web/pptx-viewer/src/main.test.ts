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
  window.readerPptxDispose?.();
  vi.resetModules();
  startViewer.mockReset();
  document.body.innerHTML = '<main id="app"></main>';
  delete window.qt;
  delete window.QWebChannel;
  delete window.readerPptxDispose;
});

afterEach(() => {
  window.readerPptxDispose?.();
  vi.restoreAllMocks();
});

it("shows a fatal bootstrap error when WebChannel is unavailable", async () => {
  await import("./main");

  expect(document.querySelector("#app")?.textContent).toContain("Reader bridge unavailable");
  expect(document.querySelector("#app")?.classList).toContain("viewer-bootstrap-error");
  expect(window.readerPptxDispose).toBeTypeOf("function");
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
  startViewer.mockResolvedValue(undefined);

  await import("./main");

  expect(startViewer).toHaveBeenCalledWith(
    document.querySelector("#app"),
    bridge.sourceUrl,
    bridge,
    expect.objectContaining({
      testFailSlide: -1,
      signal: expect.any(AbortSignal),
    }),
  );
});

it("retains the resolved controller and disposes it exactly once", async () => {
  const bridge = makeBridge("file:///C:/decks/visual-elements.pptx");
  installChannel(bridge);
  const controller = { destroy: vi.fn() };
  startViewer.mockResolvedValue(controller);

  await import("./main");
  await Promise.resolve();
  window.readerPptxDispose?.();
  window.readerPptxDispose?.();

  expect(controller.destroy).toHaveBeenCalledOnce();
  const options = startViewer.mock.calls[0]?.[3] as { signal: AbortSignal };
  expect(options.signal.aborted).toBe(true);
});

describe("scaffold smoke", () => {
  it("keeps bootstrap local and offline-friendly", () => {
    const source = readFileSync("src/main.ts", "utf-8");
    expect(source).toContain('querySelector<HTMLElement>("#app")');
    expect(source).not.toMatch(/from\s+["']https?:\/\//);
    expect(source).not.toMatch(/import\s*\(\s*["']https?:\/\//);
  });
});
