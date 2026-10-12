import {
  getThumbnails,
  loadPresentation,
  renderSlideToElement,
  type LoadedPresentation,
} from "pptx-viewer";
import { createNavigationState, fitScale, type NavigationState } from "./state";

export interface ViewerBridge {
  viewerReady(count: number): void;
  viewerError(message: string): void;
  slideChanged(index: number): void;
}

export interface ViewerElements {
  rail: HTMLElement;
  stage: HTMLElement;
  canvas: HTMLElement;
  host: HTMLElement;
  page: HTMLOutputElement;
  zoom: HTMLOutputElement;
}

export interface ViewerOptions {
  slideCount: number;
  slideWidth: number;
  slideHeight: number;
  onRender?: (index: number, host: HTMLElement) => void;
  onDestroy?: () => void;
}

export interface StartViewerOptions {
  testFailSlide?: number;
  signal?: AbortSignal;
}

export interface ViewerController {
  readonly state: NavigationState;
  readonly elements: ViewerElements;
  render(index: number): number;
  fit(): number;
  setZoom(scale: number): number;
  zoomBy(delta: number): number;
  destroy(): void;
}

/** Empty space kept around the slide when fitting it to the stage. */
export const STAGE_GUTTER = 16;

const ROOT_CONTROLLER_KEY = Symbol("reader-pptx-viewer-controller");
type ViewerRoot = HTMLElement & { [ROOT_CONTROLLER_KEY]?: ViewerController };
const rootControllerMap = new WeakMap<HTMLElement, ViewerController>();

function focusRoot(root: HTMLElement): void {
  try {
    root.focus({ preventScroll: true });
  } catch {
    root.focus();
  }
}

export function buildViewerDom(root: HTMLElement): ViewerElements {
  root.innerHTML = `
    <section class="viewer-shell">
      <aside class="viewer-shell__rail" aria-label="幻灯片缩略图"></aside>
      <article class="viewer-shell__main">
        <header class="viewer-shell__toolbar">
          <button type="button" data-action="previous" aria-label="上一页">上一页</button>
          <button type="button" data-action="next" aria-label="下一页">下一页</button>
          <output class="viewer-shell__page" aria-live="polite"></output>
          <span class="viewer-shell__spacer"></span>
          <button type="button" data-action="zoom-out" aria-label="缩小">-</button>
          <output class="viewer-shell__zoom" aria-live="polite"></output>
          <button type="button" data-action="zoom-in" aria-label="放大">+</button>
          <button type="button" data-action="fit" aria-label="适合窗口">适合窗口</button>
        </header>
        <div class="viewer-shell__stage">
          <div class="viewer-shell__canvas">
            <div class="viewer-shell__host" role="img" aria-label="幻灯片画布"></div>
          </div>
        </div>
      </article>
    </section>
  `;

  return {
    rail: root.querySelector<HTMLElement>(".viewer-shell__rail")!,
    stage: root.querySelector<HTMLElement>(".viewer-shell__stage")!,
    canvas: root.querySelector<HTMLElement>(".viewer-shell__canvas")!,
    host: root.querySelector<HTMLElement>(".viewer-shell__host")!,
    page: root.querySelector<HTMLOutputElement>(".viewer-shell__page")!,
    zoom: root.querySelector<HTMLOutputElement>(".viewer-shell__zoom")!,
  };
}

export function createViewer(root: HTMLElement, options: ViewerOptions): ViewerController {
  const previousController = rootControllerMap.get(root);
  previousController?.destroy();

  root.tabIndex = 0;

  const state = createNavigationState(options.slideCount);
  const elements = buildViewerDom(root);
  const thumbnails: HTMLButtonElement[] = [];
  let fitEnabled = true;
  let disposed = false;
  let observer: ResizeObserver | null = null;
  let panX = 0;
  let panY = 0;
  let drag: { x: number; y: number } | null = null;
  const view = root.ownerDocument.defaultView ?? window;

  elements.host.style.width = `${options.slideWidth}px`;
  elements.host.style.height = `${options.slideHeight}px`;

  for (let index = 0; index < options.slideCount; index += 1) {
    const thumb = root.ownerDocument.createElement("button");
    thumb.type = "button";
    thumb.className = "viewer-shell__thumb";
    thumb.dataset.slideIndex = String(index);
    thumb.textContent = String(index + 1);
    elements.rail.append(thumb);
    thumbnails.push(thumb);
  }

  const updateSelection = (): void => {
    for (const [index, thumb] of thumbnails.entries()) {
      thumb.classList.toggle("is-active", index === state.currentIndex);
    }
  };

  // The host keeps its native slide size and scales from the top-left corner;
  // the canvas carries the scaled size so the slide is centred in the stage.
  // How far the slide may be panned from centre on each axis (0 when it fits).
  const panLimits = (): { x: number; y: number } => {
    const usableWidth = elements.stage.clientWidth - 2 * STAGE_GUTTER;
    const usableHeight = elements.stage.clientHeight - 2 * STAGE_GUTTER;
    return {
      x: Math.max(0, (options.slideWidth * state.zoom - usableWidth) / 2),
      y: Math.max(0, (options.slideHeight * state.zoom - usableHeight) / 2),
    };
  };

  // The host keeps its native slide size and scales from the top-left corner;
  // the canvas carries the scaled size so the slide is centred in the stage.
  const applyScale = (): void => {
    const scaledWidth = options.slideWidth * state.zoom;
    const scaledHeight = options.slideHeight * state.zoom;
    const stageWidth = elements.stage.clientWidth;
    const stageHeight = elements.stage.clientHeight;
    const limits = panLimits();
    panX = Math.max(-limits.x, Math.min(limits.x, panX));
    panY = Math.max(-limits.y, Math.min(limits.y, panY));
    elements.stage.classList.toggle("is-pannable", limits.x > 0 || limits.y > 0);
    elements.host.style.transformOrigin = "0 0";
    elements.host.style.transform = `scale(${state.zoom})`;
    elements.canvas.style.width = `${scaledWidth}px`;
    elements.canvas.style.height = `${scaledHeight}px`;
    elements.canvas.style.left = `${(stageWidth - scaledWidth) / 2 + panX}px`;
    elements.canvas.style.top = `${(stageHeight - scaledHeight) / 2 + panY}px`;
  };

  const panBy = (dx: number, dy: number): void => {
    panX += dx;
    panY += dy;
    applyScale();
  };

  const updateStatus = (): void => {
    elements.page.textContent = `${state.currentIndex + 1} / ${state.slideCount}`;
    elements.zoom.textContent = `${Math.round(state.zoom * 100)}%`;
    updateSelection();
    applyScale();
  };

  const render = (index: number): number => {
    if (disposed) {
      throw new Error("viewer is disposed");
    }
    const nextIndex = state.goTo(index);
    options.onRender?.(nextIndex, elements.host);
    updateStatus();
    return nextIndex;
  };

  const setZoom = (scale: number): number => {
    fitEnabled = false;
    state.setZoom(scale);
    updateStatus();
    return state.zoom;
  };

  const zoomBy = (delta: number): number => {
    fitEnabled = false;
    state.zoomBy(delta);
    updateStatus();
    return state.zoom;
  };

  const fit = (): number => {
    fitEnabled = true;
    panX = 0;
    panY = 0;
    state.setZoom(
      fitScale(
        elements.stage.clientWidth - 2 * STAGE_GUTTER,
        elements.stage.clientHeight - 2 * STAGE_GUTTER,
        options.slideWidth,
        options.slideHeight,
      ),
    );
    updateStatus();
    return state.zoom;
  };

  const goPrevious = (): void => {
    render(state.previous());
  };
  const goNext = (): void => {
    render(state.next());
  };
  const goFirst = (): void => {
    render(state.first());
  };
  const goLast = (): void => {
    render(state.last());
  };

  const onClick = (event: Event): void => {
    const target = (event.target as Element | null)?.closest<HTMLElement>("[data-action],[data-slide-index]");
    if (!target) {
      return;
    }
    focusRoot(root);
    if (target.dataset.slideIndex !== undefined) {
      render(Number(target.dataset.slideIndex));
      return;
    }
    switch (target.dataset.action) {
      case "previous":
        goPrevious();
        break;
      case "next":
        goNext();
        break;
      case "zoom-in":
        zoomBy(0.1);
        break;
      case "zoom-out":
        zoomBy(-0.1);
        break;
      case "fit":
        fit();
        break;
      default:
        break;
    }
  };

  const onKeyDown = (event: KeyboardEvent): void => {
    if ((event.ctrlKey || event.metaKey) && !event.altKey) {
      if (event.key === "=" || event.key === "+") {
        event.preventDefault();
        zoomBy(0.1);
      } else if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        zoomBy(-0.1);
      } else if (event.key === "0") {
        event.preventDefault();
        fit();
      }
      return;
    }
    switch (event.key) {
      case "ArrowLeft":
      case "PageUp":
        event.preventDefault();
        goPrevious();
        break;
      case "ArrowRight":
      case "PageDown":
        event.preventDefault();
        goNext();
        break;
      case "Home":
        event.preventDefault();
        goFirst();
        break;
      case "End":
        event.preventDefault();
        goLast();
        break;
      default:
        break;
    }
  };

  const onWheel = (event: WheelEvent): void => {
    if (event.ctrlKey || event.metaKey) {
      event.preventDefault();
      if (event.deltaY !== 0) {
        zoomBy(event.deltaY < 0 ? 0.1 : -0.1);
      }
      return;
    }
    const limits = panLimits();
    if (limits.x <= 0 && limits.y <= 0) {
      return;
    }
    event.preventDefault();
    if (event.shiftKey) {
      panBy(-(event.deltaY || event.deltaX), 0);
    } else {
      panBy(-event.deltaX, -event.deltaY);
    }
  };

  const onMouseDown = (event: MouseEvent): void => {
    const limits = panLimits();
    if (event.button !== 0 || (limits.x <= 0 && limits.y <= 0)) {
      return;
    }
    event.preventDefault();
    drag = { x: event.clientX, y: event.clientY };
    elements.stage.classList.add("is-panning");
  };

  const onMouseMove = (event: MouseEvent): void => {
    if (!drag) {
      return;
    }
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    drag = { x: event.clientX, y: event.clientY };
    panBy(dx, dy);
  };

  const onMouseUp = (): void => {
    drag = null;
    elements.stage.classList.remove("is-panning");
  };

  root.addEventListener("click", onClick);
  root.addEventListener("keydown", onKeyDown);
  elements.stage.addEventListener("wheel", onWheel, { passive: false });
  elements.stage.addEventListener("mousedown", onMouseDown);
  view.addEventListener("mousemove", onMouseMove);
  view.addEventListener("mouseup", onMouseUp);

  const controller: ViewerController = {
    state,
    elements,
    render,
    fit,
    setZoom,
    zoomBy,
    destroy() {
      if (disposed) {
        return;
      }
      disposed = true;
      root.removeEventListener("click", onClick);
      root.removeEventListener("keydown", onKeyDown);
      elements.stage.removeEventListener("wheel", onWheel);
      elements.stage.removeEventListener("mousedown", onMouseDown);
      view.removeEventListener("mousemove", onMouseMove);
      view.removeEventListener("mouseup", onMouseUp);
      observer?.disconnect();
      try {
        options.onDestroy?.();
      } finally {
        if (rootControllerMap.get(root) === controller) {
          rootControllerMap.delete(root);
        }
        const ownedRoot = root as ViewerRoot;
        if (ownedRoot[ROOT_CONTROLLER_KEY] === controller) {
          delete ownedRoot[ROOT_CONTROLLER_KEY];
        }
      }
    },
  };

  try {
    const resizeObserverCtor = globalThis.ResizeObserver;
    observer =
      resizeObserverCtor === undefined
        ? null
        : new resizeObserverCtor(() => {
            if (fitEnabled) {
              fit();
            } else {
              applyScale();
            }
          });
    observer?.observe(elements.stage);

    // Register before callbacks so any initialization failure can remove all ownership atomically.
    Object.defineProperty(root, ROOT_CONTROLLER_KEY, {
      configurable: true,
      enumerable: false,
      writable: true,
      value: controller,
    });
    rootControllerMap.set(root, controller);

    render(0);
    fit();
    focusRoot(root);
    return controller;
  } catch (error) {
    controller.destroy();
    root.replaceChildren();
    throw error;
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function requireLocalFileUrl(sourceUrl: string): void {
  let source: URL;
  try {
    source = new URL(sourceUrl);
  } catch {
    throw new Error("Reader requires a local file URL");
  }
  if (source.protocol !== "file:") {
    throw new Error("Reader requires a local file URL");
  }
}

export async function startViewer(
  root: HTMLElement,
  sourceUrl: string,
  bridge: ViewerBridge,
  options: StartViewerOptions = {},
): Promise<ViewerController | undefined> {
  let presentation: LoadedPresentation | undefined;
  let controller: ViewerController | undefined;
  let cleaned = false;
  const cleanupPresentation = (): void => {
    if (cleaned) {
      return;
    }
    cleaned = true;
    presentation?.cleanup();
  };
  const onAbort = (): void => {
    controller?.destroy();
  };
  options.signal?.addEventListener("abort", onAbort, { once: true });

  try {
    requireLocalFileUrl(sourceUrl);
    if (options.signal?.aborted) {
      options.signal.removeEventListener("abort", onAbort);
      return undefined;
    }
    presentation = await loadPresentation(sourceUrl);
    if (options.signal?.aborted) {
      cleanupPresentation();
      options.signal.removeEventListener("abort", onAbort);
      return undefined;
    }
    if (presentation.slides.length === 0) {
      throw new Error("presentation has no slides");
    }

    const renderWidth = presentation.slideSize.width;
    const renderHeight = presentation.slideSize.height;
    root.dataset.elementTypes = JSON.stringify(
      presentation.slides.map((slide) =>
        [...new Set(slide.elements.map((element) => element.type))].sort().join(","),
      ),
    );
    controller = createViewer(root, {
      slideCount: presentation.slides.length,
      slideWidth: renderWidth,
      slideHeight: renderHeight,
      onRender(index, host) {
        try {
          if (options.testFailSlide === index) {
            throw new Error("injected slide failure");
          }
          renderSlideToElement(presentation!, index, host, {
            width: renderWidth,
            height: renderHeight,
          });
          delete host.dataset.slideError;
        } catch (error) {
          const placeholder = root.ownerDocument.createElement("div");
          placeholder.className = "viewer-shell__slide-error";
          placeholder.textContent = `第 ${index + 1} 页无法渲染`;
          host.replaceChildren(placeholder);
          host.dataset.slideError = errorMessage(error);
        }
        bridge.slideChanged(index);
      },
      onDestroy() {
        options.signal?.removeEventListener("abort", onAbort);
        try {
          cleanupPresentation();
        } finally {
          root.replaceChildren();
        }
      },
    });
    if (options.signal?.aborted) {
      controller.destroy();
      return undefined;
    }

    try {
      const thumbnails = getThumbnails(presentation, 200);
      const buttons = controller.elements.rail.querySelectorAll<HTMLButtonElement>(
        "[data-slide-index]",
      );
      thumbnails.forEach((thumbnail, index) => {
        buttons[index]?.replaceChildren(thumbnail);
      });
    } catch (error) {
      controller.elements.rail.dataset.thumbnailError = errorMessage(error);
    }

    bridge.viewerReady(presentation.slides.length);
    return controller;
  } catch (error) {
    options.signal?.removeEventListener("abort", onAbort);
    if (controller) {
      controller.destroy();
    } else {
      cleanupPresentation();
    }
    bridge.viewerError(errorMessage(error));
    throw error;
  }
}
