# Task 2 Report - Viewer State, Navigation, Zoom, Fit (with Important review fix)

## Scope

- Completed Task 2 baseline with strict TDD.
- Applied Important review fix with strict RED:
  - per-instance keyboard isolation;
  - root-scoped listeners/focus behavior;
  - same-root remount auto-destroy to prevent stale closures/listener leaks.
- Rendering remains placeholder-only (Task 3 will integrate real `pptx-viewer` rendering).

## RED Evidence (Important review fix)

- Added failing tests first in `src/viewer.test.ts`:
  - focused first viewer + `ArrowRight` only advances first;
  - focused second viewer + `ArrowRight` only advances second;
  - `destroy()` first viewer then keydown on first root has no effect;
  - same root remount auto-destroys previous controller;
  - click on toolbar/thumbnail focuses root.
- Ran:
  - `npm --prefix web/pptx-viewer test -- src/viewer.test.ts`
- RED failures observed before implementation:
  - keyboard events were still window-scoped;
  - focused routing assertions failed;
  - same-root remount isolation assertion failed;
  - click focus assertion failed.

## Implementation Changes

- `src/viewer.ts`
  - moved keydown registration from `window` to `root`.
  - enforced `root.tabIndex = 0`.
  - added `focusRoot(root)` and called it on:
    - initial mount;
    - toolbar/thumbnail click handling (`preventScroll` with safe fallback).
  - introduced same-root lifecycle guard:
    - `WeakMap<HTMLElement, ViewerController>` tracks active controller per root;
    - `createViewer` auto-destroys existing controller before rebuilding DOM;
    - `destroy()` removes root keydown/click listeners, disconnects observer, clears map entry.
  - kept Symbol-based root attachment for diagnostics (`ROOT_CONTROLLER_KEY`).

- `src/viewer.test.ts`
  - expanded to validate multi-instance keyboard isolation, destroy behavior, remount behavior, and root focus on click.
  - keyboard dispatch now targets root to match root-scoped listener design.

## GREEN and Regression Evidence

- Focused viewer GREEN:
  - `npm --prefix web/pptx-viewer test -- src/viewer.test.ts` -> passed (`6` tests).

- Required web checks:
  - `npm --prefix web/pptx-viewer test` -> passed (`12` tests).
  - `npm --prefix web/pptx-viewer run typecheck` -> passed.
  - `npm --prefix web/pptx-viewer run build` -> passed.

- Required Python checks:
  - `python -m pytest tests/test_pptx_web_assets.py` -> passed (`4` tests).
  - `python -m pytest` -> passed (`203` tests).

## Status Sync

- Updated `docs/STATUS.md` with Task 2 Important review fix completion note.

## Risks / Concerns

- Task 2 still intentionally does not render real PPTX content yet.
- Task 3 bridge integration must preserve root-scoped event isolation when wiring renderer callbacks.
