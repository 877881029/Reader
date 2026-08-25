# Task 3 Report - Official Renderer Integration (with Important fixes)

## Scope

- Integrated official `pptx-viewer@0.2.2` APIs: `loadPresentation`, `renderSlideToElement`, and `getThumbnails`.
- Preserved master/layout inheritance and Task 2 navigation, keyboard, zoom, fit, and focus behavior.
- Added Qt WebChannel bootstrap, local `file:` URL enforcement, bridge callbacks, per-slide error isolation, empty-deck failure, and presentation cleanup.
- Built the real offline bundle under `assets/pptx-viewer/`.
- Did not modify the Python product pipeline.

## Important Fixes

### Cancellation and ownership

- `startViewer` accepts `AbortSignal` and returns `Promise<ViewerController | undefined>`.
- Abort during `await loadPresentation` cleans the resolved presentation exactly once without mounting or reporting ready.
- Abort after mounting destroys the controller idempotently.
- `main.ts` retains the resolved controller and exposes `window.readerPptxDispose()`.
- `pagehide` and `beforeunload` use the same disposal path for Task 5 integration.

### Atomic initialization cleanup

- Initial render/onRender failures remove click/keydown listeners, disconnect `ResizeObserver`, clear WeakMap/symbol ownership and partial DOM, then rethrow.
- Initial `bridge.slideChanged` failures use that path.
- The same root can then remount; keyboard and click each trigger only the new viewer once.
- Cleanup has a once guard so create failure and start catch cannot clean the presentation twice.

### Minor regression coverage

- Clicking inside a real official SVG thumbnail navigates through event bubbling.
- Double destroy and double abort are safe.
- Public `render()` after destroy throws `viewer is disposed`, avoiding access to a cleaned presentation.

## Strict RED Evidence

Command:

`npm --prefix web/pptx-viewer test -- src/viewer.test.ts src/main.test.ts`

Before implementation: `8 failed, 10 passed`.

Expected failures covered:

- deferred-load abort still mounted and returned a controller;
- main exposed no dispose function, passed no signal, and retained no controller;
- initialization failure did not disconnect the observer;
- disposed render did not reject;
- slideChanged initialization failure did not clean atomically.

## Final Verification

- Focused Web tests: `18 passed`
- `npm --prefix web/pptx-viewer test`: `23 passed`
- `npm --prefix web/pptx-viewer run typecheck`: passed
- `npm --prefix web/pptx-viewer run build`: passed; emitted `index-BJ-YEzKG.js`
- Python resource tests: `4 passed`
- Python full suite: `203 passed in 53.22s`
- IDE diagnostics: no errors

## Commits and Boundaries

- Task 3: `5989ade`
- Important fixes: `2fd6f7a`
- No amend, git config change, or push.
- The known Vite qrc warning is expected; the output retains `qrc:///qtwebchannel/qwebchannel.js` for Qt.
