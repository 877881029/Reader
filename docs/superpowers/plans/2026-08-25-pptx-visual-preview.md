# PPTX Visual Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace builtin PPTX outline rendering with a fully offline visual slide viewer, while retaining explicit text mode, automatic text fallback, optional Office rendering, deterministic packaging, and leak-free lifecycle behavior.

**Architecture:** `pptx-viewer@0.2.2` is wrapped by a small TypeScript UI using its official `loadPresentation`, `renderSlideToElement`, and `getThumbnails` APIs, preserving slide→layout→master inheritance and calling `presentation.cleanup()` on destruction. Python separates `visual`, `text`, and `office` preview modes; a manually started `PptxVisualView` injects Qt WebChannel support, obtains one fully encoded source URL from a bridge property, enforces an offline scheme allowlist, and changes its own page to the result’s fallback HTML on startup/load/timeout/render failure.

**Tech Stack:** Python 3.12+, PySide6 6.7+ Qt Widgets/WebEngine/WebChannel, python-pptx 1.0+, TypeScript, Vite, Vitest/jsdom, Node.js 18+, npm `pptx-viewer@0.2.2` (MIT; sole runtime dependency `fflate@^0.8.2`), PyInstaller onedir, pytest, pytest-qt.

## Global Constraints

- Each slide is rendered as a real canvas (background, images, text, shapes, tables, basic charts), not a “Slide N + paragraphs” outline.
- Default open path stays fast and offline: no PowerPoint COM, no network.
- UI is a left thumbnail rail, right single-slide stage, previous/next, page number, zoom, and real fit-to-window.
- “Office 高保真” remains optional; default PPTX mode is visual, never Office-first.
- Provide a visible “文本模式” action; automatic visual failure displays the same text fallback and status `内置预览（视觉渲染失败）`.
- Static v1 fidelity includes masters/themes, pictures, text styles, common shapes, tables, and basic charts.
- Missing fonts use browser/library substitution and do not fail the deck.
- A single-slide rendering exception creates a placeholder for that slide and does not trigger whole-deck fallback.
- Do not copy or vendor `astx-jp.vscode-pptx-viewer` proprietary source or plugins.
- Do not require PowerPoint, LibreOffice, internet, animations, video, or macros.
- Pin `pptx-viewer` exactly to `0.2.2`; commit `package-lock.json`; `fflate` remains its only runtime dependency.
- Commit the deterministic bundle under `assets/pptx-viewer/`; source and frozen execution load it with `resource_path`.
- Local WebEngine may use only `file`, `qrc`, `data`, and `blob`; HTTP/HTTPS and unknown schemes are blocked.
- Visual results never use existing HTML/PDF cache entries; text and Office retain separate cache strategies.
- Closing tabs/windows and switching modes destroys the presentation, view, bridge, page, interceptor, and profile.
- Normal Python tests never invoke npm; Windows production build validates Node/npm, runs `npm ci` and `npm run build`, then PyInstaller.
- Every implementation task updates `docs/STATUS.md`, commits, and pushes `origin/main`.

---

## File Structure

- Create `web/pptx-viewer/{package.json,package-lock.json,tsconfig.json,vite.config.ts,index.html,THIRD_PARTY_NOTICES.txt}`.
- Create `web/pptx-viewer/src/{state.ts,state.test.ts,viewer.ts,viewer.test.ts,main.ts,style.css}`.
- Create/refresh `assets/pptx-viewer/index.html` and `assets/pptx-viewer/assets/*`.
- Modify `.gitignore`.
- Create `src/reader/preview/pptx_view.py`.
- Modify `src/reader/{formats/pptx.py,preview/result.py,preview/pipeline.py,preview/cache.py,shell/window.py,smoke.py}`.
- Create `scripts/generate_pptx_visual_fixture.py` and `tests/fixtures/pptx/visual-elements.pptx`.
- Create `tests/{test_pptx_web_assets.py,test_pptx_view.py,test_pptx_webengine.py}`.
- Modify `tests/{test_formats_pptx.py,test_pipeline.py,test_cache.py,test_window.py,test_packaging.py,test_smoke.py}`.
- Modify `pyproject.toml`, `reader.spec`, `scripts/build_windows.ps1`, `scripts/smoke_windows.ps1`, and `docs/STATUS.md`.

---

### Task 1: Deterministic Web Scaffold and Licensing

**Files:** create the web root/config/notice files and `tests/test_pptx_web_assets.py`; modify `.gitignore` and `docs/STATUS.md`.

**Interfaces:** Node.js `>=18`; scripts `test`, `typecheck`, `build`; Vite test environment `jsdom`; output `assets/pptx-viewer/`.

- [ ] **Step 1: Write RED tests**

```python
# tests/test_pptx_web_assets.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "pptx-viewer"

def test_locked_supply_chain_and_node_floor():
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((WEB / "package-lock.json").read_text(encoding="utf-8"))
    assert package["engines"] == {"node": ">=18"}
    assert package["dependencies"] == {"pptx-viewer": "0.2.2"}
    assert package["devDependencies"]["@types/node"].startswith("^")
    assert lock["packages"]["node_modules/pptx-viewer"]["version"] == "0.2.2"
    assert lock["packages"]["node_modules/pptx-viewer"]["dependencies"] == {"fflate": "^0.8.2"}

def test_two_complete_mit_notices_and_ignore():
    notice = (WEB / "THIRD_PARTY_NOTICES.txt").read_text(encoding="utf-8")
    assert notice.count("MIT License") == 2
    assert "Copyright (c) 2025" in notice
    assert "Copyright (c) 2023 Arjun Barrett" in notice
    assert "astx-jp" not in notice
    assert "web/pptx-viewer/node_modules/" in (ROOT / ".gitignore").read_text()

def test_vite_uses_jsdom_and_relative_bundle():
    config = (WEB / "vite.config.ts").read_text(encoding="utf-8")
    assert 'environment: "jsdom"' in config
    assert 'base: "./"' in config
```

- [ ] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_pptx_web_assets.py -v`

Expected: FAIL because the web project does not exist.

- [ ] **Step 3: Add exact scaffold**

```json
// web/pptx-viewer/package.json
{
  "name": "reader-pptx-viewer",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": {"node": ">=18"},
  "scripts": {
    "test": "vitest run",
    "typecheck": "tsc --noEmit",
    "build": "npm run typecheck && vite build"
  },
  "dependencies": {"pptx-viewer": "0.2.2"},
  "devDependencies": {}
}
```

Run exactly once:

```powershell
npm install --prefix web/pptx-viewer --save-exact pptx-viewer@0.2.2
npm install --prefix web/pptx-viewer --save-dev vite typescript vitest jsdom @types/node
```

These two installs create the one committed lockfile; do not run a redundant lock-only install.

```json
// web/pptx-viewer/tsconfig.json
{"compilerOptions":{"target":"ES2022","module":"ESNext","moduleResolution":"Bundler","strict":true,"noUncheckedIndexedAccess":true,"lib":["ES2022","DOM","DOM.Iterable"],"types":["vitest/globals","node"]},"include":["src","vite.config.ts"]}
```

```typescript
// web/pptx-viewer/vite.config.ts
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";
export default defineConfig({
  base: "./",
  test: { environment: "jsdom" },
  build: {
    outDir: fileURLToPath(new URL("../../assets/pptx-viewer", import.meta.url)),
    emptyOutDir: true, assetsDir: "assets", sourcemap: false,
  },
});
```

`index.html` contains only `<main id="app"></main>` and `<script type="module" src="/src/main.ts"></script>`; it contains no `qrc:` script. Append `web/pptx-viewer/node_modules/` to `.gitignore`. Copy the complete two license texts verified from npm: `pptx-viewer 0.2.2` copyright 2025 and `fflate 0.8.2` copyright 2023 Arjun Barrett, each including all MIT paragraphs, into `THIRD_PARTY_NOTICES.txt`.

- [ ] **Step 4: Run GREEN**

Run: `npm --prefix web/pptx-viewer run typecheck && .venv\Scripts\python.exe -m pytest tests/test_pptx_web_assets.py -v`

Expected: typecheck exits 0 and 3 tests pass.

- [ ] **Step 5: Update status and checkpoint**

```bash
git add .gitignore web/pptx-viewer tests/test_pptx_web_assets.py docs/STATUS.md
git commit -m "build: lock the offline PPTX web toolchain"
git push origin main
```

---

### Task 2: Viewer State, Navigation, Zoom, and Fit

**Files:** create `src/state.ts`, `src/state.test.ts`, initial `src/viewer.ts`, `src/style.css`; modify `docs/STATUS.md`.

**Interfaces:** `NavigationState`; `fitScale(stageWidth, stageHeight, slideWidth, slideHeight): number`; required keys Left/Right/PageUp/PageDown/Home/End.

- [ ] **Step 1: Write RED state tests**

```typescript
// web/pptx-viewer/src/state.test.ts
import { expect, it } from "vitest";
import { createNavigationState, fitScale } from "./state";

it("rejects empty decks and clamps navigation", () => {
  expect(() => createNavigationState(0)).toThrow("presentation has no slides");
  const state = createNavigationState(3);
  expect(state.goTo(99)).toBe(2);
  expect(state.previous()).toBe(1);
  expect(state.goTo(-1)).toBe(0);
});

it("fits by ratio and defers safely at zero size", () => {
  expect(fitScale(1000, 500, 1600, 900)).toBeCloseTo(500 / 900);
  expect(fitScale(800, 900, 1600, 900)).toBeCloseTo(0.5);
  expect(fitScale(0, 900, 1600, 900)).toBe(1);
});
```

- [ ] **Step 2: Run RED**

Run: `npm --prefix web/pptx-viewer test -- src/state.test.ts`

Expected: FAIL because `state.ts` is absent.

- [ ] **Step 3: Implement state and DOM controls**

```typescript
// web/pptx-viewer/src/state.ts
export function createNavigationState(count: number) {
  if (!Number.isInteger(count) || count < 1) throw new Error("presentation has no slides");
  const state = {
    current: 0,
    goTo(index: number) {
      state.current = Math.max(0, Math.min(count - 1, Math.trunc(index)));
      return state.current;
    },
    previous() { return state.goTo(state.current - 1); },
    next() { return state.goTo(state.current + 1); },
  };
  return state;
}

export function fitScale(sw: number, sh: number, pw: number, ph: number): number {
  if ([sw, sh, pw, ph].some((value) => value <= 0)) return 1;
  return Math.min(sw / pw, sh / ph);
}
```

```typescript
// web/pptx-viewer/src/viewer.ts
export function buildViewerDom(root: HTMLElement) {
  root.innerHTML = `<div class="viewer-shell"><aside class="thumbnail-rail"></aside>
    <section><div class="toolbar"><button data-action="previous">‹</button>
    <output class="page-number"></output><button data-action="next">›</button>
    <button data-action="zoom-out">−</button><output class="zoom-value"></output>
    <button data-action="zoom-in">＋</button><button data-action="fit">适合窗口</button></div>
    <div class="stage"><div class="slide-host"></div></div></section></div>`;
  return {
    rail: root.querySelector<HTMLElement>(".thumbnail-rail")!,
    stage: root.querySelector<HTMLElement>(".stage")!,
    host: root.querySelector<HTMLElement>(".slide-host")!,
    page: root.querySelector<HTMLOutputElement>(".page-number")!,
    zoom: root.querySelector<HTMLOutputElement>(".zoom-value")!,
  };
}

import { createNavigationState } from "./state";
export function bindControls(root: HTMLElement, state: ReturnType<typeof createNavigationState>,
  render: (index: number) => void, fit: () => void,
  setZoom: (delta: number) => void): () => void {
  const click = (event: Event) => {
    const target = (event.target as Element).closest<HTMLElement>("[data-action],[data-slide]");
    if (!target) return;
    if (target.dataset.slide !== undefined) render(Number(target.dataset.slide));
    if (target.dataset.action === "previous") render(state.current - 1);
    if (target.dataset.action === "next") render(state.current + 1);
    if (target.dataset.action === "fit") fit();
    if (target.dataset.action === "zoom-in") setZoom(0.1);
    if (target.dataset.action === "zoom-out") setZoom(-0.1);
  };
  const key = (event: KeyboardEvent) => {
    const actions: Record<string, () => void> = {
      ArrowLeft: () => render(state.current - 1), PageUp: () => render(state.current - 1),
      ArrowRight: () => render(state.current + 1), PageDown: () => render(state.current + 1),
      Home: () => render(0), End: () => render(Number.MAX_SAFE_INTEGER),
    };
    if (actions[event.key]) { event.preventDefault(); actions[event.key]!(); }
  };
  root.addEventListener("click", click); window.addEventListener("keydown", key);
  return () => { root.removeEventListener("click", click); window.removeEventListener("keydown", key); };
}
```

- [ ] **Step 4: Run GREEN**

Run: `npm --prefix web/pptx-viewer test -- src/state.test.ts`

Expected: 2 passed.

- [ ] **Step 5: Update status and checkpoint**

```bash
git add web/pptx-viewer/src docs/STATUS.md
git commit -m "feat: define PPTX viewer interaction state"
git push origin main
```

---

### Task 3: Official Renderer Integration and Bundle

**Files:** create `scripts/generate_pptx_visual_fixture.py`, real fixture, `src/viewer.test.ts`, `src/main.ts`; finish `src/viewer.ts`; build `assets/pptx-viewer/*`; modify `docs/STATUS.md`.

**Interfaces:** official 0.2.2 APIs `loadPresentation(File|ArrayBuffer|Uint8Array|string) -> Promise<LoadedPresentation>`, `renderSlideToElement(presentation,index,host,{width,height})`, `getThumbnails(presentation,200)`, `LoadedPresentation.cleanup()`.

- [ ] **Step 1: Generate a real four-slide fixture and write RED renderer tests**

```python
# scripts/generate_pptx_visual_fixture.py
from io import BytesIO
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

out = Path(__file__).resolve().parents[1] / "tests/fixtures/pptx/visual-elements.pptx"
prs = Presentation()
s = prs.slides.add_slide(prs.slide_layouts[1]); s.background.fill.solid()
s.background.fill.fore_color.rgb = RGBColor(20, 48, 90); s.shapes.title.text = "Inherited title"
image = BytesIO(); Image.new("RGB", (320, 180), (37, 99, 235)).save(image, "PNG"); image.seek(0)
s.shapes.add_picture(image, Inches(7), Inches(2), width=Inches(4))
s = prs.slides.add_slide(prs.slide_layouts[6])
t = s.shapes.add_table(3, 3, Inches(1), Inches(1), Inches(10), Inches(3)).table
for r, row in enumerate((("Metric","Q1","Q2"),("A","10","14"),("B","8","13"))):
    for c, value in enumerate(row): t.cell(r, c).text = value
s = prs.slides.add_slide(prs.slide_layouts[6]); data = ChartData()
data.categories = ["North","South","West"]; data.add_series("Revenue", (12,18,15))
s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1), Inches(10), Inches(5), data)
s = prs.slides.add_slide(prs.slide_layouts[6]); box = s.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2))
box.text = "Missing font continues"; box.text_frame.paragraphs[0].runs[0].font.name = "ReaderMissingFontZZ"
out.parent.mkdir(parents=True, exist_ok=True); prs.save(out)
```

```typescript
// web/pptx-viewer/src/viewer.test.ts
import { readFile } from "node:fs/promises";
import { afterEach, expect, it, vi } from "vitest";
import { loadPresentation, renderSlideToElement } from "pptx-viewer";
import { startViewer } from "./viewer";

const fixture = new URL("../../../tests/fixtures/pptx/visual-elements.pptx", import.meta.url);
afterEach(() => { document.body.replaceChildren(); vi.restoreAllMocks(); });

it("loads inheritance, picture, table, chart, missing font, and cleanup", async () => {
  const bytes = await readFile(fixture);
  const presentation = await loadPresentation(new Uint8Array(bytes));
  const cleanup = vi.spyOn(presentation, "cleanup");
  expect(presentation.slides).toHaveLength(4);
  expect(presentation.slideLayouts.size).toBeGreaterThan(0);
  expect(presentation.slideMasters.size).toBeGreaterThan(0);
  expect(presentation.slides[0]!.elements.some(e => e.type === "image")).toBe(true);
  expect(presentation.slides[1]!.elements.some(e => e.type === "table")).toBe(true);
  expect(presentation.slides[2]!.elements.some(e => e.type === "chart")).toBe(true);
  const host = document.createElement("div");
  Object.defineProperty(host, "getBoundingClientRect", {value: () => ({width:960,height:540})});
  document.body.append(host);
  renderSlideToElement(presentation, 0, host, {width: 960, height: 540});
  expect(host.querySelector("svg image")).not.toBeNull();
  renderSlideToElement(presentation, 1, host, {width: 960, height: 540});
  expect(host.querySelector("foreignObject table")).not.toBeNull();
  renderSlideToElement(presentation, 2, host, {width: 960, height: 540});
  expect(host.querySelectorAll("svg rect,svg path").length).toBeGreaterThan(3);
  renderSlideToElement(presentation, 3, host, {width: 960, height: 540});
  expect(host.querySelector("svg")).not.toBeNull();
  presentation.cleanup();
  expect(cleanup).toHaveBeenCalledOnce();
});
```

- [ ] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe scripts/generate_pptx_visual_fixture.py && npm --prefix web/pptx-viewer test -- src/viewer.test.ts`

Expected: fixture generation succeeds; Vitest FAIL because `startViewer` does not yet use the official presentation lifecycle.

- [ ] **Step 3: Implement official renderer wrapper**

```typescript
// core of web/pptx-viewer/src/viewer.ts
import { getThumbnails, loadPresentation, renderSlideToElement, type LoadedPresentation } from "pptx-viewer";
import { createNavigationState, fitScale } from "./state";

export interface ViewerBridge {
  viewerReady(count: number): void;
  viewerError(message: string): void;
  slideChanged(index: number): void;
}

export async function startViewer(root: HTMLElement, sourceUrl: string, bridge: ViewerBridge,
  options: {testFailSlide?: number} = {}) {
  let presentation: LoadedPresentation | undefined;
  let disposed = false;
  try {
    presentation = await loadPresentation(sourceUrl);
    if (presentation.slides.length === 0) throw new Error("presentation has no slides");
    const state = createNavigationState(presentation.slides.length);
    const {rail, stage, host, page, zoom} = buildViewerDom(root);
    getThumbnails(presentation, 200).forEach((svg, index) => {
      const button = document.createElement("button");
      button.className = "thumbnail"; button.dataset.slide = String(index);
      button.append(svg); rail.append(button);
    });
    const render = (index: number) => {
      state.goTo(index);
      try {
        if (options.testFailSlide === state.current) throw new Error("injected slide failure");
        renderSlideToElement(presentation!, state.current, host, {width: 1280});
      } catch (error) {
        host.innerHTML = `<div class="slide-error">第 ${state.current + 1} 页无法渲染</div>`;
        host.dataset.slideError = error instanceof Error ? error.message : String(error);
      }
      page.value = `${state.current + 1} / ${presentation!.slides.length}`;
      bridge.slideChanged(state.current);
    };
    let manualZoom = 1;
    const setZoom = (delta: number) => {
      manualZoom = Math.max(0.25, Math.min(4, manualZoom + delta));
      host.style.transform = `scale(${manualZoom})`;
      zoom.value = `${Math.round(manualZoom * 100)}%`;
    };
    const fit = () => {
      const scale = fitScale(stage.clientWidth, stage.clientHeight,
        presentation!.slideSize.width, presentation!.slideSize.height);
      manualZoom = scale;
      host.style.transform = `scale(${scale})`; zoom.value = `${Math.round(scale * 100)}%`;
    };
    const observer = new ResizeObserver(() => fit());
    observer.observe(stage);
    const unbindControls = bindControls(root, state, render, fit, setZoom);
    render(0); fit(); bridge.viewerReady(presentation.slides.length);
    return {goTo: render, fit, destroy() {
      if (disposed) return; disposed = true;
      observer.disconnect(); unbindControls(); presentation!.cleanup(); root.replaceChildren();
    }};
  } catch (error) {
    presentation?.cleanup();
    bridge.viewerError(error instanceof Error ? error.message : String(error));
    throw error;
  }
}
```

In jsdom, define `stage.clientWidth=1000`, `stage.clientHeight=500`, and a fake `ResizeObserver` that captures its callback. Derive the expected percentage from the loaded fixture rather than assuming a 16:9 deck:

```typescript
const expectedFit = Math.round(
  fitScale(1000, 500, presentation.slideSize.width, presentation.slideSize.height) * 100,
);
expect(zoom.value).toBe(`${expectedFit}%`);
zoomIn.click();
expect(zoom.value).toBe(`${Math.min(400, expectedFit + 10)}%`);
```

Also assert resizing invokes the callback, 50 repeated zoom-ins clamp at `400%`, and repeated zoom-outs clamp at `25%`. Spy on `renderSlideToElement`, throw only at index 1, then prove index 2 still renders and `viewerError` has zero calls.

```typescript
// web/pptx-viewer/src/main.ts
import "./style.css";
import { startViewer, type ViewerBridge } from "./viewer";
declare global {
  interface Window {
    qt?: { webChannelTransport: unknown };
    QWebChannel?: new (transport: unknown,
      callback: (channel: {objects: {bridge: ViewerBridge & {sourceUrl: string; testFailSlide: number}}}) => void) => object;
  }
}
const root = document.querySelector<HTMLElement>("#app");
if (!root) throw new Error("viewer mount #app is missing");
if (!window.qt?.webChannelTransport || !window.QWebChannel) {
  root.textContent = "Reader bridge unavailable";
} else {
  new window.QWebChannel(window.qt.webChannelTransport, ({objects}) => {
    void startViewer(root, objects.bridge.sourceUrl, objects.bridge,
      {testFailSlide: objects.bridge.testFailSlide})
      .catch(error => objects.bridge.viewerError(error instanceof Error ? error.message : String(error)));
  });
}
```

```css
/* web/pptx-viewer/src/style.css */
*{box-sizing:border-box}html,body,#app{width:100%;height:100%;margin:0;overflow:hidden}
body{font-family:"Segoe UI",sans-serif;background:#111827;color:#f8fafc}
.viewer-shell{display:grid;grid-template-columns:220px minmax(0,1fr);height:100%}
.thumbnail-rail{overflow:auto;padding:12px;background:#18181b;border-right:1px solid #3f3f46}
.thumbnail{display:block;width:100%;margin-bottom:12px;padding:4px;background:#27272a;border:1px solid #52525b}
.thumbnail.selected{border:2px solid #60a5fa}.thumbnail svg{display:block;width:100%;height:auto}
.viewer-shell>section{display:grid;grid-template-rows:auto minmax(0,1fr);min-width:0}
.toolbar{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:8px;padding:8px;background:#27272a}
.toolbar button{min-width:34px;padding:6px 10px}.page-number,.zoom-value{min-width:60px;text-align:center}
.stage{display:grid;place-items:center;overflow:auto;min-width:0;min-height:0;padding:24px}
.slide-host{width:1280px;transform-origin:center}.slide-host>svg{display:block;width:100%;height:auto;background:white}
.slide-error{display:grid;place-items:center;aspect-ratio:16/9;background:#3f3f46}
```

- [ ] **Step 4: Run GREEN and build**

Run: `npm --prefix web/pptx-viewer test && npm --prefix web/pptx-viewer run build`

Expected: real renderer and state tests pass; bundle uses relative assets; `presentation.cleanup()` tests pass.

- [ ] **Step 5: Update status and checkpoint**

```bash
git add scripts/generate_pptx_visual_fixture.py tests/fixtures web/pptx-viewer assets/pptx-viewer docs/STATUS.md
git commit -m "feat: render inherited PPTX content with the official API"
git push origin main
```

---

### Task 4: Visual/Text Result Modes and Cache Contract

**Files:** modify result, PPTX format, pipeline, cache, worker section of window, four existing test files, and status.

**Interfaces:** `PreviewMode = Literal["builtin","visual","text","office"]`; PPTX default resolves to `visual`; `to_visual()` returns `kind="pptx"` plus `fallback_html`; `text` returns HTML status `内置预览（文本模式）`.

- [ ] **Step 1: Write RED contracts and migrations**

```python
def test_pptx_falls_back_when_office_missing(tmp_path):
    from pptx import Presentation
    p = tmp_path / "a.pptx"
    prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "pptx-fallback"; prs.save(p)
    office = FakeOffice(available=False)
    result = preview(p, office=office, mode="office")
    assert office.available_calls == [".pptx"]
    assert office.calls == []
    assert result.kind == "pptx"
    assert result.fallback_html is not None
    assert "pptx-fallback" in result.fallback_html

def test_explicit_text_mode_returns_cacheable_html(tmp_path):
    from pptx import Presentation
    path = tmp_path / "text.pptx"
    prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "manual-text"; prs.save(path)
    result = preview(path, mode="text")
    assert result.kind == "html"
    assert result.status_label == "内置预览（文本模式）"
    assert "manual-text" in result.html
```

Migrate exactly four existing fake-PDF tests away from builtin `.pptx`: `test_switch_back_preserves_builtin_pdf_and_cleans_both_artifacts` uses `deck.docx`; `test_pdf_is_pinned_until_tab_closes` uses `deck.docx`; `test_window_close_cleans_loaded_pdf_pin` uses `loaded.docx`; `test_viewer_reentrancy_close_discards_widget_and_artifact` uses `close-during-viewer.docx`. Tests specifically exercising Office PPTX keep `.pptx` and `mode="office"`.

- [ ] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_formats_pptx.py tests/test_pipeline.py tests/test_cache.py tests/test_window.py -k "pptx or pdf_is_pinned or loaded_pdf" -v`

Expected: existing Office-missing assertion fails with HTML, and explicit text/visual modes are unknown.

- [ ] **Step 3: Implement without truncating worker control flow**

```python
# result.py
PreviewKind = Literal["html", "pdf", "pptx", "error"]
# add fallback_html: str | None = None

# pipeline.py
PreviewMode = Literal["builtin", "visual", "text", "office"]
if mode == "visual" and suffix != ".pptx":
    raise ValueError("visual mode supports only .pptx")
if suffix == ".pptx" and mode in {"builtin", "visual"}:
    return fmt_pptx.to_visual(path)
if suffix == ".pptx" and mode == "text":
    text = fmt_pptx.to_html(path)
    return replace(text, status_label="内置预览（文本模式）")
# after these PPTX branches, execute the existing Office branch and _BUILTIN dispatch unchanged
```

`to_visual` catches text extraction failure and stores escaped clear fallback HTML (`演示文稿已加密或损坏：...`) so the visual renderer can still attempt to open; manual text mode propagates its parse error to the existing worker error UI.

In `_PreviewWorker.run`, replace only cache selection:

```python
strategy = "visual" if self.path.suffix.lower() == ".pptx" and self.mode in {"builtin","visual"} else self.mode
result: PreviewResult | None = None
cache = None
if strategy != "visual":
    try:
        cache = self.cache_factory()
        result = cache.get(self.path, strategy)
    except Exception:
        cache = None
if result is None:
    result = self.preview_fn(self.path, office=self.office, mode=self.mode)
    cacheable = not (result.kind == "html" and result.asset_dir is not None)
    if cache is not None and cacheable:
        try: cache.put(self.path, strategy, result)
        except Exception: pass
output = _pin_pdf(result)
# the surrounding existing except emits (document_id, None, exc);
# the success path emits (document_id, output, None).
```

Add a full test asserting visual performs neither `get` nor `put`, text uses `("get", path, "text")` then `("put", path, "text")`, and `PreviewCache.put(...kind="pptx")` raises `ValueError`. Do not alter `_pin_pdf`.

Window submission is exact: `_start_preview` chooses `initial_mode = "visual" if path.suffix.lower() == ".pptx" else "builtin"` and stores/submits that mode; DOCX/XLSX/MD remain builtin. `_Document` gains `builtin_mode: Literal["builtin","visual","text"] = "builtin"`; successful non-Office results set both `mode` and `builtin_mode` to the requested mode. Office switching changes only `mode="office"`; switching back calls `_restore_builtin(document.builtin_mode)`, never hard-codes `"builtin"`.

- [ ] **Step 4: Run GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_formats_pptx.py tests/test_pipeline.py tests/test_cache.py tests/test_window.py -v`

Expected: all pass, including migrated PDF pinning tests.

- [ ] **Step 5: Update status and checkpoint**

```bash
git add src/reader tests/test_formats_pptx.py tests/test_pipeline.py tests/test_cache.py tests/test_window.py docs/STATUS.md
git commit -m "feat: separate PPTX visual and text preview strategies"
git push origin main
```

---

### Task 5: Secure Explicit-Start WebEngine View

**Files:** create `pptx_view.py`, `test_pptx_view.py`; modify status.

**Interfaces:** constructor has `parent: QWidget | None` and does not load; `start()` loads once; bridge constant property `sourceUrl`; 15-second timeout; thread-safe `blocked_urls()`.

- [ ] **Step 1: Write RED tests**

```python
def test_constructor_does_not_load_and_source_is_once_encoded(qtbot, tmp_path):
    source = tmp_path / "季度 #1 100%.pptx"; source.write_bytes(b"x")
    result = PreviewResult(html="", fallback_html="<p>fallback</p>",
                           status_label="内置预览", kind="pptx")
    view = PptxVisualView(result, source)
    qtbot.addWidget(view)
    assert view.started is False
    assert view.bridge.sourceUrl == QUrl.fromLocalFile(str(source.resolve())).toString(
        QUrl.ComponentFormattingOption.FullyEncoded)
    assert "%2523" not in view.bridge.sourceUrl

def test_start_failure_and_timeout_each_fallback_once(qtbot, tmp_path):
    source = tmp_path / "broken.pptx"; source.write_bytes(b"x")
    result = PreviewResult(html="", fallback_html="<p>fallback</p>",
                           status_label="内置预览", kind="pptx")
    view = PptxVisualView(result, source)
    qtbot.addWidget(view)
    failures = []; view.render_failed.connect(failures.append)
    view.start(); view._load_finished(False); view._startup_timeout()
    assert failures == ["viewer bundle failed to load"]
    assert view.is_fallback
```

- [ ] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_pptx_view.py -v`

Expected: import FAIL because the view does not exist.

- [ ] **Step 3: Implement explicit start, injection, policy, and safe teardown**

```python
import PySide6.QtWebChannel  # registers :/qtwebchannel/qwebchannel.js
from PySide6.QtCore import QFile, QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript, QWebEngineUrlRequestInterceptor
from PySide6.QtWidgets import QWidget

class OfflineRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent); self._lock = threading.Lock(); self._blocked: list[str] = []
    def interceptRequest(self, info):
        if info.requestUrl().scheme().lower() not in {"file","qrc","data","blob"}:
            with self._lock: self._blocked.append(info.requestUrl().toString())
            info.block(True)
    def blocked_urls(self) -> tuple[str, ...]:
        with self._lock: return tuple(self._blocked)

class PptxBridge(QObject):
    ready = Signal(int)
    failed = Signal(str)
    changed = Signal(int)
    def __init__(self, source: Path, test_fail_slide: int | None = None, parent=None):
        super().__init__(parent)
        self._test_fail_slide = test_fail_slide
        self._source_url = QUrl.fromLocalFile(str(source.resolve())).toString(
            QUrl.ComponentFormattingOption.FullyEncoded)
    @Property(str, constant=True)
    def sourceUrl(self) -> str: return self._source_url
    @Property(int, constant=True)
    def testFailSlide(self) -> int: return self._test_fail_slide if self._test_fail_slide is not None else -1
    @Slot(int)
    def viewerReady(self, count): self.ready.emit(count)
    @Slot(str)
    def viewerError(self, message): self.failed.emit(message)
    @Slot(int)
    def slideChanged(self, index): self.changed.emit(index)
```

`PptxVisualView.__init__(..., parent: QWidget | None = None, test_fail_slide: int | None = None)` creates profile/interceptor/page/channel/bridge, replaces and deletes the automatically created default page, configures local-file true/remote false, and stores the test-only integer on the bridge; it does not call `load` and never adds it to the source URL. Open `QFile(":/qtwebchannel/qwebchannel.js")`; if `open(QIODevice.ReadOnly)` fails or bytes are empty, queue `_show_fallback("Qt WebChannel script unavailable")` and leave `started=False`. Otherwise inject the decoded source as a `QWebEngineScript` at `DocumentCreation`, `MainWorld`, all frames false. `start()` starts a single-shot `QTimer(15_000)` and loads only `resource_path("assets","pptx-viewer","index.html")` without source query. `_load_finished(False)`, timer expiry, bundle read failure, and bridge error call one idempotent `_show_fallback`.

Teardown order is exact: stop timer/view; `profile.setUrlRequestInterceptor(None)`; disconnect load signal; `page.setWebChannel(None)`; deregister bridge; replace the view’s page with a new view-owned inert page; clear Python references; `deleteLater` old page, bridge, channel, interceptor, then profile. Repeated `shutdown()` is a no-op.

- [ ] **Step 4: Run GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_pptx_view.py -v`

Expected: constructor/start, failed-load, timeout, source encoding, allowlist snapshot, bridge relay, and teardown tests pass.

- [ ] **Step 5: Update status and checkpoint**

```bash
git add src/reader/preview/pptx_view.py tests/test_pptx_view.py docs/STATUS.md
git commit -m "feat: add a race-free offline PPTX WebEngine host"
git push origin main
```

---

### Task 6: Window Integration, Manual Text Mode, and Lifecycle

**Files:** modify window and full window tests; modify status.

**Interfaces:** actions `actionTextPreview` and `actionVisualPreview`; one `_install_document_content(...)` path binds events then calls `start()`; one `_dispose_widget`.

- [ ] **Step 1: Write complete RED scenarios**

Define `FakeVisual(QWidget)` with `ready = Signal(int)`, `render_failed = Signal(str)`, integer `start_calls/shutdown_calls`, and concrete `start()`/`shutdown()` increments. Each test constructs `MainWindow` with existing `FakeCache`, `FakeOfficeAvailability`, and a viewer factory returning a new `FakeVisual` for `kind=="pptx"`; assert worker completion, Office switch, switch-back, stale error, close tab/window, manual text, and fresh visual behavior independently.

```python
def test_office_failure_preserves_current_visual_fallback(qtbot, tmp_path):
    path = tmp_path / "deck.pptx"; path.write_bytes(b"x")
    visual = FakeVisual()
    result = PreviewResult(
        html="", fallback_html="<p>fallback</p>",
        status_label="内置预览", kind="pptx",
    )
    def preview_fn(_path, office=None, mode="visual"):
        if mode == "office": raise RuntimeError("COM failed")
        return result
    window = MainWindow(
        preview_fn=preview_fn, cache_factory=FakeCache,
        viewer_factory=lambda _result, _path: visual,
        office=FakeOfficeAvailability(True),
    )
    qtbot.addWidget(window); window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    visual.render_failed.emit("parse")
    current = visual
    qtbot.waitUntil(window.actionOfficePreview.isEnabled)
    window.switch_current_tab_to_office()
    qtbot.waitUntil(lambda: window._executor.active_count() == 0)
    page = window._tabs.widget(0); layout = page.layout()
    assert layout is not None and layout.itemAt(0).widget() is current
    assert window.status_text() == "内置预览（Office 导出失败）"
    assert next(iter(window._documents.values())).mode == "visual"
    assert next(iter(window._documents.values())).builtin_mode == "visual"
```

- [ ] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_window.py -k "visual or text_mode or office_failure_preserves" -v`

Expected: FAIL because actions and unified install/start/dispose path do not exist.

- [ ] **Step 3: Implement one guarded installation path**

```python
def _dispose_widget(widget: QWidget) -> None:
    shutdown = getattr(widget, "shutdown", None)
    if callable(shutdown): shutdown()
    widget.setParent(None)
    widget.deleteLater()

def _install_document_content(self, document_id, document, content, generation):
    if self._documents.get(document_id) is not document or document.generation != generation:
        _dispose_widget(content); return False
    layout = document.page.layout()
    if layout is None: _dispose_widget(content); return False
    while layout.count():
        old = layout.takeAt(0).widget()
        if old is not None: _dispose_widget(old)
    layout.addWidget(content)
    self._bind_visual_events(document_id, generation, content)
    start = getattr(content, "start", None)
    if callable(start): start()
    return True
```

Both worker completion and Office→builtin/visual restoration use this method. Every viewer-factory exception, stale completion, failed install, tab close, window close, Office replacement, and error-result branch uses `_dispose_widget`. Event handlers require matching document identity, generation, mode `visual`, and `layout.indexOf(widget)>=0`.

```python
def _bind_visual_events(self, document_id: str, generation: int, widget: QWidget) -> None:
    failed = getattr(widget, "render_failed", None)
    if failed is not None:
        failed.connect(lambda message: self._visual_render_failed(
            document_id, generation, widget, message))
    ready = getattr(widget, "ready", None)
    if ready is not None:
        ready.connect(lambda count: self._visual_ready(
            document_id, generation, widget, count))

def _visual_ready(self, document_id, generation, widget, count):
    document = self._documents.get(document_id)
    layout = document.page.layout() if document is not None else None
    if (document is None or self._closing or document.generation != generation
        or document.mode != "visual" or layout is None or layout.indexOf(widget) < 0):
        return
    append_visual_ready(str(document.path), count)
```

`actionTextPreview` is enabled for PPTX unless mode is text and calls `_restart_preview(id,"text")`; `actionVisualPreview` is enabled unless mode is visual and calls `_restart_preview(id,"visual")`. Automatic fallback keeps mode/builtin_mode visual and result kind pptx; manual text mode sets both to text. Before Office submission save `builtin_mode`; Office failure restores `mode=document.builtin_mode`, preserves the current widget, and sets status exactly `内置预览（Office 导出失败）` even when that widget already shows automatic text fallback.

- [ ] **Step 4: Run GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_window.py -v`

Expected: all existing late-result, Office failure, pinning, close/reentrancy, plus new visual/text lifecycle tests pass.

- [ ] **Step 5: Update status and checkpoint**

```bash
git add src/reader/shell/window.py tests/test_window.py docs/STATUS.md
git commit -m "feat: integrate PPTX visual and text modes safely"
git push origin main
```

---

### Task 7: Real QWebEngine Fidelity and Offline Tests

**Files:** create `test_pptx_webengine.py`; modify marker config/status.

**Interfaces:** unique JavaScript callback keys via monotonic counter; skip when QtWebEngineProcess or committed bundle absent.

- [ ] **Step 1: Write RED integration tests**

```python
_js_ids = itertools.count()
def run_js(qtbot, view, script):
    key = f"js-{next(_js_ids)}"; done = []
    view.page().runJavaScript(script, lambda value: done.append(value))
    qtbot.waitUntil(lambda: bool(done), timeout=10_000)
    return done[0]

from PySide6.QtCore import QLibraryInfo
qt_root = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.LibraryExecutablesPath))
WEBENGINE_MISSING = (
    not resource_path("assets","pptx-viewer","index.html").is_file()
    or not (qt_root / "QtWebEngineProcess.exe").is_file()
)
pytestmark = [
    pytest.mark.webengine,
    pytest.mark.skipif(WEBENGINE_MISSING, reason="committed WebEngine bundle unavailable"),
]
```

Add a session probe that constructs a temporary `QWebEngineView`, loads `data:text/html,ok`, waits at most five seconds for `loadFinished(True)`, and skips with `pytest.skip("QtWebEngine process cannot start")` on failure. The real test starts explicitly, waits for ready count 4, asserts four thumbnails and first selection; slide 1 has `svg image`; slide 2 has `foreignObject table`; slide 3 has multiple `path/rect` and presentation data says chart; all six keys and thumbnail click update bridge index; fit scale changes after stage resize; missing-font slide renders an SVG; inserted `https://example.invalid/tracker.png` appears exactly in `interceptor.blocked_urls()` and never loads. A separate test constructs `PptxVisualView(..., test_fail_slide=1)`, asserts `.slide-error`, then navigates successfully and asserts no whole-deck fallback.

- [ ] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_pptx_webengine.py -v`

Expected: tests are collected (marker registered) and FAIL because bundle/view integration does not yet expose all probes; only environments lacking WebEngine resources skip.

- [ ] **Step 3: Register marker and complete probes**

Add `"webengine: requires Qt WebEngine process and committed viewer bundle"` to `pyproject.toml`. Bridge exposes constant `testFailSlide` only when constructor receives the test argument; `main.ts` passes it into `startViewer(..., {testFailSlide})`; production construction returns `-1`, and no test flag enters any URL. Expose DOM `data-element-types` from parsed presentation for stable chart assertion.

- [ ] **Step 4: Run GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/test_pptx_webengine.py -v`

Expected: picture/table/chart/font/nav/thumbnail/fit/offline/slide-local tests pass, or explicit environment skip.

- [ ] **Step 5: Update status and checkpoint**

```bash
git add tests/test_pptx_webengine.py pyproject.toml web/pptx-viewer assets/pptx-viewer docs/STATUS.md
git commit -m "test: verify real PPTX fidelity and offline isolation"
git push origin main
```

---

### Task 8: Frozen Resources and Native Fail-Fast Build

**Files:** modify spec/build script/packaging tests/status.

- [ ] **Step 1: Write RED packaging tests**

Assert spec collects `assets/pptx-viewer` and `collect_submodules('PySide6.QtWebChannel')`; script contains `Get-Command node`, `Get-Command npm.cmd`, Node major >=18 check, `cmd.exe /d /s /c`, `npm ci`, `npm run build`, `$process.ExitCode`, and orders both npm commands before PyInstaller. Assert ordinary pytest configuration contains no npm hook and committed index/hash manifest exist.

- [ ] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_packaging.py tests/test_pptx_web_assets.py -v`

Expected: FAIL on missing WebChannel data and native command checks.

- [ ] **Step 3: Implement exact native process helper**

```powershell
$node = Get-Command node.exe -ErrorAction Stop
$npm = Get-Command npm.cmd -ErrorAction Stop
$major = [int]((& $node.Source --version).TrimStart("v").Split(".")[0])
if ($LASTEXITCODE -ne 0 -or $major -lt 18) { throw "Node.js 18+ is required" }
function Invoke-Npm([string]$Arguments) {
    $process = Start-Process -FilePath $env:ComSpec `
        -ArgumentList @("/d", "/s", "/c", "`"$($npm.Source)`" $Arguments") `
        -WorkingDirectory $Root -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) { throw "npm $Arguments failed (exit $($process.ExitCode))" }
}
Invoke-Npm "ci --prefix web\pptx-viewer"
Invoke-Npm "run build --prefix web\pptx-viewer"
```

Generate and verify the manifest before PyInstaller:

```powershell
$assetFiles = Get-ChildItem assets\pptx-viewer -File -Recurse |
    Where-Object Name -ne "manifest.sha256" | Sort-Object FullName
$lines = foreach ($file in $assetFiles) {
    $relative = [IO.Path]::GetRelativePath((Resolve-Path "assets\pptx-viewer"), $file.FullName).Replace("\","/")
    "$((Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower())  $relative"
}
$lines | Set-Content assets\pptx-viewer\manifest.sha256 -Encoding ascii
foreach ($line in Get-Content assets\pptx-viewer\manifest.sha256) {
    $hash, $relative = $line -split "  ", 2
    $actual = (Get-FileHash (Join-Path "assets\pptx-viewer" $relative) -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $hash) { throw "PPTX bundle hash mismatch: $relative" }
}
```

Spec adds bundle datas and QtWebChannel hidden modules.

- [ ] **Step 4: Run GREEN/build**

Run: `.venv\Scripts\python.exe -m pytest tests/test_packaging.py tests/test_pptx_web_assets.py -v`

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_windows.ps1`

Expected: tests pass; native npm failures propagate; frozen bundle/WebChannel exist.

- [ ] **Step 5: Update status and checkpoint**

```bash
git add reader.spec scripts/build_windows.ps1 tests/test_packaging.py tests/test_pptx_web_assets.py assets/pptx-viewer docs/STATUS.md
git commit -m "build: package and verify the offline PPTX runtime"
git push origin main
```

---

### Task 9: Separate Frozen Visual Smoke and Final Regression

**Files:** modify smoke module/script/tests/status and refresh build/shortcut.

- [ ] **Step 1: Write RED durable telemetry test**

```python
def test_visual_ready_flushes_and_fsyncs(monkeypatch, tmp_path, mocker):
    log = tmp_path / "visual.jsonl"
    fsync = mocker.patch("reader.smoke.os.fsync")
    monkeypatch.setenv("READER_SMOKE_VISUAL_LOG", str(log))
    assert append_visual_ready("C:/deck.pptx", 4)
    assert json.loads(log.read_text(encoding="utf-8"))["slides"] == 4
    fsync.assert_called_once()

def test_late_visual_ready_after_close_is_not_logged(qtbot, tmp_path, monkeypatch):
    path = tmp_path / "late-ready.pptx"; path.write_bytes(b"x")
    visual = FakeVisual()
    result = PreviewResult(html="", fallback_html="<p>fallback</p>",
                           status_label="内置预览", kind="pptx")
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: result,
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
    )
    qtbot.addWidget(window); window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    calls = []
    monkeypatch.setattr("reader.shell.window.append_visual_ready",
                        lambda source, count: calls.append((source, count)))
    window.close_tab(0)
    visual.ready.emit(4)
    qtbot.wait(10)
    assert calls == []
```

- [ ] **Step 2: Run RED**

Run: `.venv\Scripts\python.exe -m pytest tests/test_smoke.py tests/test_window.py::test_late_visual_ready_after_close_is_not_logged -v`

Expected: FAIL because visual telemetry and fsync do not exist.

- [ ] **Step 3: Implement telemetry and two non-overlapping lifecycles**

```python
def append_visual_ready(path: str, slides: int) -> bool:
    target = os.environ.get("READER_SMOKE_VISUAL_LOG")
    if not target: return False
    payload = {"path": path, "kind": "pptx", "slides": slides, "status": "ready"}
    with Path(target).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return True
```

In PowerShell use `$visualProcess` and `$ipcPrimary` as distinct variables. Phase A starts only `$visualProcess` with a dedicated 60-second visual deadline, waits for one four-slide record, stops its entire Reader/QtWebEngine process tree, waits for exit, and removes its profile/namespace before Phase B. Phase B then starts `$ipcPrimary` and runs the unchanged existing two-batch forwarding assertions. Never assign the visual process to `$primary`; never overlap phases.

- [ ] **Step 4: Full verification, build, smoke, hash, shortcut**

Run:

```powershell
npm --prefix web/pptx-viewer test
npm --prefix web/pptx-viewer run build
.venv\Scripts\python.exe -m pytest -v
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_windows.ps1 -ReaderExe dist\Reader\Reader.exe
Get-FileHash dist\Reader\Reader.exe -Algorithm SHA256
```

Expected: all tests pass; phase A visual process fully exits before phase B; IPC smoke passes; hash is recorded in `docs/STATUS.md`. Only then update desktop `Reader.lnk` target, working directory, and icon to the verified executable.

- [ ] **Step 5: Final status and checkpoint**

Record dependency/version, bundle hash, EXE hash, test counts, skips, smoke phases, shortcut refresh, completed feature, and next user-acceptance step.

```bash
git add src/reader/smoke.py scripts/smoke_windows.ps1 tests/test_smoke.py tests/test_window.py assets/pptx-viewer docs/STATUS.md
git commit -m "test: certify visual PPTX preview in frozen Reader"
git push origin main
git status --short
```

---

## Self-Review Record

- [x] **Review fixes:** Node types/floor, jsdom, exact two-license notice, ignore rule, official 0.2.2 APIs, master/layout inheritance, cleanup, ratio fit, visual/text strategies, existing test migrations, complete worker-flow preservation, explicit start, injected WebChannel, single URL encoding, timeout fallback, thread-safe interceptor records, teardown ownership, unified install/dispose, manual text entry, stale event guards, real picture/table/chart/font tests, WebEngine skips, native npm exit propagation, separate smoke lifecycles, fsync, hashes, shortcut, and status are assigned to Tasks 1–9.
- [x] **Second review fixes:** Vite imports `defineConfig` from `vitest/config`; zero-size fit defers at scale 1 and `ResizeObserver` recomputes; zoom buttons are wired/clamped/tested; worker initializes `result=None`; all four fake-PDF tests migrate; `builtin_mode` preserves visual/text across Office; Office failure status remains `内置预览（Office 导出失败）`; tests inspect the layout widget directly; guarded `ready` telemetry ignores closed/stale views; bridge signals/imports/qrc failure are explicit; test slide injection is a constructor/bridge property rather than a URL; WebEngine executable/startability skip, durable manifest generation, complete `main.ts`, complete CSS, and HTTPS exact-string assertions are specified.
- [x] **Specification coverage:** default visual/no COM, thumbnails/single-slide/nav/zoom/fit, optional Office, manual and automatic text fallback, encrypted/corrupt messaging, missing-font continuation, slide-local placeholder, no network, no visual cache, source/frozen resources, and leak-free destruction all have code and tests.
- [x] **Placeholder scan:** no deferred marker, cross-task shorthand, undefined helper ellipsis, or prose-only code mutation remains; each task has RED/GREEN commands and expected outcomes.
- [x] **Type consistency:** official `LoadedPresentation.cleanup`, `PreviewMode`, `PreviewKind`, `fallback_html`, bridge `sourceUrl/viewerReady/viewerError/slideChanged`, view `start/shutdown/ready/render_failed`, and window guards use the same names throughout.
- [x] **Race/ownership review:** constructors do not load; bindings precede `start`; source is encoded exactly once; every failure converges on one fallback; interceptor emits no cross-thread Qt signal; page/channel/interceptor references are detached before profile deletion.
