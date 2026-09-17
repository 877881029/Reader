# Open / Resize / Cold-Start Snappiness

Date: 2026-09-17  
Status: Approved (user: boot-first launch too slow; Explorer open flashes welcome; open/resize wait or black frame)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

1. After a Windows boot, the first Reader window appears without a long freeze.  
2. Opening a file with Reader when no window exists must **never paint the welcome page**.  
3. Opening a new document or resizing must not stay on a black full-frame surface while Chromium catches up.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.  
Do **not** share one `QWebEngineProfile` across documents.  
Do **not** add a splash exe.

## 2. Causes

| Symptom | Cause |
|---|---|
| First launch after boot is slow | Chromium cold start; warmup waits 400ms; first-tick `register_open_with` may call `claim_protected_defaults()` which **sleeps on the UI thread** up to ~12s |
| Explorer open shows welcome then the file | Hidden create + `open_paths` + `show()` is already the argv path, but the stack starts on welcome and visual tabs are treated as “ready” as soon as the WebEngine widget exists, so the first paint can be welcome or an unpainted native surface |
| Open / resize black flash | Content stack switches before `ready` / `loadFinished`; `_stretch_pane` on every resize rebuilds the Chromium HWND geometry |
| Slow PPTX open | `to_visual()` still runs full `to_html()` for fallback on the single preview worker |

## 3. Decisions

1. **File argv launch:** schedule WebEngine warmup with `delay_ms=0` before `open_paths` / `show()`. Empty launch default delay **50ms** (was 400). Warmup view uses paper `setBackgroundColor`.  
2. **Shell integration:** first-tick timer still writes HKCU associations and the desktop shortcut. `claim_protected_defaults` runs on a **later** timer (~2.5s), not inside that first tick. Registry writes stay off the first paint; Settings UI must not block `show()`.  
3. **Welcome suppression:** `open_paths` while the window is not visible sets a flag so `showEvent` never enables welcome. Content stack stays on tabs (paper loading is OK).  
4. **Leave welcome only when a tab can paint:** widgets with a `ready` signal (PPTX/MD visual) or `QWebEngineView` count as content only after `ready` / `loadFinished`. Plain Qt viewers (code, labels, SVG, images) stay immediate. Failures / fallback still switch away from welcome.  
5. **PPTX visual:** `to_visual()` does **not** extract text. `PptxVisualView` builds fallback HTML lazily in `_show_fallback`. Safe canned HTML if extract fails.  
6. **Resize:** `ChromeTabWidget.resizeEvent` coalesces `_stretch_pane` (~16ms). `showEvent` / `tabInserted` / `LayoutRequest` still stretch immediately.

## 4. Non-goals

- Shared profile / view pool  
- GPU Chromium flags  
- Changing PDF plugin chrome colors  
- Hit-testing / window move

## 5. Testing

- argv file launch: warmup `delay_ms=0`; window not shown before `open_paths`; after `show()`, stack is tabs and `_welcome_allowed` is False  
- Visible welcome + viewer with `ready`: stack stays welcome until `ready`  
- `to_visual` has no extracted slide text in `fallback_html`; fallback helper / view still produces HTML when needed  
- `claim_protected_defaults` is not invoked from the first-tick shell integration function body  
- Caption hit tests stay green  
- Frozen smoke PPTX / MD / IPC still pass  
