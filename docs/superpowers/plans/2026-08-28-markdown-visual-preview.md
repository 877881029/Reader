# Markdown Visual Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Reader's basic Markdown HTML page with a polished, offline WebEngine viewer that renders Mermaid diagrams and opens same-directory `[[wikilinks]]` in Reader tabs.

**Architecture:** A dedicated Vite/TypeScript bundle parses Markdown with `markdown-it`, renders each Mermaid block independently, and communicates with a Python `MarkdownVisualView` through Qt WebChannel. Python owns file-system resolution, network/file URL policy, lifecycle, fallback HTML, tab creation, caching, packaging, and smoke verification.

**Tech Stack:** Python 3.12+, PySide6 QtWebEngine/QtWebChannel, TypeScript, Vite, Vitest/jsdom, `markdown-it`, official `mermaid`, PyInstaller.

## Global Constraints

- No runtime Node.js, Office COM, internet, CDN, or second process is required.
- Use latest packages through npm, then save exact versions and commit `package-lock.json`.
- Raw Markdown HTML/JavaScript is disabled.
- Mermaid uses strict security and one bad diagram cannot fail the document.
- `[[wikilinks]]` resolve only an exact sibling `.md`; reject empty, absolute, nested, and `..` targets.
- HTTP/HTTPS/WS/WSS are blocked; `file:` is limited to the source directory and viewer bundle.
- Relative images under the source directory remain visible.
- Keep current Python HTML renderer as the whole-view fallback.
- Do not add Markdown editing, backlinks, graph view, embeds, callouts, translation, or dual pane.
- Do not change PPTX behavior or weaken its narrower file allowlist.
- Every task uses RED → GREEN, updates `docs/STATUS.md`, commits, and pushes `origin/main`.

## File Structure

### New web unit

- `web/md-viewer/package.json`, `package-lock.json`: exact supply chain and commands.
- `web/md-viewer/scripts/generate-notices.mjs`: deterministic runtime-license aggregation.
- `web/md-viewer/index.html`: local Qt WebChannel bootstrap only.
- `web/md-viewer/vite.config.ts`, `vitest.config.ts`, `tsconfig.json`: deterministic build/test config.
- `web/md-viewer/src/markdown.ts`: Markdown parser, wiki-link inline rule, relative image rewriting.
- `web/md-viewer/src/mermaid.ts`: strict Mermaid initialization and per-block isolation.
- `web/md-viewer/src/viewer.ts`: DOM composition, link behavior, disposal.
- `web/md-viewer/src/main.ts`: Qt WebChannel bootstrap and source loading.
- `web/md-viewer/src/style.css`: technical-document visual system.
- `web/md-viewer/src/*.test.ts`: unit/integration tests.
- `assets/md-viewer/**`: committed build, notices, deterministic manifest.

### New Python unit

- `src/reader/preview/md_view.py`: bridge, same-directory resolver, request interceptor, WebEngine lifecycle.
- `tests/fixtures/md/visual-document.md`, `linked-note.md`, `diagram.png`: committed real fixture.
- `tests/test_md_view.py`: Python lifecycle/security tests.
- `tests/test_md_webengine.py`: real Chromium rendering and wiki navigation tests.
- `tests/test_md_web_assets.py`: supply-chain/build/resource tests.

### Existing integration

- `src/reader/formats/md.py`: safe fallback and `to_visual`.
- `src/reader/preview/result.py`, `pipeline.py`, `cache.py`: `markdown` kind and visual strategy.
- `src/reader/shell/window.py`: viewer factory, lifecycle signals, wiki tab opening.
- `reader.spec`, `scripts/build_windows.ps1`, `scripts/smoke_windows.ps1`: frozen resources and smoke.
- `tests/test_formats_md.py`, `test_pipeline.py`, `test_cache.py`, `test_window.py`, `test_packaging.py`: integration contracts.

---

### Task 1: Deterministic offline web scaffold and license baseline

**Files:**
- Create: `tests/test_md_web_assets.py`
- Create: `web/md-viewer/package.json`
- Create: `web/md-viewer/package-lock.json`
- Create: `web/md-viewer/index.html`
- Create: `web/md-viewer/tsconfig.json`
- Create: `web/md-viewer/vite.config.ts`
- Create: `web/md-viewer/vitest.config.ts`
- Create: `web/md-viewer/src/main.ts`
- Create: `web/md-viewer/scripts/generate-notices.mjs`
- Create: `web/md-viewer/THIRD_PARTY_NOTICES.txt`
- Modify: `.gitignore`
- Generate: `assets/md-viewer/**`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Produces npm scripts: `test`, `typecheck`, `build`, `notices`.
- Vite output is exactly `assets/md-viewer`, relative-base, empty-before-build.
- Runtime dependencies are exact `markdown-it` and `mermaid`; dev dependencies are exact.

- [ ] **Step 1: Write failing supply-chain/resource tests**

Create tests that require exact versions, local bootstrap, deterministic output, and complete notices:

```python
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "md-viewer"

def test_md_viewer_supply_chain_is_exact_and_offline():
    package = json.loads((WEB / "package.json").read_text("utf-8"))
    assert package["engines"] == {"node": ">=18"}
    assert set(package["dependencies"]) == {"markdown-it", "mermaid"}
    assert all(not value.startswith(("^", "~")) for value in package["dependencies"].values())
    index = (WEB / "index.html").read_text("utf-8")
    assert '<main id="app"></main>' in index
    assert 'qrc:///qtwebchannel/qwebchannel.js' in index
    assert "http://" not in index and "https://" not in index

def test_committed_md_bundle_manifest_matches_bytes():
    bundle = ROOT / "assets" / "md-viewer"
    manifest = bundle / "manifest.sha256"
    expected = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle).as_posix()}"
        for path in sorted(
            (p for p in bundle.rglob("*") if p.is_file() and p != manifest),
            key=lambda p: p.relative_to(bundle).as_posix(),
        )
    ]
    assert manifest.read_text("ascii").splitlines() == expected
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_md_web_assets.py -v
```

Expected: FAIL because `web/md-viewer` and `assets/md-viewer` do not exist.

- [ ] **Step 3: Create package with current exact dependencies**

Run from `web/md-viewer` after verifying the parent `web` directory:

```powershell
npm init -y
npm install --save-exact markdown-it mermaid
npm install --save-dev --save-exact @types/markdown-it @types/node jsdom typescript vite vitest license-checker-rseidelsohn
```

Set:

```json
{
  "name": "reader-md-viewer",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "engines": {"node": ">=18"},
  "scripts": {
    "notices": "node scripts/generate-notices.mjs",
    "test": "vitest run",
    "typecheck": "tsc --noEmit",
    "build": "npm run typecheck && vite build && npm run notices"
  }
}
```

- [ ] **Step 4: Add deterministic Vite and TypeScript configuration**

```typescript
// vite.config.ts
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: {
    outDir: fileURLToPath(new URL("../../assets/md-viewer", import.meta.url)),
    emptyOutDir: true,
  },
});
```

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
export default defineConfig({ test: { environment: "jsdom" } });
```

`tsconfig.json` uses ES2022, ESNext, Bundler resolution, strict,
`noUncheckedIndexedAccess`, DOM libs, and `vitest/globals` + `node` types.

- [ ] **Step 5: Add local bootstrap**

`index.html` contains only `#app`, the qrc WebChannel script, and local
`/src/main.ts`. Initial `main.ts` renders “Markdown viewer loading” without any
network import.

- [ ] **Step 6: Generate complete runtime notices**

`generate-notices.mjs` invokes the installed license checker with production
dependencies, sorts `name@version`, reads every returned `licenseFile`, rejects
missing license text, and writes one deterministic `THIRD_PARTY_NOTICES.txt`.
Copy the same bytes into `assets/md-viewer` after Vite build. Include the
generator itself in tests by asserting every production package reported by:

```powershell
npm ls --omit=dev --all --json
```

appears in the notice.

- [ ] **Step 7: Build and generate manifest**

Run:

```powershell
npm ci
npm test
npm run typecheck
npm run build
```

Generate `assets/md-viewer/manifest.sha256` with the same ordinal relative-path
algorithm used for PPTX. Add `web/md-viewer/node_modules/` to `.gitignore`.

- [ ] **Step 8: Verify GREEN and checkpoint**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_md_web_assets.py -v
git diff --check
```

Update STATUS, commit `feat: establish offline Markdown viewer bundle`, and
push `origin/main`.

---

### Task 2: Markdown parser, wiki syntax, theme, and relative images

**Files:**
- Create: `web/md-viewer/src/markdown.ts`
- Create: `web/md-viewer/src/markdown.test.ts`
- Create: `web/md-viewer/src/style.css`
- Modify: `web/md-viewer/src/main.ts`
- Generate: `assets/md-viewer/**`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Produces:

```typescript
export interface WikiLink {
  element: HTMLAnchorElement;
  target: string;
}
export function renderMarkdown(source: string, sourceUrl: string): {
  fragment: DocumentFragment;
  wikiLinks: WikiLink[];
};
```

- `data-wiki-target` stores target stem; no filesystem path enters generated HTML.

- [ ] **Step 1: Write parser/theme RED tests**

```typescript
it("renders GFM structures, wikilinks, and rewrites relative images", () => {
  const { fragment, wikiLinks } = renderMarkdown(
    "# 文档地图\n\n| 文档 | 用途 |\n|---|---|\n| 本文 | 总览 |\n\n" +
      "[[linked-note|下一篇]]\n\n![diagram](diagram.png)\n\n" +
      "<script>globalThis.pwned=true</script>",
    "file:///C:/docs/index.md",
  );
  const host = document.createElement("div");
  host.append(fragment);
  expect(host.querySelector("table")).not.toBeNull();
  expect(host.querySelector("script")).toBeNull();
  expect(wikiLinks[0]?.target).toBe("linked-note");
  expect(wikiLinks[0]?.element.textContent).toBe("下一篇");
  expect(host.querySelector("img")?.src).toBe("file:///C:/docs/diagram.png");
});

it("does not transform wikilink text inside code", () => {
  const { fragment, wikiLinks } = renderMarkdown(
    "`[[inline]]`\n\n```\n[[fenced]]\n```",
    "file:///C:/docs/index.md",
  );
  expect(wikiLinks).toHaveLength(0);
});
```

- [ ] **Step 2: Run RED**

Run `npm test -- src/markdown.test.ts`; expect missing module/function failure.

- [ ] **Step 3: Implement a markdown-it inline wiki rule**

Register a rule before `link` that recognizes `[[target]]` and
`[[target|alias]]`, emits:

```html
<a class="wiki-link is-pending" data-wiki-target="target">alias</a>
```

Reject empty target/alias in the parser by leaving source text unchanged.
Initialize MarkdownIt with:

```typescript
new MarkdownIt({
  html: false,
  linkify: true,
  typographer: false,
  breaks: false,
}).enable(["table", "strikethrough"]);
```

After rendering through a `<template>`, rewrite only relative `img[src]` with
`new URL(rawSource, sourceUrl).href`; retain `data:` and absolute URLs for the
interceptor to allow/block.

- [ ] **Step 4: Implement the technical-document theme**

Use CSS variables and these measurable contracts:

```css
:root {
  --paper: #fbfbfa;
  --ink: #202124;
  --muted: #62666d;
  --line: #d9dde3;
  --accent: #287f8c;
  --code: #f3f5f7;
}
body { margin: 0; background: var(--paper); color: var(--ink); }
.markdown-document {
  max-width: 980px;
  margin: 0 auto;
  padding: 36px 48px 72px;
  font: 15px/1.72 "Segoe UI", "Microsoft YaHei UI", sans-serif;
}
.table-scroll { overflow-x: auto; margin: 1.25rem 0; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid var(--line); padding: .55rem .7rem; text-align: left; }
th { background: #f0f3f5; font-weight: 650; }
pre { overflow: auto; padding: 1rem; background: var(--code); border-radius: 6px; }
.wiki-link { color: var(--accent); text-decoration: underline; cursor: pointer; }
.wiki-link.is-missing { color: #a04b45; text-decoration-style: dotted; }
```

Wrap each table in `.table-scroll` after render. Add restrained heading,
blockquote, inline-code, link, image, selection, and print rules.

- [ ] **Step 5: Verify GREEN and checkpoint**

Run `npm test`, `npm run typecheck`, `npm run build`, refresh manifest, run
`tests/test_md_web_assets.py`, update STATUS, commit
`feat: render polished Markdown documents`, and push.

---

### Task 3: Strict Mermaid rendering and WebChannel bootstrap

**Files:**
- Create: `web/md-viewer/src/mermaid.ts`
- Create: `web/md-viewer/src/mermaid.test.ts`
- Create: `web/md-viewer/src/viewer.ts`
- Create: `web/md-viewer/src/viewer.test.ts`
- Modify: `web/md-viewer/src/main.ts`
- Modify: `web/md-viewer/src/style.css`
- Generate: `assets/md-viewer/**`
- Modify: `docs/STATUS.md`

**Interfaces:**

```typescript
export interface MarkdownBridge {
  sourceUrl: string;
  viewerReady(): void;
  viewerError(message: string): void;
  wikiExists(target: string, callback: (exists: boolean) => void): void;
  openWiki(target: string): void;
}

export interface MarkdownController { destroy(): void; }
export async function renderMermaidBlocks(root: HTMLElement): Promise<void>;
export async function startViewer(
  root: HTMLElement,
  source: string,
  sourceUrl: string,
  bridge: MarkdownBridge,
  signal?: AbortSignal,
): Promise<MarkdownController>;
```

- [ ] **Step 1: Write Mermaid and bridge RED tests**

Mock `mermaid.render` so one source resolves to `<svg>` and another rejects.
Assert two fenced blocks become one `.mermaid-rendered svg` and one
`.mermaid-error pre`, while paragraph/table remain. Assert `viewerReady` fires
once only after diagrams settle.

For wiki links, fake asynchronous `wikiExists` callbacks and assert:

```typescript
expect(resolved.classList.contains("is-resolved")).toBe(true);
expect(missing.classList.contains("is-missing")).toBe(true);
resolved.click();
expect(bridge.openWiki).toHaveBeenCalledWith("linked-note");
missing.click();
expect(bridge.openWiki).not.toHaveBeenCalledWith("missing");
```

- [ ] **Step 2: Run RED**

Run `npm test -- src/mermaid.test.ts src/viewer.test.ts`; expect missing
implementations.

- [ ] **Step 3: Implement isolated Mermaid rendering**

Initialize once:

```typescript
mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
  theme: "neutral",
  suppressErrorRendering: true,
});
```

For each `pre > code.language-mermaid`, call
`mermaid.render("reader-mermaid-N", source)`. Replace only that `<pre>` on
success. On error replace only it with:

```html
<section class="mermaid-error">
  <strong>图表无法渲染</strong>
  <pre><code></code></pre>
</section>
```

Assign `textContent` for the source; never interpolate source into HTML.

- [ ] **Step 4: Implement viewer lifecycle**

`startViewer` clears prior controller for the same root (WeakMap), renders
Markdown, waits for Mermaid blocks and wiki existence checks, then calls
`viewerReady`. Abort/destroy removes click listeners, empties root, and prevents
late callbacks or `viewerReady`.

Ordinary `a[href]` clicks with HTTP/HTTPS/WS/WSS call `preventDefault`; do not
navigate.

- [ ] **Step 5: Implement Qt bootstrap**

`main.ts` obtains `qt.webChannelTransport`, creates `QWebChannel`, reads
`bridge.sourceUrl`, fetches that local URL, then calls `startViewer`. It owns an
AbortController and exposes `window.readerMdDispose`, also invoked from
`pagehide` and `beforeunload`. Bootstrap/fetch errors call `viewerError` with a
fixed message, not the source path or raw exception.

- [ ] **Step 6: Verify GREEN and checkpoint**

Run all web tests/typecheck/build, refresh notices + manifest, run Python asset
tests, update STATUS, commit `feat: render Mermaid diagrams offline`, and push.

---

### Task 4: Python Markdown result, fallback, pipeline, and cache contract

**Files:**
- Modify: `src/reader/preview/result.py`
- Modify: `src/reader/formats/md.py`
- Modify: `src/reader/preview/pipeline.py`
- Modify: `src/reader/shell/window.py` (`_PreviewWorker.run` only)
- Modify: `tests/test_formats_md.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_cache.py`
- Modify: `tests/test_window.py` (worker cache tests)
- Modify: `docs/STATUS.md`

**Interfaces:**

```python
PreviewKind = Literal["html", "pdf", "pptx", "markdown", "error"]
def to_html(path: Path) -> PreviewResult: ...
def to_visual(path: Path) -> PreviewResult: ...
```

- [ ] **Step 1: Add RED tests**

```python
def test_markdown_visual_contract_and_safe_fallback(tmp_path):
    path = tmp_path / "note.md"
    path.write_bytes(b"# Hello\n\n```mermaid\nflowchart TB\nA-->B\n```\xff")
    result = md.to_visual(path)
    assert result.kind == "markdown"
    assert result.html == ""
    assert result.status_label == "内置预览（视觉模式）"
    assert "<h1>Hello</h1>" in result.fallback_html
    assert "\ufffd" in result.fallback_html
    assert "<script" not in result.fallback_html

def test_markdown_default_is_visual_and_never_calls_office(tmp_path):
    result = preview(note, office=office, mode="builtin")
    assert result.kind == "markdown"
    office.available_for.assert_not_called()
    office.export.assert_not_called()
```

Add cache test that `PreviewCache.put(... kind="markdown")` raises `ValueError`,
and worker test that Markdown visual calls neither cache `get` nor `put`.

- [ ] **Step 2: Run RED**

Run focused format/pipeline/cache/window tests; expect missing `markdown` kind
and current HTML result.

- [ ] **Step 3: Implement safe fallback and visual result**

```python
_MD = MarkdownIt("commonmark", {"html": False}).enable("table")

def _read(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")

def to_visual(path: Path) -> PreviewResult:
    return PreviewResult(
        html="",
        fallback_html=to_html(path).html,
        status_label="内置预览（视觉模式）",
        kind="markdown",
    )
```

Keep fallback CSS readable but do not embed Mermaid JS.

- [ ] **Step 4: Update pipeline and visual cache strategy**

Allow mode `visual` for suffixes `{".pptx", ".md"}`. For `.md` and modes
`builtin`/`visual`, call `fmt_md.to_visual`; Markdown still never enters Office.

In `_PreviewWorker.run`, define visual strategy as:

```python
visual_suffix = suffix in {".pptx", ".md"}
strategy = "visual" if visual_suffix and self.mode in {"builtin", "visual"} else self.mode
```

Skip cache get/put for visual strategy exactly as today.

- [ ] **Step 5: Verify GREEN and checkpoint**

Run focused tests, then full Python suite. Update STATUS, commit
`feat: route Markdown through visual preview`, and push.

---

### Task 5: MarkdownVisualView, same-directory resolver, and security boundary

**Files:**
- Create: `src/reader/preview/md_view.py`
- Create: `tests/test_md_view.py`
- Modify: `docs/STATUS.md`

**Interfaces:**

```python
def resolve_wikilink(source: Path, target: str) -> Path | None: ...

class MarkdownBridge(QObject):
    ready = Signal()
    failed = Signal(str)
    open_path = Signal(str)
    missing = Signal(str)
    sourceUrl = Property(str, constant=True)

    @Slot(str, result=bool)
    def wikiExists(self, target: str) -> bool: ...
    @Slot(str)
    def openWiki(self, target: str) -> None: ...
    @Slot()
    def viewerReady(self) -> None: ...
    @Slot(str)
    def viewerError(self, message: str) -> None: ...

class MarkdownVisualView(QWebEngineView):
    ready = Signal(int)          # emits 1 for generic visual binding
    render_failed = Signal(str)
    open_path = Signal(str)
    missing_link = Signal(str)
    def start(self) -> None: ...
    def shutdown(self) -> None: ...
```

- [ ] **Step 1: Write resolver RED tests**

Cover `[[other]]`, `[[other.md]]`, case-insensitive Windows suffix,
missing target, empty target, absolute path, `..`, `/`, `\`, non-md suffix, and
a symlink/junction escape when available. Expected output is resolved canonical
sibling path or `None`.

- [ ] **Step 2: Write view/interceptor RED tests**

Mirror the PPTX lifecycle tests but assert:

- construction does not load;
- `start()` loads `assets/md-viewer/index.html`;
- profile is off-the-record and per-view;
- file allowlist permits source, sibling `diagram.png`, and bundle assets;
- blocks parent/sibling-directory paths, symlink escape, and all remote schemes;
- bridge `wikiExists`/`openWiki` use resolver and emit no untrusted path;
- missing bundle/load timeout/bridge error shows fixed safe fallback;
- repeated shutdown and close-during-start are safe.

- [ ] **Step 3: Run RED**

Run `pytest tests/test_md_view.py -v`; expect missing module.

- [ ] **Step 4: Implement resolver and bridge**

Resolver algorithm:

```python
def resolve_wikilink(source: Path, target: str) -> Path | None:
    value = target.strip()
    if (
        not value
        or "\x00" in value
        or "/" in value
        or "\\" in value
        or Path(value).is_absolute()
        or Path(value).suffix.lower() not in {"", ".md"}
        or value in {".", ".."}
    ):
        return None
    name = value if value.lower().endswith(".md") else f"{value}.md"
    candidate = (source.resolve().parent / name).resolve()
    if candidate.parent != source.resolve().parent or not candidate.is_file():
        return None
    return candidate
```

Bridge returns only bool to JS. `openWiki` emits canonical path only after the
same resolver succeeds; otherwise emits the original display target via
`missing` (bounded to 256 characters).

- [ ] **Step 5: Implement isolated WebEngine lifecycle**

Follow the proven ownership order from `PptxVisualView`, but keep
Markdown-specific bridge and interceptor in `md_view.py`. The interceptor
allows:

- `qrc`, `data`, `blob`;
- canonical bundle root descendants;
- canonical source-directory descendants;
- nothing else.

On fallback: stop loading, clear scripts/channel, disable JavaScript, then
`setHtml(fallback_html, QUrl())`; cap fallback at 1,900,000 UTF-8 bytes and use
a fixed safe fallback beyond the cap.

- [ ] **Step 6: Verify GREEN and checkpoint**

Run `tests/test_md_view.py`, `tests/test_pptx_view.py`, then full suite. Update
STATUS, commit `feat: host Markdown in isolated WebEngine view`, and push.

---

### Task 6: MainWindow lifecycle and wiki-link tab integration

**Files:**
- Modify: `src/reader/shell/window.py`
- Modify: `tests/test_window.py`
- Modify: `docs/STATUS.md`

**Interfaces:**
- `_default_viewer` maps `kind="markdown"` to `MarkdownVisualView`.
- `_bind_visual_events` additionally binds optional `open_path` and
  `missing_link` signals.
- Resolved wiki links call existing `MainWindow.open_paths([path])`.

- [ ] **Step 1: Write RED window tests**

Use a fake Markdown view with `ready`, `render_failed`, `open_path`,
`missing_link`, `start`, and `shutdown`. Assert:

1. default `.md` creates the fake visual view and calls `start`;
2. `open_path.emit(sibling)` creates a second tab;
3. emitting the same path focuses the existing tab;
4. stale signal after source tab replacement/close does nothing;
5. `missing_link.emit("missing")` updates status but creates no tab;
6. closing tab/window calls `shutdown`;
7. Markdown visual ready does not call PPTX-specific slide telemetry.

- [ ] **Step 2: Run RED**

Run focused new tests; expect HTML viewer or absent signal binding.

- [ ] **Step 3: Integrate viewer and signals**

Set initial mode to visual for `{".pptx", ".md"}`. In factory:

```python
if result.kind == "markdown":
    from reader.preview.md_view import MarkdownVisualView
    return MarkdownVisualView(result, source_path)
```

Extend `_bind_visual_events` with optional signal connections guarded by the
same document identity/generation/widget/layout checks. `_visual_open_path`
calls `open_paths([path])` only for an active visual document.
`_visual_missing_link` displays `找不到：{target}`.

In `_visual_ready`, call `append_visual_ready` only when
`document.last_result.kind == "pptx"`; still retain Markdown readiness.

- [ ] **Step 4: Verify GREEN and checkpoint**

Run all window tests and full Python suite. Update STATUS, commit
`feat: open Markdown wikilinks in Reader tabs`, and push.

---

### Task 7: Real Chromium fidelity, Mermaid isolation, and network tests

**Files:**
- Create: `tests/fixtures/md/visual-document.md`
- Create: `tests/fixtures/md/linked-note.md`
- Create: `tests/fixtures/md/diagram.png`
- Create: `tests/test_md_webengine.py`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Real fixture includes heading, table, Python code, valid flowchart, invalid
  Mermaid block, relative image, resolved alias wiki link, missing wiki link,
  and remote image/link probes.

- [ ] **Step 1: Add real QWebEngine RED test**

Wait for `ready == [1]`, then probe DOM:

```python
assert data["title"] == "文档地图"
assert data["table_rows"] >= 2
assert data["python_code"] is True
assert data["mermaid_svg"] == 1
assert data["mermaid_errors"] == 1
assert data["raw_valid_source_visible"] is False
assert data["local_image_loaded"] is True
assert data["resolved_class"] is True
assert data["missing_class"] is True
```

Click resolved wiki and assert `open_path` emits canonical `linked-note.md`.
Click missing wiki and assert only `missing_link` emits.

- [ ] **Step 2: Add network and lifecycle RED test**

Before injection, blocked snapshot must be empty. Inject HTTP, HTTPS, WS, WSS
requests after temporarily enabling local remote access at the first layer;
assert the interceptor records exactly all four and blocks them. Assert
shutdown invalidates the profile.

- [ ] **Step 3: Run RED and fix only integration defects**

Run `pytest tests/test_md_webengine.py -v`. Any failure must be fixed in the
smallest owning unit (`md-viewer` web code or `md_view.py`) with its unit test
first; do not weaken assertions.

- [ ] **Step 4: Verify GREEN and checkpoint**

Run Markdown web tests, Markdown Python tests, PPTX WebEngine regression, and
full Python suite. Update STATUS, commit
`test: verify Markdown visual preview in Chromium`, and push.

---

### Task 8: Frozen packaging, smoke, final review, and desktop handoff

**Files:**
- Modify: `reader.spec`
- Modify: `scripts/build_windows.ps1`
- Modify: `scripts/smoke_windows.ps1`
- Modify: `src/reader/smoke.py` only if telemetry becomes format-generic
- Modify: `tests/test_packaging.py`
- Modify: `tests/test_smoke.py` only if telemetry changes
- Modify: `docs/STATUS.md`
- Rebuild: `dist/Reader/Reader.exe`
- Refresh: desktop `Reader.lnk`

**Interfaces:**
- PyInstaller collects entire `assets/md-viewer`.
- Build performs `npm ci`, tests/typecheck/build, notices, manifest validation
  for both web bundles before PyInstaller.
- Frozen smoke opens the real Markdown fixture and waits for a Markdown-ready
  record or another durable, format-explicit signal.

- [ ] **Step 1: Write packaging RED tests**

Assert:

```python
assert "(str(ROOT / 'assets/md-viewer'), 'assets/md-viewer')" in spec
assert 'Invoke-Npm "ci --prefix web\\md-viewer"' in build
assert 'Invoke-Npm "run build --prefix web\\md-viewer"' in build
assert "_internal\\assets\\md-viewer\\index.html" in build
assert "_internal\\assets\\md-viewer\\manifest.sha256" in build
assert "_internal\\assets\\md-viewer\\THIRD_PARTY_NOTICES.txt" in build
```

Extend npm fail-fast test so either web package failure happens before
dist/build cleanup and PyInstaller.

- [ ] **Step 2: Implement generic bundle manifest function**

Rename the PowerShell helper from PPTX-specific to format-neutral:

```powershell
function Test-WebBundleManifest {
    param([string]$ManifestPath, [string]$BundlePath, [string]$MismatchLabel)
    # retain strict nonblank "64 lowercase hex + two spaces + path" validation
}
```

Build PPTX then Markdown, copy each notice, generate ordinal manifests, verify
source manifests, run PyInstaller, then verify both frozen manifests.

- [ ] **Step 3: Add frozen Markdown smoke**

Use a separate clean phase/process to open
`tests/fixtures/md/visual-document.md`. Record explicit
`kind="markdown", status="ready"` without changing PPTX `slides=4` semantics.
Require no renderer failure, stop Reader/QtWebEngine children, and remove
isolated profile before IPC Phase B.

- [ ] **Step 4: Run focused and full verification**

```powershell
npm --prefix web\md-viewer ci
npm --prefix web\md-viewer test
npm --prefix web\md-viewer run typecheck
npm --prefix web\md-viewer run build
.venv\Scripts\python.exe -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_windows.ps1 -ReaderExe dist\Reader\Reader.exe
```

- [ ] **Step 5: Final independent review**

Review for Critical/Important findings, specifically:

- raw HTML/script execution;
- path traversal or symlink escape through wikilinks/images;
- remote requests;
- late WebChannel callbacks opening tabs after close;
- one bad Mermaid diagram failing the document;
- stale bundle assets or missing runtime licenses;
- PPTX lifecycle/build/smoke regression.

Fix any finding with RED/GREEN evidence and a new commit (do not amend a failed
hook commit).

- [ ] **Step 6: Refresh desktop and record hashes**

Refresh `Reader.lnk`; verify target/workdir/icon. Record source/frozen
Markdown manifest SHA256, executable byte size/SHA256, test counts, frozen
smoke result, and review verdict in STATUS.

- [ ] **Step 7: Final commit and push**

Mark the Markdown goal complete, set next acceptance step, commit
`test: certify Markdown visual preview in frozen Reader`, push `origin/main`,
and verify `git status --short --branch` is clean and synchronized.

## Self-Review Record

- [x] Spec coverage: theme, complete pinned Mermaid, per-block failure,
  same-directory wiki links, relative images, fallback, security, lifecycle,
  cache, packaging, frozen smoke, and handoff each map to a task.
- [x] Placeholder scan: no placeholder token or unspecified code step.
- [x] Type consistency: `kind="markdown"`, `MarkdownBridge`,
  `MarkdownVisualView.ready(int)`, `open_path`, `missing_link`,
  `renderMarkdown`, `renderMermaidBlocks`, and `startViewer` use one spelling
  across tasks.
- [x] Scope correction: `.markdown` was removed; Reader supports `.md` only.
