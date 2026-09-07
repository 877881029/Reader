# Native PDF Reading Design

Date: 2026-09-07  
Status: Approved by user (Chrome-style WebEngine viewer; continuous execute)  
Depends on: v1 preview pipeline + existing `kind="pdf"` WebEngine load path  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Reader opens native `.pdf` files as first-class, **read-only** tabs using Chromium’s built-in PDF viewer (same WebEngine path already used for Office-exported PDFs).

Users can open PDFs via drag-and-drop, `Ctrl+O`, argv/IPC, and Windows Open With.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`. No PDF editing. No sidebar thumbnails/bookmarks UI.

## 2. Current behavior

`sniff` rejects `.pdf` (`unsupported_extension`). PDF `PreviewResult`s exist only as Office COM export artifacts, which `_pin_pdf` copies into a temp dir before `QWebEngineView.load`.

## 3. Architecture

- Add `.pdf` to `SUPPORTED_EXTENSIONS` and `associate.EXTENSIONS`.
- `reader.formats.pdf.to_preview(path)` returns `PreviewResult(kind="pdf", pdf_path=resolved source, html="", status_label="内置预览", asset_dir=None)`.
- Pipeline: `.pdf` returns that result for any mode (builtin/visual/text/office). Do not call Office COM.
- `_pin_pdf`: if `kind=="pdf"` and `asset_dir is None`, return the result **without copying**. Office exports keep `asset_dir` and still pin.
- Preview worker: skip cache get/put for `.pdf` (do not duplicate large user files).
- `_default_viewer` already loads `result.pdf_path` in `QWebEngineView`. Keep that.
- Open dialog filter includes `*.pdf`.
- Unsupported-file tests that used `bad.pdf` switch to another suffix (e.g. `.exe`).

## 4. Non-goals

- Custom chrome PDF toolbar, outline, annotations, or print menu of our own.
- Changing Office-export PDF pinning.
- Markdown/PPTX mode shortcuts on PDF tabs.

## 5. Testing

- sniff accepts `.pdf` / `.PDF`.
- `decide_open` opens a real `.pdf`; rejects `.exe`.
- `preview(pdf)` returns `kind="pdf"` and `pdf_path` is the source; `mode="visual"` does not raise.
- Opening a `.pdf` tab uses the source path (no temp `preview.pdf` pin); `artifact_dir` is None.
- Open With registers `.pdf`.
- Existing Office PDF pin tests stay green.
- Caption-move / min-max click tests stay green.
