import { createNavigationState, fitScale, type NavigationState } from "./state";

export interface ViewerElements {
  rail: HTMLElement;
  stage: HTMLElement;
  host: HTMLElement;
  page: HTMLOutputElement;
  zoom: HTMLOutputElement;
}

export interface ViewerOptions {
  slideCount: number;
  slideWidth: number;
  slideHeight: number;
  onRender?: (index: number, host: HTMLElement) => void;
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

export function buildViewerDom(root: HTMLElement): ViewerElements {
  root.innerHTML = `
    <section class="viewer-shell">
      <aside class="viewer-shell__rail" aria-label="Slide thumbnails"></aside>
      <article class="viewer-shell__main">
        <header class="viewer-shell__toolbar">
          <button type="button" data-action="previous" aria-label="Previous slide">Prev</button>
          <button type="button" data-action="next" aria-label="Next slide">Next</button>
          <output class="viewer-shell__page" aria-live="polite"></output>
          <span class="viewer-shell__spacer"></span>
          <button type="button" data-action="zoom-out" aria-label="Zoom out">-</button>
          <output class="viewer-shell__zoom" aria-live="polite"></output>
          <button type="button" data-action="zoom-in" aria-label="Zoom in">+</button>
          <button type="button" data-action="fit" aria-label="Fit slide to stage">Fit</button>
        </header>
        <div class="viewer-shell__stage">
          <div class="viewer-shell__host" role="img" aria-label="Slide surface"></div>
        </div>
      </article>
    </section>
  `;

  return {
    rail: root.querySelector<HTMLElement>(".viewer-shell__rail")!,
    stage: root.querySelector<HTMLElement>(".viewer-shell__stage")!,
    host: root.querySelector<HTMLElement>(".viewer-shell__host")!,
    page: root.querySelector<HTMLOutputElement>(".viewer-shell__page")!,
    zoom: root.querySelector<HTMLOutputElement>(".viewer-shell__zoom")!,
  };
}

export function createViewer(root: HTMLElement, options: ViewerOptions): ViewerController {
  const state = createNavigationState(options.slideCount);
  const elements = buildViewerDom(root);
  const thumbnails: HTMLButtonElement[] = [];
  let fitEnabled = true;

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

  const applyScale = (): void => {
    elements.host.style.transform = `scale(${state.zoom})`;
  };

  const updateStatus = (): void => {
    elements.page.textContent = `${state.currentIndex + 1} / ${state.slideCount}`;
    elements.zoom.textContent = `${Math.round(state.zoom * 100)}%`;
    updateSelection();
    applyScale();
  };

  const render = (index: number): number => {
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
    state.setZoom(fitScale(elements.stage.clientWidth, elements.stage.clientHeight, options.slideWidth, options.slideHeight));
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

  root.addEventListener("click", onClick);
  window.addEventListener("keydown", onKeyDown);

  const resizeObserverCtor = globalThis.ResizeObserver;
  const observer =
    resizeObserverCtor === undefined
      ? null
      : new resizeObserverCtor(() => {
          if (fitEnabled) {
            fit();
          }
        });
  observer?.observe(elements.stage);

  render(0);
  fit();

  return {
    state,
    elements,
    render,
    fit,
    setZoom,
    zoomBy,
    destroy() {
      root.removeEventListener("click", onClick);
      window.removeEventListener("keydown", onKeyDown);
      observer?.disconnect();
    },
  };
}
