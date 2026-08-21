# Reader v1 Design

Date: 2026-08-21  
Status: Draft for user review  
Product: Reader, a Windows desktop document viewer for daily work

## 1. Goal

Ship a single-icon Windows GUI named Reader that opens and high-fidelity-previews `.docx`, `.pptx`, `.xlsx`, and `.md`. Users launch it from a desktop shortcut, drag files in, or choose Reader from Explorer’s “Open with” list. Multiple documents open as tabs; a second window can be created when needed. One process, one taskbar icon.

v1 does not convert formats, split the view into original/Chinese panes, or translate. Those stay reserved extension points.

## 2. Non-goals (v1)

- Dual pane (original | Chinese) and any “split view” button
- Translation (MT API, LLM, or sidecar Chinese files)
- Format conversion between office/markdown/PDF
- HTML and image/OCR support
- Becoming the system default handler for Office or Markdown files
- macOS / Linux

Later phases (not implemented in v1, interfaces only):

- After preview and chrome are stable: add a dual-pane toggle
- Then: translation, preferring a dedicated MT API; LLM optional for hard passages; fallback to opening an existing Chinese file
- Then: conversion and HTML/image

## 3. Users and success

Primary user: the author, opening firmware/docs from Downloads and work folders.

v1 is successful when:

1. Double-clicking the desktop Reader icon opens an empty tabbed window.
2. `.docx` / `.pptx` / `.xlsx` / `.md` appear under Explorer right-click → Open with → Reader, without changing the default app.
3. Opening several mixed-format files (or dragging them) creates one tab each in the active window.
4. With Microsoft Office installed, Word/PowerPoint/Excel previews are visually close to native Office.
5. Without Office, the same files still open via built-in HTML preview; the status bar says “内置预览”.
6. Unsupported files show a short error; the app does not crash; other tabs keep working.

## 4. Architecture

Single Python process, Qt (PySide6) UI, embedded Chromium (Qt WebEngine) for HTML/PDF display.

```text
Explorer / Desktop / Drag-drop / argv
        │
        ▼
   App (single instance, AppUserModelID = Reader)
        │
        ├── MainWindow (tab strip + preview stack + status bar)
        │       └── DocumentTab (one file, one preview widget)
        │
        ├── PreviewPipeline (worker thread)
        │       ├── OfficeComPreview (Word/PPT/Excel COM → PDF or HTML)
        │       └── BuiltinPreview (docx/pptx/xlsx/md → HTML)
        │
        └── ShellIntegration
                ├── Desktop shortcut
                └── Per-user “Open with” ProgID for the four extensions
```

`App` owns windows and the single-instance lock. A second launch (icon click or “Open with”) does not start another process; it activates an existing window and, if paths were passed, opens them as new tabs in the active window.

`PreviewPipeline` is the only place that chooses Office vs builtin. Windows and tabs never talk to COM directly.

Office COM export and builtin parsing run on a worker thread. The UI thread only loads the resulting PDF/HTML into `QWebEngineView` (or a small error page).

## 5. Window and interaction model

Notepad (Windows 11) style:

- One `MainWindow` contains a tab bar and a preview area.
- Menu/shortcut **新建窗口** creates another `MainWindow` in the same process.
- Windows share one AppUserModelID so the taskbar shows a single Reader icon with grouped windows.
- Closing the last tab leaves an empty window (File → Open and drag-drop still work). Closing the last window exits the app.
- Drag-drop onto the window or tab bar: each supported file becomes a new tab; unsupported files get a toast/dialog and are skipped.
- PPT: previous/next slide (or scroll between slides).
- Excel: sheet switcher.
- Word and Markdown: vertical scroll.

No dual-pane control in v1.

## 6. Shell integration

- Desktop shortcut named `Reader`, targeting the installed/launcher executable, working directory set appropriately, custom icon.
- File association: register a ProgID `Reader.Document` (or per-type ProgIDs) for `.docx`, `.pptx`, `.xlsx`, `.md` under **HKCU** so they appear in “Open with”. Do not write `UserChoice` (do not steal defaults).
- First-run (or Settings → Repair association) writes the HKCU keys. If registration fails, Reader still runs from the shortcut and shows a non-blocking hint.
- Command line: `reader.exe [path ...]` opens each path as a tab. Zero paths → empty window. If an instance exists, paths are forwarded over a local socket/QLocalServer and the new process exits.

## 7. Preview pipeline

Supported extensions (case-insensitive): `.docx`, `.pptx`, `.xlsx`, `.md`.  
Reject: directories, missing files, `.doc` / `.ppt` / `.xls` legacy binary, `.pdf`, images, HTML.

Algorithm for a path:

1. Validate extension and that the file is readable.
2. If `.md`: always builtin Markdown → HTML (no Office).
3. If Office extension and COM for that app is available: export to PDF preferred, HTML if PDF export fails; load in WebEngine. Status: “Office 预览”.
4. If COM missing or export fails: builtin renderer → HTML. Status: “内置预览”.
5. If builtin fails: tab error page with the exception text; other tabs unchanged.

Temporary preview artifacts live under `%LOCALAPPDATA%\Reader\preview-cache\` keyed by path + mtime + size + strategy. Closing a tab may delete that tab’s temps; a cache cap (simple LRU, max 200 MB) prevents unbounded growth.

Builtin rendering intent (not pixel-identical to Office, but structured and readable):

- **docx:** headings, paragraphs, lists, tables, inline images as HTML
- **pptx:** one HTML section per slide, title + body + table text, images when extractable
- **xlsx:** sheet tabs in HTML; first N rows of the active sheet (N = 1000 in v1, with a notice if truncated); freeze-like header row repeated in the table header
- **md:** GitHub-flavored Markdown, fenced code, tables, mermaid left as code block in v1 (no mermaid render requirement)

Office path intent: visual closeness to native apps (fonts, layout, charts, shapes) via Office’s own export.

## 8. Module boundaries

| Unit | Responsibility | Depends on |
|------|----------------|------------|
| `reader.app` | QApplication, single instance, window list, AppUserModelID | shell, open |
| `reader.shell.window` | MainWindow, tabs, drag-drop, new window | open, preview widget |
| `reader.open` | Resolve paths, duplicate-tab policy (same path focuses existing tab in that window), forward to running instance | — |
| `reader.preview.pipeline` | Strategy selection, cache, worker jobs | office, formats |
| `reader.preview.office` | Detect COM, export docx/pptx/xlsx | pywin32 |
| `reader.formats.docx` | Builtin HTML | python-docx (and zip/XML as needed for images) |
| `reader.formats.pptx` | Builtin HTML | python-pptx |
| `reader.formats.xlsx` | Builtin HTML | openpyxl |
| `reader.formats.md` | Builtin HTML | markdown-it-py or mistune |
| `reader.shell.associate` | Shortcut + HKCU Open with | Windows APIs |
| `reader.ext.dual_pane` | Stub: not wired | — |
| `reader.ext.convert` | Stub: not wired | — |
| `reader.ext.translate` | Stub: not wired | — |

Each format module exposes the same function: `to_html(path: Path) -> PreviewResult` with `html: str` and optional `asset_dir`. Pipeline never imports UI.

## 9. Error handling

| Case | Behavior |
|------|----------|
| Unsupported extension | Message, no tab |
| File vanished / access denied / locked | Error page in a tab if already creating one; otherwise dialog |
| Office COM timeout or RPC busy | Fall back to builtin; log warning |
| Builtin empty or exception | Error page in that tab |
| Association write denied | App runs; settings hint |
| WebEngine fails to load PDF | Try HTML export; then builtin |

No crash dialogs from uncaught worker exceptions: they become tab error pages.

## 10. Testing strategy (TDD)

Framework: pytest, pytest-qt for GUI, unittest.mock for COM and registry.

Fixtures: copy a **small** representative set from `C:\Users\runqyang\Downloads` into `tests/fixtures/` (do not scan the whole Downloads tree in CI):

- Word: `Navi3x-dGPU-A-B-recovery-spec.docx` (or a trimmed copy if huge)
- PowerPoint: `AMD Server EDKII BIOS.pptx` (or smaller `eSID pre-SI AI Watchdog.pptx` if size is better)
- Markdown: `component-release-cross-component-scaling.md`
- Excel: one workbook from Downloads, plus a tiny generated `tests/fixtures/small.xlsx` for fast unit tests

Tests own the copies; original Downloads files stay untouched.

Red-green order:

1. Format sniff + reject list
2. Builtin `to_html` for each fixture contains expected substrings and is non-empty
3. Pipeline: mock COM present → office exporter called; mock COM absent → builtin; COM raises → builtin
4. Single-instance: second argv list is received by a fake server
5. Association: writing HKCU is invoked with expected ProgID (mock winreg)
6. pytest-qt: open a markdown fixture → one tab with that title
7. Office COM integration: `@pytest.mark.office`, skipped when Word/Excel/PowerPoint cannot be dispatched

Do not require Office on a machine that lacks it.

## 11. Tech stack

- Python 3.12+
- PySide6 (Qt widgets + WebEngine)
- pywin32 (COM, optional import if Office path unused in tests)
- python-docx, python-pptx, openpyxl
- markdown renderer (markdown-it-py)
- pytest, pytest-qt, pytest-mock
- Windows 10/11 only

Packaging (v1 may start as `python -m reader` plus a script that creates the shortcut; a frozen exe via PyInstaller is in scope once preview works).

## 12. Data and privacy

- Local files only; v1 makes no network calls.
- Preview cache is local and may contain exported PDF/HTML of opened documents; treat cache as sensitive as the source files.
- No telemetry.

## 13. Open decisions locked in this spec

- Preview fidelity: prefer Office, degrade to builtin (user choice C).
- Tabs plus optional new window; one taskbar icon.
- Conversion, dual pane, translation: out of v1.
- Translation later need not be an LLM; dedicated MT API first.
- TDD with Downloads-derived fixtures copied into the repo.

## 14. Risks

- Office COM on a worker thread can be unstable; if so, confine COM to a dedicated STA thread or a tiny helper process, still behind `reader.preview.office`.
- Large xlsx/pptx can freeze builtin HTML; enforce row/slide caps and show a truncation notice.
- WebEngine PDF plugin availability varies; HTML export is the documented fallback.
