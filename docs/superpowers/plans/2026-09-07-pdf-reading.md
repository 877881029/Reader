# Native PDF Reading Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. User asked to start in this session — execute inline without review gates.

**Goal:** Open native `.pdf` files as read-only Chromium PDF tabs.

**Architecture:** Add `.pdf` to sniff/open/association. New `formats.pdf.to_preview` returns `kind="pdf"` pointing at the source file. Skip pin/cache copies when `asset_dir is None`. Reuse existing WebEngine PDF load.

**Tech Stack:** PySide6, pytest-qt.

## Global Constraints

- Do not edit `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Do not copy user PDFs; Office-exported PDFs still pin.
- Do not bind Ctrl+I / Ctrl+T on PDF tabs.
- Commit + push; update `docs/STATUS.md`.

---

### Task 1: Sniff, pipeline, Open With

**Files:**
- Create: `src/reader/formats/pdf.py`, `tests/test_formats_pdf.py`
- Modify: `src/reader/sniff.py`, `src/reader/preview/pipeline.py`, `src/reader/shell/associate.py`
- Modify: `tests/test_sniff.py`, `tests/test_open.py`, `tests/test_pipeline.py`, `tests/test_associate.py`

**Interfaces:**
- Produces: `to_preview(path: Path) -> PreviewResult`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_formats_pdf.py
def test_to_preview_points_at_source_without_asset_dir(tmp_path: Path):
    from reader.formats.pdf import to_preview

    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4\n")
    result = to_preview(path)
    assert result.kind == "pdf"
    assert result.status_label == "内置预览"
    assert result.pdf_path == path.resolve()
    assert result.asset_dir is None
    assert result.html == ""
```

Update sniff supported set to include `.pdf`; parametrize `("e.PDF", ".pdf")`; replace `test_sniff_rejects_pdf` with accept.

`test_rejected_items_keep_reason_and_order`: reject `.exe` instead of `.pdf`; add `test_opens_pdf`.

`test_unsupported_raises`: use `x.exe`. Add `test_pdf_preview_uses_source_path` calling `preview(path)` and `preview(path, mode="visual")`.

Associate: `EXTENSIONS == (".docx", ".pptx", ".xlsx", ".md", ".pdf")`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_formats_pdf.py tests/test_sniff.py tests/test_open.py tests/test_pipeline.py::test_unsupported_raises tests/test_pipeline.py::test_pdf_preview_uses_source_path tests/test_associate.py::test_register_open_with_hkcu_classes_only_and_close_keys -v`

Expected: FAIL (`.pdf` still unsupported / module missing).

- [ ] **Step 3: Minimal implementation**

`to_preview` as above. Pipeline:

```python
from reader.formats import pdf as fmt_pdf

    suffix = sniff(path)
    if suffix == ".pdf":
        return fmt_pdf.to_preview(path)
```

Add `.pdf` to `SUPPORTED_EXTENSIONS` and `EXTENSIONS`.

- [ ] **Step 4: Run tests to verify they pass**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: accept native PDF files in sniff, preview, and Open With
```

---

### Task 2: Open in place (no pin) + dialog

**Files:**
- Modify: `src/reader/shell/window.py` (`_pin_pdf`, `_PreviewWorker` cache skip, open dialog filter)
- Modify: `tests/test_window.py` (unsupported examples + native open test)

**Interfaces:**
- Consumes: `to_preview` / `kind="pdf"` with `asset_dir is None`
- Produces: native PDF tabs load source path; `artifact_dir is None`

- [ ] **Step 1: Write the failing tests**

Change `test_unsupported_is_nonblocking_and_does_not_add_tab` and `test_unsupported_drop_keeps_blank_tab` to use `bad.exe`.

```python
def test_native_pdf_opens_source_without_pinning(qtbot, tmp_path: Path):
    from reader.shell.window import MainWindow

    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4\n")
    viewed: list[Path] = []

    def preview_fn(source: Path, office=None, mode="builtin") -> PreviewResult:
        return PreviewResult(
            html="",
            status_label="内置预览",
            kind="pdf",
            pdf_path=source.resolve(),
        )

    def viewer(result: PreviewResult, _source: Path) -> QLabel:
        assert result.pdf_path is not None
        viewed.append(result.pdf_path)
        label = QLabel(result.pdf_path.name)
        label.setObjectName("previewContent")
        return label

    window = MainWindow(
        preview_fn=preview_fn,
        cache_factory=FakeCache,
        viewer_factory=viewer,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: window.tab_count() == 1)
    qtbot.waitUntil(lambda: viewed != [])
    assert viewed[0] == path.resolve()
    document = next(iter(window._documents.values()))
    assert document.artifact_dir is None
    assert "doc.pdf" in window.tab_title(0)
```

Assert `_open_dialog` filter contains `*.pdf` (read the call via monkeypatch recording args, or a tiny unit that inspects the filter string in window.py via opening dialog mock):

```python
def test_open_dialog_filter_includes_pdf(qtbot, monkeypatch):
    captured: list[str] = []
    window = make_window(lambda *_a, **_k: builtin_result())
    qtbot.addWidget(window)
    monkeypatch.setattr(
        "reader.shell.window.QFileDialog.getOpenFileNames",
        lambda *_args, **kwargs: captured.append(_args[3] if len(_args) > 3 else kwargs.get("filter", "")) or ([], ""),
    )
    window._open_dialog()
    assert captured and "*.pdf" in captured[0]
```

(Adjust to however Qt passes the filter positional arg: parent, caption, dir, filter.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_window.py::test_native_pdf_opens_source_without_pinning tests/test_window.py::test_unsupported_is_nonblocking_and_does_not_add_tab tests/test_window.py::test_open_dialog_filter_includes_pdf -v`

Expected: FAIL (PDF still pinned to temp or filter missing). After Task 1, unsupported `.pdf` tests would open a tab — they must already be switched to `.exe` in this step’s test edits before implementation, so they stay green.

- [ ] **Step 3: Minimal implementation**

`_pin_pdf`: if `kind=="pdf"` and `asset_dir is None`, `return _WorkerOutput(result)`.

Worker: skip cache when `self.path.suffix.lower() == ".pdf"`.

Open filter: `Documents (*.docx *.pptx *.xlsx *.md *.pdf)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_window.py::test_native_pdf_opens_source_without_pinning tests/test_window.py::test_pdf_is_pinned_until_tab_closes tests/test_window.py::test_unsupported_drop_keeps_blank_tab tests/test_window.py::test_caption_press_on_main_window_starts_system_move tests/test_window.py::test_window_buttons_are_client_hits_and_clickable tests/test_title_chrome.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: open native PDFs in Chromium viewer without copying
```

---

### Task 3: Frozen certify

- [ ] Full `python -m pytest`
- [ ] `scripts/build_windows.ps1` then `scripts/smoke_windows.ps1`
- [ ] Refresh desktop `Reader.lnk` with `overwrite=True`
- [ ] Update STATUS; commit + push `origin/main`
