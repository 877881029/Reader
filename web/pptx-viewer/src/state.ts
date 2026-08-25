export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 4;

export interface NavigationState {
  readonly slideCount: number;
  currentIndex: number;
  zoom: number;
  goTo(index: number): number;
  previous(): number;
  next(): number;
  first(): number;
  last(): number;
  pageUp(): number;
  pageDown(): number;
  setZoom(scale: number): number;
  zoomBy(delta: number): number;
}

function clampIndex(index: number, maxIndex: number): number {
  const value = Number.isFinite(index) ? Math.trunc(index) : 0;
  return Math.max(0, Math.min(maxIndex, value));
}

function clampZoom(scale: number): number {
  if (!Number.isFinite(scale)) {
    return 1;
  }
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, scale));
}

export function createNavigationState(slideCount: number): NavigationState {
  if (!Number.isInteger(slideCount) || slideCount < 1) {
    throw new Error("presentation has no slides");
  }

  const maxIndex = slideCount - 1;
  const state: NavigationState = {
    slideCount,
    currentIndex: 0,
    zoom: 1,
    goTo(index: number) {
      state.currentIndex = clampIndex(index, maxIndex);
      return state.currentIndex;
    },
    previous() {
      return state.goTo(state.currentIndex - 1);
    },
    next() {
      return state.goTo(state.currentIndex + 1);
    },
    first() {
      return state.goTo(0);
    },
    last() {
      return state.goTo(maxIndex);
    },
    pageUp() {
      return state.previous();
    },
    pageDown() {
      return state.next();
    },
    setZoom(scale: number) {
      state.zoom = clampZoom(scale);
      return state.zoom;
    },
    zoomBy(delta: number) {
      return state.setZoom(state.zoom + delta);
    },
  };

  return state;
}

export function fitScale(stageWidth: number, stageHeight: number, slideWidth: number, slideHeight: number): number {
  if (stageWidth <= 0 || stageHeight <= 0 || slideWidth <= 0 || slideHeight <= 0) {
    return 1;
  }
  return clampZoom(Math.min(stageWidth / slideWidth, stageHeight / slideHeight));
}
