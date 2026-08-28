# Markdown Visual Preview Task 2 Report

## 实现内容
- 新增 `web/md-viewer/src/markdown.ts`，实现 `renderMarkdown(source, sourceUrl)` 与 `WikiLink` 接口。
- 使用 `markdown-it`（`html: false`、`linkify: true`、`typographer: false`、`breaks: false`）并启用 `table`、`strikethrough`。
- 注册 inline 规则（位于 `link` 前）解析 `[[target]]` 与 `[[target|alias]]`，输出：
  - `<a class="wiki-link is-pending" data-wiki-target="target">alias</a>`
  - 空 target / 空 alias 会拒绝转换，保留原始文本。
- 渲染后通过 `<template>` DOM 后处理：
  - 仅重写相对 `img[src]` 到 `new URL(rawSource, sourceUrl).href`
  - 保留 `data:`、绝对 URL、`//`、`#...` 形式不改写
  - 每个 `table` 包裹 `.table-scroll`
- 新增 `web/md-viewer/src/style.css` 技术文档主题（变量、表格、代码、引用、标题、链接、图片、selection、print）。
- 修改 `web/md-viewer/src/main.ts`：引入样式并将渲染结果挂载到 `.markdown-document`。
- 更新 `docs/superpowers/plans/2026-08-28-markdown-visual-preview.md` Task 2 Step 1-5 全部勾选。
- 更新 `docs/STATUS.md`，记录 Task 2 完成项、验证结果与下一步切换到 Task 3。

## RED/GREEN 命令与关键输出
### RED
```powershell
npm test -- src/markdown.test.ts
```
- 结果：失败（符合预期 RED）
- 关键输出：
  - `Failed to resolve import "./markdown" from "src/markdown.test.ts". Does the file exist?`

### GREEN（实现后）
```powershell
npm test -- src/markdown.test.ts
```
- 结果：`2 passed`

### 全量门禁验证
```powershell
npm test
npm run typecheck
npm run build
python -m pytest tests/test_md_web_assets.py -v
git diff --check
```
- `npm test`：`2 files, 3 tests passed`
- `npm run typecheck`：通过
- `npm run build`：通过，产物刷新到 `assets/md-viewer/`
- `pytest tests/test_md_web_assets.py -v`：`7 passed`
- `git diff --check`：无空白错误（仅 LF/CRLF 警告）

## 变更文件
- `web/md-viewer/src/markdown.ts`
- `web/md-viewer/src/markdown.test.ts`
- `web/md-viewer/src/style.css`
- `web/md-viewer/src/main.ts`
- `assets/md-viewer/index.html`
- `assets/md-viewer/assets/index-25FDcigA.css`
- `assets/md-viewer/assets/index-Rq43_jMh.js`
- `assets/md-viewer/manifest.sha256`
- `docs/superpowers/plans/2026-08-28-markdown-visual-preview.md`
- `docs/STATUS.md`

## 自审结果
- raw HTML 已禁用：`<script>` 不会进入输出 DOM。
- 代码块与行内代码中的 `[[...]]` 不触发 wikilink 解析（测试覆盖）。
- `data-wiki-target` 仅存储 wiki target stem，未注入文件系统绝对路径。
- 相对图片改写与 table wrapper 均在渲染后 DOM 阶段处理，逻辑清晰且可测。
- 未提前实现 Mermaid/WebChannel；本次仅覆盖 parser/theme 范围。

## Concerns
- `npm run build` 输出包含 Vite 提示：`qrc:///qtwebchannel/qwebchannel.js can't be bundled without type="module"`。该脚本是预期运行时注入依赖，构建成功且不影响当前 Task 2 功能。

---

## Reviewer Needs fixes 追加（Task 2）

### 修复内容
- `web/md-viewer/src/markdown.ts` 的 wikilink inline rule 在开头增加链接上下文防护：`state.linkLevel > 0` 时直接 `return false`，禁止在普通 Markdown 链接文本中转换 wikilink，避免生成嵌套 `<a>`。
- 同时修正 rule 的 silent 分支返回逻辑，避免 `ParserInline.skipToken` 在链接标签解析场景触发 `inline rule didn't increment state.pos` 异常。

### 新增回归测试
- `wikilink inside ordinary Markdown link`：`[see [[note]]](target.md)` 不转换为 wiki link，且最终仅保留外层合法 `<a href="target.md">...`
- `empty target / empty alias`：`[[|alias]]` 与 `[[target|]]` 保持源码文本，不生成 wiki link
- `absolute/special image src`：`http://`、`data:`、`#hash`、`//protocol-relative` 不被相对路径改写

### RED / GREEN 记录
#### RED
```powershell
npm test -- src/markdown.test.ts
```
- 结果：`1 failed, 4 passed`
- 关键失败：`renderMarkdown > does not transform wikilinks inside markdown links`
- 关键报错：`inline rule didn't increment state.pos`

#### GREEN
```powershell
npm test -- src/markdown.test.ts
```
- 结果：`5 passed`

### 本轮门禁验证
```powershell
npm test
npm run typecheck
npm run build
python -m pytest tests/test_md_web_assets.py -v
git diff --check
```
- `npm test`：`2 files, 6 tests passed`
- `npm run typecheck`：通过
- `npm run build`：通过（刷新 `assets/md-viewer` bundle 与 manifest）
- `pytest tests/test_md_web_assets.py -v`：`7 passed`
- `git diff --check`：通过（仅 LF/CRLF warnings）

### 本轮变更文件
- `web/md-viewer/src/markdown.ts`
- `web/md-viewer/src/markdown.test.ts`
- `assets/md-viewer/index.html`
- `assets/md-viewer/assets/index-CEBkNwzv.js`
- `assets/md-viewer/manifest.sha256`
- `docs/STATUS.md`
- `.superpowers/sdd/md-task-2-report.md`

### 自审
- Important 项已关闭：普通链接内不会再展开 wikilink，也不会产生 nested anchor。
- Minor 回归已覆盖并验证通过，图片 URL 重写边界更完整。
- `docs/STATUS.md` 仅追加审查修复记录，`## 下一步` 保持 Task 3 不变。
