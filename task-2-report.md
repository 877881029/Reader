# Task 2 Report - Viewer State, Navigation, Zoom, and Fit

## Scope

- Implemented Task 2 in `web/pptx-viewer` with strict TDD flow (RED -> GREEN -> full verification).
- Kept rendering as placeholder only; no real `pptx-viewer` slide rendering integration (reserved for Task 3).

## RED Evidence

- Added `src/state.test.ts` and `src/viewer.test.ts` first.
- Ran:
  - `npm --prefix web/pptx-viewer test -- src/state.test.ts src/viewer.test.ts`
- RED failure observed as expected:
  - `Failed to resolve import "./state"`
  - `Failed to resolve import "./viewer"`

## Implementation

- Added `src/state.ts`
  - `NavigationState` with `goTo/previous/next/first/last/pageUp/pageDown`.
  - Empty deck rejection: throws `presentation has no slides`.
  - Navigation clamp to `[0, slideCount - 1]`.
  - Zoom clamp range: `25%` to `400%` (`MIN_ZOOM=0.25`, `MAX_ZOOM=4`).
  - `fitScale(stageW, stageH, slideW, slideH)`:
    - ratio fit by stage/slide dimensions.
    - returns `1` for any zero/non-positive dimension (safe defer).

- Added `src/viewer.ts`
  - Viewer DOM builder (left thumbnail rail + right toolbar/stage two-column layout).
  - Controls:
    - Buttons: `previous`, `next`, `zoom-in`, `zoom-out`, `fit`.
    - Keyboard: `ArrowLeft/ArrowRight`, `PageUp/PageDown`, `Home/End`.
    - Thumbnail click via `data-slide-index`.
  - Fit/zoom behavior:
    - real zoom delta (`+0.1` / `-0.1`) with clamp.
    - fit recalculates from stage/slide dimensions.
  - Resizing:
    - safe when stage initially `0x0` (no throw).
    - when `ResizeObserver` exists, auto-refit on stage resize.
    - when `ResizeObserver` does not exist, degrades safely.

- Updated `src/main.ts`
  - Switched scaffold to `createViewer(...)` bootstrap with placeholder slide rendering.

- Updated `src/style.css`
  - Completed two-column viewer styling (rail, toolbar, stage, host, active thumbnail).

## GREEN and Regression Evidence

- Focused GREEN:
  - `npm --prefix web/pptx-viewer test -- src/state.test.ts src/viewer.test.ts`
  - Result: passed (`8` tests).

- Required web checks:
  - `npm --prefix web/pptx-viewer test` -> passed (`9` tests).
  - `npm --prefix web/pptx-viewer run typecheck` -> passed.
  - `npm --prefix web/pptx-viewer run build` -> passed.

- Required Python checks:
  - Related resource test: `python -m pytest tests/test_pptx_web_assets.py` -> passed (`4` tests).
  - Full suite: `python -m pytest` -> passed (`203` tests).

## Status Sync

- Updated `docs/STATUS.md`:
  - Added Task 2 completion entry under "已完成".
  - Moved "下一步" to Task 3 bridge/render integration.

## Risks / Concerns

- Task 2 intentionally keeps placeholder slide host; no real PPTX render tree yet.
- Keyboard listener is bound to `window`; behavior is correct for current shell but may need focus-scoping refinements when bridge events are introduced in Task 3.
