# Markdown Visual Preview Task 3 Report

## Original Task 3 (RED/GREEN)

### RED
- `npm test -- src/mermaid.test.ts src/viewer.test.ts`
- Failure matched missing implementations (`./mermaid`, `./viewer` unresolved).

### GREEN
- Implemented strict Mermaid per-block rendering and isolated error replacement (`textContent` source write).
- Implemented `startViewer(...)` lifecycle with WeakMap ownership, wiki resolved/missing bridge, remote anchor `preventDefault`, abort/destroy late-callback suppression.
- Implemented Qt bootstrap in `main.ts` (`QWebChannel` + `bridge.sourceUrl` fetch + `readerMdDispose`).
- Added bootstrap fixed-error no-path-leak tests.

### Original verification
- `npm test -- src/mermaid.test.ts src/viewer.test.ts` -> `4 passed`
- `npm test` -> `12 passed`
- `npm run typecheck` -> pass
- `npm run build` -> pass
- `python -m pytest tests/test_md_web_assets.py -v` -> `7 passed`

## Reviewer Fix Round (Important + Minor)

### Regression RED
- `npm test -- src/main.test.ts src/viewer.test.ts` -> `7 failed`
- Root causes reproduced:
  - fetch missing abort signal + late `viewerError` after dispose/AbortError
  - wikiExists synchronous throw / never-callback causing fail-open or hang
  - lifecycle listeners not removed on dispose and potential stale closure accumulation

### Fixes (GREEN)
- `main.ts`
  - `fetch(bridge.sourceUrl, { signal: abortController.signal })`
  - catch short-circuits when `disposed` or `AbortError`
  - dispose now removes `pagehide`/`beforeunload` listeners and clears `readerMdDispose`
- `viewer.ts`
  - Added `WIKI_EXISTS_TIMEOUT_MS = 2000`
  - Wrapped `bridge.wikiExists(...)` in `try/catch` for fail-closed behavior
  - Added timer-based missing fallback for never-callback path
  - Timer cleared on callback settlement and destroy; late callback remains no-op
- `main.test.ts`
  - Added regressions for pending-fetch dispose late-error suppression
  - Added rejected-fetch AbortError suppression
  - Added explicit listener remove assertions + multi-import listener isolation
  - `afterEach` now actively disposes to avoid residual closures
- `viewer.test.ts`
  - Added fake-timer regressions for sync throw, never-callback timeout, destroy + late callback
- `type-fest`
  - Queried npm engines and installed exact Node18-compatible `type-fest@4.41.0`
  - Removed `src/type-fest.d.ts` ambient shim
  - Updated supply-chain expectation test accordingly

### Reviewer-round verification
- Focused regression: `npm test -- src/main.test.ts src/viewer.test.ts` -> `13 passed`
- Full web: `npm test` -> `19 passed`
- Typecheck: `npm run typecheck` -> pass
- Build: `npm run build` -> pass (notices + manifest refreshed)
- Python assets: `python -m pytest tests/test_md_web_assets.py -v` -> `7 passed`
- Lockfile integrity: `npm ci` -> pass
- Diff hygiene: `git diff --check` -> pass (CRLF warnings only)

## Concerns
- `vite build` still emits non-blocking warning for `qrc:///qtwebchannel/qwebchannel.js` bundling semantics; expected in Qt runtime injection path and does not affect pass/fail.
