import { beforeEach, describe, expect, it, vi } from "vitest";
import { createViewer } from "./viewer";

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
});
