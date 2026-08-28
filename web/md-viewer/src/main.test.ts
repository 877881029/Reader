import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const startViewerMock = vi.fn();
vi.mock("./viewer", () => ({
  startViewer: startViewerMock,
}));

type BridgeStub = {
  sourceUrl: string;
  viewerReady: ReturnType<typeof vi.fn>;
  viewerError: ReturnType<typeof vi.fn>;
  wikiExists: ReturnType<typeof vi.fn>;
  openWiki: ReturnType<typeof vi.fn>;
};

function createBridge(sourceUrl = "file:///C:/docs/source.md"): BridgeStub {
  return {
    sourceUrl,
    viewerReady: vi.fn(),
    viewerError: vi.fn(),
    wikiExists: vi.fn(),
    openWiki: vi.fn(),
  };
}

async function bootstrapWithBridge(bridge: BridgeStub) {
  const transport = {};
  (window as typeof window & { qt?: { webChannelTransport?: unknown } }).qt = {
    webChannelTransport: transport,
  };
  class QWebChannelStub {
    constructor(
      _transport: unknown,
      callback: (channel: { objects: { bridge: BridgeStub } }) => void,
    ) {
      callback({ objects: { bridge } });
    }
  }
  (window as typeof window & { QWebChannel?: unknown }).QWebChannel =
    QWebChannelStub as unknown as typeof window.QWebChannel;

  await import("./main");
}

describe("main bootstrap", () => {
  beforeEach(() => {
    vi.resetModules();
    startViewerMock.mockReset();
    document.body.innerHTML = '<div id="app"></div>';
    delete (window as typeof window & { readerMdDispose?: () => void }).readerMdDispose;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete (window as typeof window & { qt?: unknown }).qt;
    delete (window as typeof window & { QWebChannel?: unknown }).QWebChannel;
    delete (window as typeof window & { readerMdDispose?: () => void }).readerMdDispose;
  });

  it("loads source markdown and starts viewer", async () => {
    const bridge = createBridge();
    const destroy = vi.fn();
    startViewerMock.mockResolvedValue({ destroy });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: vi.fn().mockResolvedValue("# heading"),
    });
    vi.stubGlobal("fetch", fetchMock);

    await bootstrapWithBridge(bridge);

    expect(fetchMock).toHaveBeenCalledWith("file:///C:/docs/source.md");
    expect(startViewerMock).toHaveBeenCalledTimes(1);
    expect(startViewerMock.mock.calls[0]?.[1]).toBe("# heading");
    expect(window.readerMdDispose).toEqual(expect.any(Function));
  });

  it("reports fixed bootstrap error without leaking source path", async () => {
    const bridge = createBridge("file:///C:/secret/private.md");
    startViewerMock.mockResolvedValue({ destroy: vi.fn() });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("ENOENT C:/secret/private.md")));

    await bootstrapWithBridge(bridge);

    expect(bridge.viewerError).toHaveBeenCalledTimes(1);
    const message = bridge.viewerError.mock.calls[0]?.[0] ?? "";
    expect(message).toBeTruthy();
    expect(message).not.toContain("secret");
    expect(message).not.toContain("private.md");
  });

  it("disposes viewer via exposed API and lifecycle events", async () => {
    const bridge = createBridge();
    const destroy = vi.fn();
    startViewerMock.mockResolvedValue({ destroy });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, text: vi.fn().mockResolvedValue("doc") }));

    await bootstrapWithBridge(bridge);
    window.readerMdDispose?.();
    window.dispatchEvent(new Event("pagehide"));
    window.dispatchEvent(new Event("beforeunload"));

    expect(destroy).toHaveBeenCalledTimes(1);
    expect(startViewerMock.mock.calls[0]?.[4]).toBeInstanceOf(AbortSignal);
  });
});
