# Markdown Visual Preview Task 3 Report

## Scope

- Implement strict Mermaid per-block rendering in web viewer.
- Implement viewer lifecycle with async wiki existence checks and click bridge.
- Implement Qt WebChannel bootstrap with abort/dispose ownership and fixed error reporting.

## TDD Record

### RED

- Ran `npm test -- src/mermaid.test.ts src/viewer.test.ts`.
- Observed expected missing implementation failures:
  - `Failed to resolve import "./mermaid"`
  - `Failed to resolve import "./viewer"`

### GREEN

- Added `mermaid.ts` + `mermaid.test.ts` with mocked `mermaid.render` success/failure.
- Added `viewer.ts` + `viewer.test.ts` covering:
  - async `wikiExists` timing and resolved/missing classes
  - resolved/missing click bridge behavior
  - remote anchor `preventDefault`
  - abort + late callback suppression
- Expanded `main.test.ts` to cover:
  - WebChannel bootstrap fetch/start path
  - fixed bootstrap error message without source path leak
  - `readerMdDispose` and unload lifecycle disposal

## Functional Outcomes

- Mermaid is initialized exactly once with:
  - `startOnLoad: false`
  - `securityLevel: "strict"`
  - `theme: "neutral"`
  - `suppressErrorRendering: true`
- Each `pre > code.language-mermaid` is rendered independently.
- Failed Mermaid blocks are replaced with `.mermaid-error`; source is written via `textContent` (no HTML interpolation).
- One bad diagram does not break other markdown content.
- `startViewer(...)` keeps per-root ownership in `WeakMap`, destroying prior controller before rebind.
- `viewerReady()` fires once only after Mermaid and all wiki existence checks settle.
- Wiki links become `.is-resolved` / `.is-missing`; only resolved links call `openWiki(target)`.
- Ordinary `http/https/ws/wss` anchors are blocked with `preventDefault`.
- Abort/destroy is idempotent: listeners removed, root cleared, late callbacks and late ready suppressed.
- `main.ts` bootstraps from `qt.webChannelTransport` + `QWebChannel`, fetches `bridge.sourceUrl`, owns `AbortController`, exposes `window.readerMdDispose`, and binds `pagehide`/`beforeunload`.
- Bootstrap/fetch/start errors use fixed `viewerError` message without leaking path/raw exception.
- Raw HTML remains disabled via existing `markdown-it` config (`html: false`).

## Verification Evidence

- Focused Task 3 tests:
  - `npm test -- src/mermaid.test.ts src/viewer.test.ts` -> `4 passed`
- Full web tests:
  - `npm test` -> `12 passed`
- Type check:
  - `npm run typecheck` -> pass
- Build (includes notices + manifest refresh):
  - `npm run build` -> pass
- Python markdown asset tests:
  - `python -m pytest tests/test_md_web_assets.py -v` -> `7 passed`
- Diff hygiene:
  - `git diff --check` -> no whitespace errors (CRLF warnings only)

## Files Changed

- `web/md-viewer/src/mermaid.ts`
- `web/md-viewer/src/mermaid.test.ts`
- `web/md-viewer/src/viewer.ts`
- `web/md-viewer/src/viewer.test.ts`
- `web/md-viewer/src/main.ts`
- `web/md-viewer/src/main.test.ts`
- `web/md-viewer/src/style.css`
- `web/md-viewer/src/type-fest.d.ts`
- `assets/md-viewer/**`
- `docs/superpowers/plans/2026-08-28-markdown-visual-preview.md`
- `docs/STATUS.md`

## Concerns

- `vite build` still emits non-blocking warning for `qrc:///qtwebchannel/qwebchannel.js` bundling semantics; expected for Qt runtime script injection and does not affect build pass/fail.
# Markdown Visual Preview Task 3 Report

## 实现内容
- 新增 `web/md-viewer/src/mermaid.ts`：实现 `renderMermaidBlocks(root)`，按块调用 `mermaid.render`，初始化固定为 `securityLevel: "strict"`、`theme: "neutral"`、`suppressErrorRendering: true`、`startOnLoad: false`。
- Mermaid 渲染策略为“逐块隔离”：成功块替换为 `.mermaid-rendered` SVG，失败块仅替换为 `.mermaid-error`，并将原源码通过 `textContent` 写入 `<pre><code>`，避免 HTML 注入。
- 新增 `web/md-viewer/src/viewer.ts`：实现 `MarkdownBridge`/`MarkdownController` 与 `startViewer(...)`，包含 WeakMap root ownership、root 重入前清理、wiki 异步存在性检查、remote anchor 拦截、abort/destroy 幂等收尾。
- `startViewer` 在 Mermaid 与 wiki 检查全部完成后只触发一次 `viewerReady`；destroy/abort 会清理 click listener、清空 root，并阻断迟到回调与迟到 ready。
- 修改 `web/md-viewer/src/main.ts`：完成 Qt WebChannel bootstrap（`qt.webChannelTransport` + `QWebChannel`），读取 `bridge.sourceUrl` 后 fetch 本地 markdown，持有 `AbortController` 并暴露 `window.readerMdDispose`，同时绑定 `pagehide/beforeunload`。
- bootstrap/fetch/startViewer 失败统一调用固定 `viewerError` 文案，不回传 source path 或原始异常细节。
- 修改 `web/md-viewer/src/style.css`：补充 `.mermaid-rendered`、`.mermaid-error`、`.wiki-link.is-resolved` 样式。
- 更新 `docs/superpowers/plans/2026-08-28-markdown-visual-preview.md` Task 3 Step 1-6 全部勾选；更新 `docs/STATUS.md` 的 Task 3 完成记录与下一步。

## RED/GREEN 与验证
### RED（严格先测）
```powershell
npm test -- src/mermaid.test.ts src/viewer.test.ts
```
- 结果：失败（符合预期 RED）
- 关键失败：`Failed to resolve import "./mermaid"`、`Failed to resolve import "./viewer"`

### GREEN（实现后聚焦）
```powershell
npm test -- src/mermaid.test.ts src/viewer.test.ts
```
- 结果：`2 files, 4 tests passed`

### 全量门禁验证
```powershell
npm test
npm run typecheck
npm run build
python -m pytest tests/test_md_web_assets.py -v
git diff --check
```
- `npm test`：`4 files, 12 tests passed`
- `npm run typecheck`：通过
- `npm run build`：通过，`assets/md-viewer/**` 刷新（含 notices + manifest）
- `pytest tests/test_md_web_assets.py -v`：`7 passed`
- `git diff --check`：通过（仅 LF/CRLF warning，无 whitespace error）

## 变更文件
- `web/md-viewer/src/mermaid.ts`
- `web/md-viewer/src/mermaid.test.ts`
- `web/md-viewer/src/viewer.ts`
- `web/md-viewer/src/viewer.test.ts`
- `web/md-viewer/src/main.ts`
- `web/md-viewer/src/main.test.ts`
- `web/md-viewer/src/style.css`
- `web/md-viewer/src/type-fest.d.ts`
- `assets/md-viewer/**`
- `docs/superpowers/plans/2026-08-28-markdown-visual-preview.md`
- `docs/STATUS.md`

## 自审与约束对照
- Mermaid 安全级别固定为 strict，且启用 `suppressErrorRendering: true`。
- Mermaid 错误源码使用 `textContent`，未做 HTML 插值。
- 单个坏图仅影响该代码块，不影响页面其它段落/表格内容。
- 普通 remote anchor（`http/https/ws/wss`）点击会 `preventDefault`，不导航。
- raw HTML 保持禁用（`markdown-it html: false`）。
- wiki link 异步存在性与点击行为已覆盖 resolved/missing 两分支。
- bootstrap 错误文案已覆盖“固定消息 + 不泄露 path”的回归测试。

## Concerns
- `npm run build` 仍会输出 Vite 提示：`qrc:///qtwebchannel/qwebchannel.js ... can't be bundled without type="module"`；该脚本为 Qt 运行时注入依赖，构建结果与任务功能不受影响。
# Markdown Visual Preview Task 3 Report

## Scope

- Implement strict Mermaid per-block rendering in web viewer.
- Implement markdown viewer lifecycle with wiki existence/click bridge and abort-safe cleanup.
- Implement Qt WebChannel bootstrap in `main.ts` with fixed error reporting and dispose hooks.

## TDD Record

### RED

- Ran `npm test -- src/mermaid.test.ts src/viewer.test.ts` to validate Task 3 focused suite wiring.
- During full web verification, `src/main.test.ts` failed under Vite dynamic import rules (`Invalid loader value`) and exposed a TS typing issue in bootstrap globals.

### GREEN

- Switched `src/main.test.ts` dynamic import to stable module import with `vi.resetModules()` retained.
- Added constructor-compatible `QWebChannel` test stub type cast.
- Narrowed bootstrap mount node in `src/main.ts` via `rootElement` guard alias.
- Added local `src/type-fest.d.ts` declarations (`SetOptional`, `SetRequired`, `RequiredDeep`) to satisfy `mermaid@11.17.2` type imports without changing locked dependency policy.

## Functional Outcomes

- Mermaid init is single-shot with `securityLevel: "strict"` and `suppressErrorRendering: true`.
- Mermaid rendering is isolated per fenced block; one failed diagram renders `.mermaid-error` and does not break surrounding content.
- Mermaid error source is assigned via `textContent` (no HTML interpolation).
- Viewer waits for Mermaid render completion and all async `wikiExists` callbacks before single-fire `viewerReady`.
- Resolved wiki links call `openWiki`; missing links never call `openWiki`.
- Remote `http/https/ws/wss` anchors are prevented from navigation.
- Abort/destroy is idempotent: removes listeners, clears root, and blocks late callbacks/ready.
- Bootstrap fetch/start failures report fixed `viewerError` message without path/exception leakage.
- `window.readerMdDispose` is exposed and bound to `pagehide` / `beforeunload`.
- Raw HTML remains disabled in markdown parser.

## Verification Evidence

- Focused Task 3 tests:
  - `npm test -- src/mermaid.test.ts src/viewer.test.ts` -> `4 passed`
- Full web tests:
  - `npm test` -> `12 passed`
- Type check:
  - `npm run typecheck` -> pass
- Build (includes notices + manifest refresh):
  - `npm run build` -> pass
- Python markdown web asset tests:
  - `python -m pytest tests/test_md_web_assets.py -v` -> `7 passed`

## Files Touched In This Task

- `web/md-viewer/src/mermaid.ts`
- `web/md-viewer/src/mermaid.test.ts`
- `web/md-viewer/src/viewer.ts`
- `web/md-viewer/src/viewer.test.ts`
- `web/md-viewer/src/main.ts`
- `web/md-viewer/src/main.test.ts`
- `web/md-viewer/src/style.css`
- `web/md-viewer/src/type-fest.d.ts`
- `assets/md-viewer/**` (build artifacts + manifest/notices refresh)
- `docs/superpowers/plans/2026-08-28-markdown-visual-preview.md` (Task 3 checkboxes)
- `docs/STATUS.md` (Task 3 progress sync)

## Concerns

- `vite build` emits non-blocking warning about `qrc:///qtwebchannel/qwebchannel.js` script tag bundling semantics; current behavior is expected for Qt runtime injection and does not fail build/test.
