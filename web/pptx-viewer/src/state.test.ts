import { describe, expect, it } from "vitest";
import { createNavigationState, fitScale, MAX_ZOOM, MIN_ZOOM } from "./state";

describe("navigation state", () => {
  it("rejects empty decks and clamps navigation", () => {
    expect(() => createNavigationState(0)).toThrow("presentation has no slides");

    const state = createNavigationState(3);
    expect(state.currentIndex).toBe(0);
    expect(state.goTo(99)).toBe(2);
    expect(state.previous()).toBe(1);
    expect(state.goTo(-10)).toBe(0);
  });

  it("supports Home/End/PageUp/PageDown style navigation", () => {
    const state = createNavigationState(4);
    expect(state.last()).toBe(3);
    expect(state.pageUp()).toBe(2);
    expect(state.pageDown()).toBe(3);
    expect(state.first()).toBe(0);
  });

  it("clamps zoom between 25% and 400%", () => {
    const state = createNavigationState(2);
    expect(state.setZoom(10)).toBe(MAX_ZOOM);
    expect(state.zoomBy(-20)).toBe(MIN_ZOOM);
    expect(state.setZoom(1.75)).toBe(1.75);
  });
});

describe("fitScale", () => {
  it("fits by stage and slide ratio", () => {
    expect(fitScale(1000, 500, 1600, 900)).toBeCloseTo(500 / 900);
    expect(fitScale(800, 900, 1600, 900)).toBeCloseTo(0.5);
  });

  it("defers safely when stage or slide size is zero", () => {
    expect(fitScale(0, 900, 1600, 900)).toBe(1);
    expect(fitScale(900, 0, 1600, 900)).toBe(1);
    expect(fitScale(900, 900, 0, 900)).toBe(1);
    expect(fitScale(900, 900, 1600, 0)).toBe(1);
  });
});
