import { beforeEach, describe, expect, it, vi } from "vitest";
import { startViewer, type MarkdownBridge } from "./viewer";

const mermaidGate = vi.hoisted(() => {
  let release: (() => void) | null = null;
  const renderMermaidBlocks = vi.fn(
    () =>
      new Promise<void>((resolve) => {
        release = resolve;
      }),
  );
  return {
    renderMermaidBlocks,
    release: () => {
      release?.();
      release = null;
    },
    reset: () => {
      release = null;
      renderMermaidBlocks.mockClear();
    },
  };
});

vi.mock("./mermaid", () => ({
  renderMermaidBlocks: mermaidGate.renderMermaidBlocks,
}));

function flush() {
  return new Promise<void>((resolve) => {
    queueMicrotask(() => resolve());
  });
}

function createBridge(overrides?: Partial<MarkdownBridge>): MarkdownBridge {
  return {
    sourceUrl: "file:///C:/docs/source.md",
    viewerReady: vi.fn(),
    viewerError: vi.fn(),
    wikiExists: vi.fn((_target: string, callback: (exists: boolean) => void) => callback(false)),
    openWiki: vi.fn(),
    ...overrides,
  };
}

describe("startViewer", () => {
  beforeEach(() => {
    mermaidGate.reset();
    vi.useRealTimers();
  });

  it("waits wiki checks and then emits ready", async () => {
    const root = document.createElement("div");
    const callbacks = new Map<string, (exists: boolean) => void>();
    const bridge = createBridge({
      wikiExists: vi.fn((target: string, callback: (exists: boolean) => void) => {
        callbacks.set(target, callback);
      }),
    });

    const controllerPromise = startViewer(
      root,
      "[[linked-note]] [[missing]]",
      bridge.sourceUrl,
      bridge,
    );

    await flush();
    expect(bridge.viewerReady).not.toHaveBeenCalled();

    callbacks.get("linked-note")?.(true);
    await flush();
    expect(bridge.viewerReady).not.toHaveBeenCalled();

    callbacks.get("missing")?.(false);
    mermaidGate.release();
    const controller = await controllerPromise;
    await flush();

    const resolved = root.querySelector<HTMLAnchorElement>('a[data-wiki-target="linked-note"]');
    const missing = root.querySelector<HTMLAnchorElement>('a[data-wiki-target="missing"]');
    expect(resolved?.classList.contains("is-resolved")).toBe(true);
    expect(missing?.classList.contains("is-missing")).toBe(true);

    resolved?.click();
    expect(bridge.openWiki).toHaveBeenCalledWith("linked-note");
    missing?.click();
    expect(bridge.openWiki).toHaveBeenCalledWith("missing");
    expect(bridge.viewerReady).toHaveBeenCalledTimes(1);

    controller.destroy();
  });

  it("prevents navigation for remote links", async () => {
    const root = document.createElement("div");
    const bridge = createBridge();

    const controllerPromise = startViewer(
      root,
      "[remote](https://example.com/path)\n\n[ws](ws://example.com/channel)",
      bridge.sourceUrl,
      bridge,
    );
    mermaidGate.release();
    const controller = await controllerPromise;

    const remote = root.querySelector<HTMLAnchorElement>('a[href="https://example.com/path"]');
    expect(remote).not.toBeNull();

    const event = new MouseEvent("click", { bubbles: true, cancelable: true });
    remote?.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);

    const ws = root.querySelector<HTMLAnchorElement>('a[href="ws://example.com/channel"]');
    const wsEvent = new MouseEvent("click", { bubbles: true, cancelable: true });
    ws?.dispatchEvent(wsEvent);
    expect(wsEvent.defaultPrevented).toBe(true);

    controller.destroy();
  });

  it("abort prevents late callbacks and clears root", async () => {
    const root = document.createElement("div");
    const callbacks: Array<(exists: boolean) => void> = [];
    const bridge = createBridge({
      wikiExists: vi.fn((_target: string, callback: (exists: boolean) => void) => {
        callbacks.push(callback);
      }),
    });

    const signal = new AbortController();
    const controllerPromise = startViewer(root, "[[linked-note]]", bridge.sourceUrl, bridge, signal.signal);
    signal.abort();
    mermaidGate.release();

    const controller = await controllerPromise;
    callbacks.forEach((cb) => cb(true));
    await flush();

    expect(root.childElementCount).toBe(0);
    expect(bridge.viewerReady).not.toHaveBeenCalled();
    expect(bridge.openWiki).not.toHaveBeenCalled();

    controller.destroy();
  });

  it("fails closed when wikiExists throws synchronously", async () => {
    const root = document.createElement("div");
    const bridge = createBridge({
      wikiExists: vi.fn(() => {
        throw new Error("bridge unavailable");
      }),
    });

    const controllerPromise = startViewer(root, "[[missing]]", bridge.sourceUrl, bridge);
    mermaidGate.release();
    const controller = await controllerPromise;

    const missing = root.querySelector<HTMLAnchorElement>('a[data-wiki-target="missing"]');
    expect(missing?.classList.contains("is-missing")).toBe(true);
    expect(bridge.viewerReady).toHaveBeenCalledTimes(1);

    controller.destroy();
  });

  it("marks missing after wiki timeout when callback never resolves", async () => {
    vi.useFakeTimers();
    const root = document.createElement("div");
    const bridge = createBridge({
      wikiExists: vi.fn(() => {
        // simulate never-callback bridge
      }),
    });

    const controllerPromise = startViewer(root, "[[missing]]", bridge.sourceUrl, bridge);
    mermaidGate.release();
    await vi.advanceTimersByTimeAsync(2000);
    const controller = await controllerPromise;

    const missing = root.querySelector<HTMLAnchorElement>('a[data-wiki-target="missing"]');
    expect(missing?.classList.contains("is-missing")).toBe(true);
    expect(bridge.viewerReady).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);

    controller.destroy();
  });

  it("keeps missing state after timeout when late callback returns true", async () => {
    vi.useFakeTimers();
    const root = document.createElement("div");
    let callback: ((exists: boolean) => void) | null = null;
    const bridge = createBridge({
      wikiExists: vi.fn((_target: string, cb: (exists: boolean) => void) => {
        callback = cb;
      }),
    });

    const controllerPromise = startViewer(root, "[[missing]]", bridge.sourceUrl, bridge);
    mermaidGate.release();
    await vi.advanceTimersByTimeAsync(2000);
    const controller = await controllerPromise;

    const missing = root.querySelector<HTMLAnchorElement>('a[data-wiki-target="missing"]');
    expect(missing?.classList.contains("is-missing")).toBe(true);
    missing?.click();
    expect(bridge.openWiki).toHaveBeenCalledWith("missing");

    const lateCallback = callback;
    expect(lateCallback).not.toBeNull();
    if (!lateCallback) {
      throw new Error("missing wiki callback");
    }
    (lateCallback as (exists: boolean) => void)(true);
    await vi.advanceTimersByTimeAsync(10);

    expect(missing?.classList.contains("is-missing")).toBe(true);
    expect(missing?.classList.contains("is-resolved")).toBe(false);
    missing?.click();
    expect(bridge.openWiki).toHaveBeenCalledWith("missing");

    controller.destroy();
  });

  it("clears wiki timeout on destroy and ignores late callbacks", async () => {
    vi.useFakeTimers();
    const root = document.createElement("div");
    let callback: ((exists: boolean) => void) | null = null;
    const bridge = createBridge({
      wikiExists: vi.fn((_target: string, cb: (exists: boolean) => void) => {
        callback = cb;
      }),
    });

    const abortController = new AbortController();
    const controllerPromise = startViewer(
      root,
      "[[linked-note]]",
      bridge.sourceUrl,
      bridge,
      abortController.signal,
    );
    await flush();
    abortController.abort();
    mermaidGate.release();
    const controller = await controllerPromise;
    controller.destroy();

    expect(vi.getTimerCount()).toBe(0);
    const lateCallback = callback;
    expect(lateCallback).not.toBeNull();
    if (!lateCallback) {
      throw new Error("missing wiki callback");
    }
    (lateCallback as (exists: boolean) => void)(true);
    await vi.advanceTimersByTimeAsync(2100);

    expect(root.childElementCount).toBe(0);
    expect(bridge.viewerReady).not.toHaveBeenCalled();
    expect(bridge.openWiki).not.toHaveBeenCalled();
  });
});
