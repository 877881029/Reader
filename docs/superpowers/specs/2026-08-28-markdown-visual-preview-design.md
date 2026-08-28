# Markdown Visual Preview Design

Date: 2026-08-28  
Status: Approved by user (Approach A); awaiting implementation plan  
Depends on: `docs/superpowers/specs/2026-08-21-reader-design.md`  
Progress ledger: `docs/STATUS.md`

This increment supersedes the v1 Markdown note that Mermaid stays a fenced code block.

## 1. Goal

Make daily `.md` files look like a document reader, not a dump of CommonMark HTML:

1. Technical-document reading theme: readable measure, heading hierarchy, bordered tables, fenced code, blockquotes, and link styling.
2. Fenced `mermaid` diagrams render as SVG using the official Mermaid library, offline.
3. Obsidian-style `[[wikilinks]]` resolve sibling Markdown files and open them as Reader tabs.
4. Default open path stays fast and local: no Office COM, no outbound network.

This increment does not add dual pane, translation, format conversion, Markdown editing, or graph/backlink views.

## 2. Problem (current)

`src/reader/formats/md.py` uses `MarkdownIt("commonmark").enable("table")` and a few inline CSS rules. Tables become HTML, but:

- Fenced `mermaid` diagrams stay source text.
- `[[01 A0 vs B0 全景对比（实测）]]` stays literal brackets.
- Theme, spacing, and table chrome are thinner than typical note/doc viewers.

The screenshot gap is therefore missing diagram rendering and wiki-link behavior, plus under-styled HTML—not a broken table parser.

## 3. Non-goals

- Do not require internet, Node at runtime, or a second process to preview Markdown.
- Do not execute raw HTML/JavaScript from the document (`markdown-it` HTML remains disabled).
- Do not implement Obsidian vaults, tags, `![[embed]]`, Dataview, or callouts.
- Do not change Word/Excel/PPTX pipelines except shared viewer plumbing if required.
- Do not auto-open unresolved wiki targets or search the whole disk.

## 4. Approved decisions

| Topic | Choice |
|---|---|
| Architecture | Approach A: dedicated local Markdown WebEngine viewer, same isolation pattern as PPTX |
| Theme | Light technical-document theme; CSS variables; not a generic purple landing page |
| Mermaid | Official `mermaid` package, pinned, offline; flowchart, sequence, class, state, ER and other diagrams the pinned version supports natively |
| Wiki links | `[[name]]` and `[[name\|alias]]`; click opens the sibling `.md` in a Reader tab |
| Fallback | Keep Python `markdown-it-py` HTML as load-failure fallback |
| Network | Block HTTP/HTTPS/WS/WSS; allow `file` only under the source directory and the viewer bundle |

## 5. Architecture

```text
.md path
  → pipeline default visual for .md
  → PreviewResult(kind="markdown", fallback_html=python markdown HTML)
  → MarkdownVisualView (QWebEngineView)
        loads assets/md-viewer (Vite bundle)
        WebChannel: sourceUrl, ready/error, openPath
        Mermaid renders in-page from fenced blocks
```

- New `web/md-viewer` package, output to `assets/md-viewer/`, collected by PyInstaller like `assets/pptx-viewer`.
- Parser in the web bundle: `markdown-it` with GFM table, strikethrough, and a small wiki-link plugin. Python `to_html` stays as fallback and may share CSS class names, not the Mermaid engine.
- Pipeline: `.md` in `builtin`/`visual` uses the visual viewer. `text` mode (if exposed later) can keep current HTML; v1 of this increment does not add a Markdown “文本模式” toolbar unless the visual viewer fails.
- Cache: visual Markdown skips mixing with old builtin HTML cache the same way PPTX visual does (`kind="markdown"` is not stored as reusable `html` artifact).
- Worker remains UI-free. Wiki-link navigation is a WebChannel request handled on the UI thread via existing `MainWindow.open_paths`.

Reuse PPTX viewer lessons without merging the two pages:

- Off-the-record profile, interceptor, explicit `start()`/`shutdown()`, Qt WebChannel qrc injection.
- `file:` allowlist uses Windows `normcase(realpath)`.
- Difference vs PPTX: Markdown must read sibling assets (images, linked `.md` is opened by Python, not fetched as navigation). Allow `file:` reads whose realpath is the source file or a file under the source parent directory, plus the viewer bundle root.

## 6. Rendering contract

### 6.1 Theme

- Centered reading column, comfortable line length, Segoe UI / system Chinese UI fonts for body, monospace for code.
- Tables: collapsed borders, header background, cell padding, horizontal overflow scroll.
- Code: muted background, overflow scroll, language class preserved when present.
- Headings, lists, blockquotes, hr, and inline code have distinct styles.
- Wiki links look like links; missing targets use a distinct unresolved style (not an exception page).

### 6.2 Mermaid

- Fenced blocks with language `mermaid` render in place.
- Pin one MIT-licensed `mermaid` version in `package-lock.json`; copy license into `THIRD_PARTY_NOTICES.txt`.
- `securityLevel` stays strict (`strict` / no loose HTML in nodes beyond library defaults).
- One diagram failure: that block shows the source plus a short Chinese error; other diagrams and the rest of the document continue.
- Viewer bootstrap failure: replace the page with `fallback_html` and status `内置预览（视觉渲染失败）`.

### 6.3 Wiki links

Syntax:

- `[[stem]]` display and target stem.
- `[[stem|alias]]` display alias, target stem.
- Do not treat ordinary Markdown `[text](url)` as wiki links.

Resolution, in order, all under the source file’s parent directory only:

1. Reject empty targets, absolute paths, `..`, and targets containing `/` or
   `\`; wiki links are intentionally same-directory only.
2. Exact `stem` if it already has `.md`; otherwise `stem.md`.
3. Otherwise unresolved.

Click:

- Resolved path: `MainWindow.open_paths`; existing tab with that path is focused (`decide_open`).
- Unresolved: no navigation; optional status `找不到：{stem}`.
- Non-Markdown resolved names are not created by this resolver (only `.md`).

### 6.4 Images and other Markdown

- Relative images under the source directory load via `file:`.
- Remote image URLs are blocked; broken-image placeholder is acceptable.
- Autolinks/HTTP links in the document do not fetch; clicks that would leave `file`/`qrc`/`data`/`blob` are ignored.

## 7. UI and lifecycle

- Markdown remains a vertically scrolling document (no thumbnail rail).
- Status: `内置预览` when ready; failure label as in §6.2.
- Closing the tab/window must `shutdown()` the profile like PPTX.
- Frozen Reader must load `assets/md-viewer` from the bundled resource path.

## 8. Error handling

| Case | Behavior |
|---|---|
| Unreadable `.md` | Tab error, other tabs unchanged |
| Viewer bundle missing | Fallback HTML + visual-failure status |
| Single Mermaid parse/render error | Local placeholder, document continues |
| Wiki target missing | Unresolved style, no crash |
| Encrypted/binary pretending to be `.md` | Decode with UTF-8; replacement characters allowed; do not crash |

## 9. Testing (TDD)

- Fixture note with heading, GFM table, fenced Python, `mermaid` flowchart, relative image, resolved `[[other]]`, unresolved `[[missing]]`.
- Default `.md` open does not call Office COM.
- Node/jsdom (or equivalent) asserts table HTML, wiki `href`/`data-wiki` attributes, and Mermaid SVG or rendered container for the flowchart.
- Real QWebEngine: table visible, flowchart not remaining as raw `flowchart TB` source, wiki click requests the sibling path.
- Interceptor: initial blocked snapshot empty; injected HTTP/HTTPS/WS/WSS blocked.
- Frozen smoke or packaging test: `assets/md-viewer` present with `index.html`, notices, and `manifest.sha256`.

## 10. Process requirement

Implementation must follow `docs/STATUS.md` and `.cursor/rules/git-progress-handoff.mdc`: commit and push at spec, plan, and task boundaries.
