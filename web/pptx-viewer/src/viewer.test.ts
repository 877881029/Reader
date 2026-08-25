import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import * as pptxViewer from "pptx-viewer";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fitScale } from "./state";
import { createViewer, startViewer } from "./viewer";

vi.mock("pptx-viewer", async (importOriginal) => {
  const official = await importOriginal<typeof import("pptx-viewer")>();
  return {
    ...official,
    loadPresentation: vi.fn(official.loadPresentation),
  };
});

const fixture = resolve(process.cwd(), "../../tests/fixtures/pptx/visual-elements.pptx");

function mountRoot(): HTMLDivElement {
  const root = document.createElement("div");
  document.body.innerHTML = "";
  document.body.append(root);
  return root;
}

function trackElementSize(element: HTMLElement, width: number, height: number): (w: number, h: number) => void {
  let currentWidth = width;
  let currentHeight = height;
  Object.defineProperty(element, "clientWidth", {
    configurable: true,
    get: () => currentWidth,
  });
  Object.defineProperty(element, "clientHeight", {
    configurable: true,
    get: () => currentHeight,
  });
  return (w: number, h: number) => {
    currentWidth = w;
    currentHeight = h;
  };
}

function dispatchArrowRight(target: HTMLElement): void {
  target.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
}

function fakePresentation(
  cleanup = vi.fn(),
  slideCount = 1,
): pptxViewer.LoadedPresentation {
  return {
    slides: Array.from({ length: slideCount }, (_, index) => ({
      id: `slide-${index + 1}`,
      elements: [],
    })),
    slideSize: { width: 960, height: 540 },
    slideLayouts: new Map(),
    slideMasters: new Map(),
    cleanup,
  } as unknown as pptxViewer.LoadedPresentation;
}

describe("viewer controls", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("handles prev/next buttons, keyboard keys, and thumbnail click", () => {
    const root = mountRoot();
    const rendered: number[] = [];
    const viewer = createViewer(root, {
      slideCount: 5,
      slideWidth: 1600,
      slideHeight: 900,
      onRender(index) {
        rendered.push(index);
      },
    });

    const setStage = trackElementSize(viewer.elements.stage, 800, 600);
    viewer.fit();
    setStage(800, 600);

    const next = root.querySelector<HTMLButtonElement>('[data-action="next"]');
    const prev = root.querySelector<HTMLButtonElement>('[data-action="previous"]');
    const thumb3 = root.querySelector<HTMLButtonElement>('[data-slide-index="3"]');

    next?.click();
    next?.click();
    prev?.click();
    thumb3?.click();

    root.focus();
    root.dispatchEvent(new KeyboardEvent("keydown", { key: "Home" }));
    root.dispatchEvent(new KeyboardEvent("keydown", { key: "End" }));
    root.dispatchEvent(new KeyboardEvent("keydown", { key: "PageUp" }));
    root.dispatchEvent(new KeyboardEvent("keydown", { key: "PageDown" }));

    expect(viewer.state.currentIndex).toBe(4);
    expect(rendered).toContain(3);
    expect(viewer.elements.page.textContent).toContain("5 / 5");
  });

  it("routes ArrowRight only to the focused viewer and ignores destroyed viewer keydown", () => {
    const firstRoot = document.createElement("div");
    const secondRoot = document.createElement("div");
    document.body.append(firstRoot, secondRoot);

    const first = createViewer(firstRoot, {
      slideCount: 5,
      slideWidth: 1600,
      slideHeight: 900,
    });
    const second = createViewer(secondRoot, {
      slideCount: 5,
      slideWidth: 1600,
      slideHeight: 900,
    });

    firstRoot.focus();
    dispatchArrowRight(firstRoot);
    expect(first.state.currentIndex).toBe(1);
    expect(second.state.currentIndex).toBe(0);

    secondRoot.focus();
    dispatchArrowRight(secondRoot);
    expect(first.state.currentIndex).toBe(1);
    expect(second.state.currentIndex).toBe(1);

    first.destroy();
    firstRoot.focus();
    dispatchArrowRight(firstRoot);
    expect(first.state.currentIndex).toBe(1);
    expect(second.state.currentIndex).toBe(1);
  });

  it("auto-destroys previous controller when mounting again on same root", () => {
    const root = mountRoot();
    const first = createViewer(root, {
      slideCount: 5,
      slideWidth: 1600,
      slideHeight: 900,
    });
    const second = createViewer(root, {
      slideCount: 5,
      slideWidth: 1600,
      slideHeight: 900,
    });

    root.focus();
    dispatchArrowRight(root);
    expect(second.state.currentIndex).toBe(1);
    expect(first.state.currentIndex).toBe(0);
  });

  it("applies real zoom in/out and clamps to 25%-400%", () => {
    const root = mountRoot();
    const viewer = createViewer(root, {
      slideCount: 2,
      slideWidth: 1600,
      slideHeight: 900,
    });

    const zoomIn = root.querySelector<HTMLButtonElement>('[data-action="zoom-in"]');
    const zoomOut = root.querySelector<HTMLButtonElement>('[data-action="zoom-out"]');

    viewer.setZoom(4);
    zoomIn?.click();
    expect(viewer.state.zoom).toBe(4);
    expect(viewer.elements.zoom.textContent).toBe("400%");

    viewer.setZoom(0.25);
    zoomOut?.click();
    expect(viewer.state.zoom).toBe(0.25);
    expect(viewer.elements.zoom.textContent).toBe("25%");
  });

  it("does not throw at zero stage size and recomputes fit after ResizeObserver", () => {
    const root = mountRoot();
    const callbacks: ResizeObserverCallback[] = [];
    const originalObserver = globalThis.ResizeObserver;
    const disconnect = vi.fn();

    class FakeResizeObserver {
      constructor(callback: ResizeObserverCallback) {
        callbacks.push(callback);
      }

      observe(): void {}

      disconnect(): void {
        disconnect();
      }
    }

    // @ts-expect-error test stub
    globalThis.ResizeObserver = FakeResizeObserver;

    const viewer = createViewer(root, {
      slideCount: 1,
      slideWidth: 1600,
      slideHeight: 900,
    });
    const setStage = trackElementSize(viewer.elements.stage, 0, 0);

    expect(() => viewer.fit()).not.toThrow();
    expect(viewer.state.zoom).toBe(1);

    setStage(800, 600);
    callbacks[0]?.([], {} as ResizeObserver);
    expect(viewer.state.zoom).toBeCloseTo(0.5, 6);

    viewer.destroy();
    expect(disconnect).toHaveBeenCalledTimes(1);
    globalThis.ResizeObserver = originalObserver;
  });

  it("focuses root after control and thumbnail clicks", () => {
    const root = mountRoot();
    createViewer(root, {
      slideCount: 3,
      slideWidth: 1600,
      slideHeight: 900,
    });

    const zoomIn = root.querySelector<HTMLButtonElement>('[data-action="zoom-in"]');
    const thumb1 = root.querySelector<HTMLButtonElement>('[data-slide-index="1"]');

    zoomIn?.click();
    expect(document.activeElement).toBe(root);

    thumb1?.click();
    expect(document.activeElement).toBe(root);
  });

  it("atomically cleans listeners and observer when initial render throws", () => {
    const root = mountRoot();
    const disconnect = vi.fn();
    const originalObserver = globalThis.ResizeObserver;
    class FakeResizeObserver {
      constructor(_callback: ResizeObserverCallback) {}
      observe(): void {}
      disconnect(): void {
        disconnect();
      }
    }
    // @ts-expect-error test stub
    globalThis.ResizeObserver = FakeResizeObserver;
    const failedRender = vi.fn(() => {
      throw new Error("bridge slideChanged failed");
    });

    expect(() =>
      createViewer(root, {
        slideCount: 4,
        slideWidth: 960,
        slideHeight: 540,
        onRender: failedRender,
      }),
    ).toThrow("bridge slideChanged failed");
    expect(disconnect).toHaveBeenCalledOnce();

    const successfulRender = vi.fn();
    const second = createViewer(root, {
      slideCount: 4,
      slideWidth: 960,
      slideHeight: 540,
      onRender: successfulRender,
    });
    dispatchArrowRight(root);
    root.querySelector<HTMLButtonElement>('[data-action="next"]')?.click();

    expect(failedRender).toHaveBeenCalledOnce();
    expect(successfulRender.mock.calls.map(([index]) => index)).toEqual([0, 1, 2]);
    expect(second.state.currentIndex).toBe(2);
    second.destroy();
    globalThis.ResizeObserver = originalObserver;
  });
});

describe("official renderer integration", () => {
  beforeEach(() => {
    const NativeURL = globalThis.URL;
    class TestURL extends NativeURL {
      static createObjectURL = vi.fn(() => "blob:reader-pptx-test");
      static revokeObjectURL = vi.fn();
    }
    vi.stubGlobal("URL", TestURL);
  });

  afterEach(() => {
    document.body.replaceChildren();
    vi.restoreAllMocks();
    vi.mocked(pptxViewer.loadPresentation).mockReset();
    vi.unstubAllGlobals();
  });

  it("loads inherited content, pictures, tables, charts, missing fonts, and cleans up", async () => {
    const bytes = await readFile(fixture);
    const official = await vi.importActual<typeof import("pptx-viewer")>("pptx-viewer");
    const presentation = await official.loadPresentation(new Uint8Array(bytes));
    const cleanup = vi.spyOn(presentation, "cleanup");

    expect(presentation.slides).toHaveLength(4);
    expect(presentation.slideLayouts.size).toBeGreaterThan(0);
    expect(presentation.slideMasters.size).toBeGreaterThan(0);
    expect(presentation.slides[0]?.elements.some((element) => element.type === "image")).toBe(true);
    expect(presentation.slides[1]?.elements.some((element) => element.type === "table")).toBe(true);
    expect(presentation.slides[2]?.elements.some((element) => element.type === "chart")).toBe(true);

    const host = document.createElement("div");
    document.body.append(host);
    pptxViewer.renderSlideToElement(presentation, 0, host, { width: 960, height: 540 });
    expect(host.querySelector("svg image")).not.toBeNull();
    pptxViewer.renderSlideToElement(presentation, 1, host, { width: 960, height: 540 });
    expect(host.querySelector("foreignObject table")).not.toBeNull();
    pptxViewer.renderSlideToElement(presentation, 2, host, { width: 960, height: 540 });
    expect(host.querySelectorAll("svg rect, svg path").length).toBeGreaterThan(3);
    expect(() =>
      pptxViewer.renderSlideToElement(presentation, 3, host, { width: 960, height: 540 }),
    ).not.toThrow();
    expect(host.querySelector("svg")).not.toBeNull();

    presentation.cleanup();
    expect(cleanup).toHaveBeenCalledOnce();
  });

  it("wires official rendering into controls and contains a single-slide failure", async () => {
    const bytes = await readFile(fixture);
    const official = await vi.importActual<typeof import("pptx-viewer")>("pptx-viewer");
    const presentation = await official.loadPresentation(new Uint8Array(bytes));
    const cleanup = vi.spyOn(presentation, "cleanup");
    vi.mocked(pptxViewer.loadPresentation).mockResolvedValue(presentation);

    const resizeCallbacks: ResizeObserverCallback[] = [];
    const disconnect = vi.fn();
    class FakeResizeObserver {
      constructor(callback: ResizeObserverCallback) {
        resizeCallbacks.push(callback);
      }
      observe(): void {}
      disconnect(): void {
        disconnect();
      }
    }
    vi.stubGlobal("ResizeObserver", FakeResizeObserver);
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1000);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(500);

    const root = mountRoot();
    const bridge = {
      viewerReady: vi.fn(),
      viewerError: vi.fn(),
      slideChanged: vi.fn(),
    };
    const controller = await startViewer(root, "file:///fixture.pptx", bridge, {
      testFailSlide: 1,
    });
    if (!controller) {
      throw new Error("viewer unexpectedly cancelled");
    }

    expect(bridge.viewerReady).toHaveBeenCalledWith(4);
    expect(root.querySelector(".viewer-shell__thumb svg")).not.toBeNull();
    const expectedFit = Math.round(
      fitScale(1000, 500, presentation.slideSize.width, presentation.slideSize.height) * 100,
    );
    expect(controller.elements.zoom.textContent).toBe(`${expectedFit}%`);
    resizeCallbacks[0]?.([], {} as ResizeObserver);
    expect(controller.elements.zoom.textContent).toBe(`${expectedFit}%`);

    root.querySelector<HTMLButtonElement>('[data-action="next"]')?.click();
    expect(controller.elements.host.querySelector(".viewer-shell__slide-error")).not.toBeNull();
    expect(controller.elements.host.dataset.slideError).toContain("injected slide failure");
    root.querySelector<HTMLButtonElement>('[data-action="next"]')?.click();
    expect(controller.elements.host.querySelector("svg")).not.toBeNull();
    expect(controller.elements.host.querySelector(".viewer-shell__slide-error")).toBeNull();
    expect(bridge.viewerError).not.toHaveBeenCalled();
    expect(bridge.slideChanged).toHaveBeenLastCalledWith(2);
    root.querySelector<SVGElement>('[data-slide-index="3"] svg')?.dispatchEvent(
      new MouseEvent("click", { bubbles: true }),
    );
    expect(bridge.slideChanged).toHaveBeenLastCalledWith(3);

    for (let count = 0; count < 50; count += 1) {
      root.querySelector<HTMLButtonElement>('[data-action="zoom-in"]')?.click();
    }
    expect(controller.elements.zoom.textContent).toBe("400%");
    for (let count = 0; count < 50; count += 1) {
      root.querySelector<HTMLButtonElement>('[data-action="zoom-out"]')?.click();
    }
    expect(controller.elements.zoom.textContent).toBe("25%");

    controller.destroy();
    controller.destroy();
    expect(disconnect).toHaveBeenCalledOnce();
    expect(cleanup).toHaveBeenCalledOnce();
    expect(root.children).toHaveLength(0);
    expect(() => controller.render(0)).toThrow("viewer is disposed");
  });

  it("rejects an empty deck as a whole-presentation error and cleans it up", async () => {
    const cleanup = vi.fn();
    vi.mocked(pptxViewer.loadPresentation).mockResolvedValue({
      slides: [],
      cleanup,
    } as unknown as pptxViewer.LoadedPresentation);
    const bridge = {
      viewerReady: vi.fn(),
      viewerError: vi.fn(),
      slideChanged: vi.fn(),
    };

    await expect(startViewer(mountRoot(), "file:///empty.pptx", bridge)).rejects.toThrow(
      "presentation has no slides",
    );
    expect(bridge.viewerError).toHaveBeenCalledWith("presentation has no slides");
    expect(cleanup).toHaveBeenCalledOnce();
  });

  it("cancels while presentation loading without mounting or reporting ready", async () => {
    let resolveLoad!: (presentation: pptxViewer.LoadedPresentation) => void;
    vi.mocked(pptxViewer.loadPresentation).mockReturnValue(
      new Promise((resolve) => {
        resolveLoad = resolve;
      }),
    );
    const cleanup = vi.fn();
    const bridge = {
      viewerReady: vi.fn(),
      viewerError: vi.fn(),
      slideChanged: vi.fn(),
    };
    const abortController = new AbortController();
    const root = mountRoot();

    const pending = startViewer(root, "file:///deferred.pptx", bridge, {
      signal: abortController.signal,
    });
    abortController.abort();
    resolveLoad(fakePresentation(cleanup));

    await expect(pending).resolves.toBeUndefined();
    expect(root.children).toHaveLength(0);
    expect(bridge.viewerReady).not.toHaveBeenCalled();
    expect(bridge.slideChanged).not.toHaveBeenCalled();
    expect(bridge.viewerError).not.toHaveBeenCalled();
    expect(cleanup).toHaveBeenCalledOnce();
  });

  it("aborts a mounted controller once and makes public render reject disposal", async () => {
    const cleanup = vi.fn();
    vi.mocked(pptxViewer.loadPresentation).mockResolvedValue(fakePresentation(cleanup));
    const bridge = {
      viewerReady: vi.fn(),
      viewerError: vi.fn(),
      slideChanged: vi.fn(),
    };
    const abortController = new AbortController();
    const root = mountRoot();
    const controller = await startViewer(root, "file:///mounted.pptx", bridge, {
      signal: abortController.signal,
    });

    expect(controller).toBeDefined();
    abortController.abort();
    abortController.abort();
    controller?.destroy();

    expect(cleanup).toHaveBeenCalledOnce();
    expect(root.children).toHaveLength(0);
    expect(() => controller?.render(0)).toThrow("viewer is disposed");
  });

  it("cleans an initialization-time slideChanged failure and remounts once", async () => {
    const disconnect = vi.fn();
    class FakeResizeObserver {
      constructor(_callback: ResizeObserverCallback) {}
      observe(): void {}
      disconnect(): void {
        disconnect();
      }
    }
    vi.stubGlobal("ResizeObserver", FakeResizeObserver);
    const firstCleanup = vi.fn();
    const secondCleanup = vi.fn();
    vi.mocked(pptxViewer.loadPresentation)
      .mockResolvedValueOnce(fakePresentation(firstCleanup))
      .mockResolvedValueOnce(fakePresentation(secondCleanup, 4));
    const badBridge = {
      viewerReady: vi.fn(),
      viewerError: vi.fn(),
      slideChanged: vi.fn(() => {
        throw new Error("bridge slideChanged failed");
      }),
    };
    const root = mountRoot();

    await expect(startViewer(root, "file:///first.pptx", badBridge)).rejects.toThrow(
      "bridge slideChanged failed",
    );
    expect(firstCleanup).toHaveBeenCalledOnce();
    expect(disconnect).toHaveBeenCalledOnce();

    const goodBridge = {
      viewerReady: vi.fn(),
      viewerError: vi.fn(),
      slideChanged: vi.fn(),
    };
    const second = await startViewer(root, "file:///second.pptx", goodBridge);
    dispatchArrowRight(root);
    root.querySelector<HTMLButtonElement>('[data-action="next"]')?.click();

    expect(badBridge.slideChanged).toHaveBeenCalledOnce();
    expect(goodBridge.slideChanged.mock.calls.map(([index]) => index)).toEqual([0, 1, 2]);
    second?.destroy();
    expect(secondCleanup).toHaveBeenCalledOnce();
  });
});
