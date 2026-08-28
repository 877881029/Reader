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
  let addListenerSpy: ReturnType<typeof vi.spyOn>;
  let removeListenerSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.resetModules();
    startViewerMock.mockReset();
    addListenerSpy = vi.spyOn(window, "addEventListener");
    removeListenerSpy = vi.spyOn(window, "removeEventListener");
    document.body.innerHTML = '<div id="app"></div>';
    delete (window as typeof window & { readerMdDispose?: () => void }).readerMdDispose;
  });

  afterEach(() => {
    window.readerMdDispose?.();
    vi.unstubAllGlobals();
    delete (window as typeof window & { qt?: unknown }).qt;
    delete (window as typeof window & { QWebChannel?: unknown }).QWebChannel;
    delete (window as typeof window & { readerMdDispose?: () => void }).readerMdDispose;
    addListenerSpy.mockRestore();
    removeListenerSpy.mockRestore();
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

    expect(fetchMock).toHaveBeenCalledWith(
      "file:///C:/docs/source.md",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
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

  it("does not report late viewerError after dispose aborts pending fetch", async () => {
    const bridge = createBridge();
    startViewerMock.mockResolvedValue({ destroy: vi.fn() });
    let rejectFetch: (error: unknown) => void = () => {
      // no-op until fetch executor assigns real reject
    };
    const fetchMock = vi.fn(
      () =>
        new Promise((_resolve, reject) => {
          rejectFetch = reject;
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await bootstrapWithBridge(bridge);
    window.readerMdDispose?.();
    (rejectFetch as (error: unknown) => void)(new DOMException("aborted", "AbortError"));
    await Promise.resolve();

    expect(bridge.viewerError).not.toHaveBeenCalled();
  });

  it("suppresses viewerError for rejected fetch AbortError", async () => {
    const bridge = createBridge();
    startViewerMock.mockResolvedValue({ destroy: vi.fn() });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError")));

    await bootstrapWithBridge(bridge);

    expect(bridge.viewerError).not.toHaveBeenCalled();
  });

  it("removes window lifecycle listeners during dispose", async () => {
    const bridge = createBridge();
    startViewerMock.mockResolvedValue({ destroy: vi.fn() });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, text: vi.fn().mockResolvedValue("doc") }));

    await bootstrapWithBridge(bridge);
    window.readerMdDispose?.();

    expect(addListenerSpy).toHaveBeenCalledWith("pagehide", expect.any(Function));
    expect(addListenerSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
    expect(removeListenerSpy).toHaveBeenCalledWith("pagehide", expect.any(Function));
    expect(removeListenerSpy).toHaveBeenCalledWith("beforeunload", expect.any(Function));
  });

  it("keeps lifecycle listeners isolated across re-imports", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, text: vi.fn().mockResolvedValue("doc") });
    vi.stubGlobal("fetch", fetchMock);

    const bridgeA = createBridge("file:///C:/docs/a.md");
    startViewerMock.mockResolvedValue({ destroy: vi.fn() });
    await bootstrapWithBridge(bridgeA);
    window.readerMdDispose?.();

    vi.resetModules();
    document.body.innerHTML = '<div id="app"></div>';
    const bridgeB = createBridge("file:///C:/docs/b.md");
    await bootstrapWithBridge(bridgeB);
    window.readerMdDispose?.();

    expect(addListenerSpy.mock.calls.filter(([name]) => name === "pagehide")).toHaveLength(2);
    expect(addListenerSpy.mock.calls.filter(([name]) => name === "beforeunload")).toHaveLength(2);
    expect(removeListenerSpy.mock.calls.filter(([name]) => name === "pagehide")).toHaveLength(2);
    expect(removeListenerSpy.mock.calls.filter(([name]) => name === "beforeunload")).toHaveLength(2);
  });
});
