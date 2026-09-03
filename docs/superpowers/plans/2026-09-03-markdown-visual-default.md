# Markdown Visual-Default Open Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. User asked to start in this session — execute inline without review gates.

**Goal:** Existing `.md` files open as read-only rendered preview; untitled stays editable; Ctrl+I / Ctrl+T toggle with force-save on Ctrl+T.

**Architecture:** Remove the `.md` text-editor short-circuit in `_start_preview`. Add Markdown-only `ApplicationShortcut` actions. Restore text with `editable=True`. Ctrl+T calls save then visual.

**Tech Stack:** PySide6, pytest-qt.

## Global Constraints

- Do not edit `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Do not bind Ctrl+I / Ctrl+T on PPTX tabs.
- Do not add title-bar/menu toggle buttons.
- Commit + push; update `docs/STATUS.md`.

---

### Task 1: Default existing `.md` open is visual

**Files:**
- Modify: `tests/test_window.py` (markdown open tests that assume text mode)
- Modify: `src/reader/shell/window.py` (`_start_preview`)

**Interfaces:**
- Consumes: existing visual `_start_preview` for `.pptx` / `.md` pipeline
- Produces: existing `.md` tabs start with `mode="visual"`; `_open_markdown_text_tab` unused for Open/drop/argv

- [ ] **Step 1: Write the failing tests**

Change `test_markdown_default_visual_mode_starts_without_pptx_telemetry` so open already uses visual:

```python
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    document = next(iter(window._documents.values()))
    assert document.mode == "visual"
    assert modes == ["visual"]
    visual.ready.emit(1)
    qtbot.wait(20)
    assert ready_calls == []
    assert markdown_calls == [str(path)]
```

Change `test_markdown_visual_skips_cache_get_and_put` so open (not a later switch) records `modes == ["visual"]` and `cache.calls == []`.

Change `test_office_action_is_disabled_for_non_office_suffix` to wait for `tab_count() == 1` instead of `MarkdownTextView`.

Keep untitled tests that look for `MarkdownTextView` after `add_untitled_markdown_tab()`.

Wikilink / close-tab markdown tests: after `open_paths`, `waitUntil(visual.start_calls == 1)` without requiring `switch_current_tab_to_visual()` first.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_window.py::test_markdown_default_visual_mode_starts_without_pptx_telemetry tests/test_window.py::test_markdown_visual_skips_cache_get_and_put tests/test_window.py::test_office_action_is_disabled_for_non_office_suffix -v`

Expected: FAIL (`mode == "text"` or `MarkdownTextView` still used / `modes == []`).

- [ ] **Step 3: Minimal implementation**

In `_start_preview`, delete the `.md` branch that calls `_open_markdown_text_tab`. Existing `.md` files use `initial_mode = "visual"` like PPTX.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_window.py::test_markdown_default_visual_mode_starts_without_pptx_telemetry tests/test_window.py::test_markdown_visual_skips_cache_get_and_put tests/test_window.py::test_office_action_is_disabled_for_non_office_suffix tests/test_window.py::test_markdown_wikilink_open_path_opens_tab_and_dedupes_focus tests/test_window.py::test_untitled_editor_starts_flush_under_title_chrome -v`

Expected: PASS. Untitled still uses the editor.

- [ ] **Step 5: Commit**

```text
fix: open existing markdown files in read-only visual preview
```

---

### Task 2: Ctrl+I / Ctrl+T with force-save

**Files:**
- Modify: `tests/test_window.py` (new shortcut tests)
- Modify: `src/reader/shell/window.py` (actions, `_restore_markdown_text`, visual switch)
- Modify: `tests/test_packaging.py` only if it asserts window.py strings that this changes

**Interfaces:**
- Consumes: `save_current_tab()`, `_restore_markdown_text`, `_restart_preview`
- Produces: `actionMarkdownEdit` (`Ctrl+I`), `actionMarkdownPreview` (`Ctrl+T`), `_ensure_markdown_saved() -> bool`

- [ ] **Step 1: Write the failing tests**

```python
def test_ctrl_i_switches_markdown_visual_to_editable_text(qtbot, tmp_path: Path):
    from PySide6.QtGui import QKeySequence
    from reader.preview.md_text_view import MarkdownTextView
    from reader.shell.window import MainWindow

    path = tmp_path / "note.md"
    path.write_text("hello", encoding="utf-8")
    visual = FakeMarkdownVisual()
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: markdown_visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: visual,
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    assert window.actionMarkdownEdit.shortcut() == QKeySequence("Ctrl+I")
    window.actionMarkdownEdit.trigger()
    qtbot.waitUntil(lambda: window.findChild(MarkdownTextView) is not None)
    view = window.findChild(MarkdownTextView)
    assert view is not None
    assert view.is_editable() is True
    assert view.text() == "hello"


def test_ctrl_t_force_saves_dirty_markdown_then_shows_visual(qtbot, tmp_path: Path):
    from reader.preview.md_text_view import MarkdownTextView
    from reader.shell.window import MainWindow

    path = tmp_path / "note.md"
    path.write_text("hello", encoding="utf-8")
    visuals = iter((FakeMarkdownVisual(), FakeMarkdownVisual()))
    window = MainWindow(
        preview_fn=lambda *_args, **_kwargs: markdown_visual_result(),
        cache_factory=FakeCache,
        viewer_factory=lambda *_args: next(visuals),
    )
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    window.actionMarkdownEdit.trigger()
    qtbot.waitUntil(lambda: window.findChild(MarkdownTextView) is not None)
    view = window.findChild(MarkdownTextView)
    view._editor.setPlainText("changed")
    window.actionMarkdownPreview.trigger()
    qtbot.waitUntil(lambda: window.findChild(MarkdownTextView) is None)
    assert path.read_text(encoding="utf-8") == "changed"
    document = next(iter(window._documents.values()))
    assert document.mode == "visual"


def test_ctrl_t_cancelled_save_as_keeps_untitled_editor(qtbot, tmp_path: Path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from reader.preview.md_text_view import MarkdownTextView

    window = make_window(lambda *_args, **_kwargs: markdown_visual_result())
    qtbot.addWidget(window)
    window.add_untitled_markdown_tab()
    view = window.findChild(MarkdownTextView)
    view._editor.setPlainText("draft")
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *_args, **_kwargs: ("", "")
    )
    window.actionMarkdownPreview.trigger()
    assert window.findChild(MarkdownTextView) is view
    assert view.text() == "draft"


def test_ctrl_i_and_ctrl_t_do_not_toggle_pptx(qtbot, tmp_path: Path):
    path = tmp_path / "deck.pptx"
    path.write_bytes(b"x")
    visual = FakeVisual()
    window = MainWindow(...)  # same pattern as other pptx visual tests
    qtbot.addWidget(window)
    window.open_paths([str(path)])
    qtbot.waitUntil(lambda: visual.start_calls == 1)
    window.actionMarkdownEdit.trigger()
    window.actionMarkdownPreview.trigger()
    document = next(iter(window._documents.values()))
    assert document.mode == "visual"
    assert visual.start_calls == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_window.py::test_ctrl_i_switches_markdown_visual_to_editable_text tests/test_window.py::test_ctrl_t_force_saves_dirty_markdown_then_shows_visual tests/test_window.py::test_ctrl_t_cancelled_save_as_keeps_untitled_editor tests/test_window.py::test_ctrl_i_and_ctrl_t_do_not_toggle_pptx -v`

Expected: FAIL (`actionMarkdownEdit` missing or restore still read-only / dirty switch aborts).

- [ ] **Step 3: Minimal implementation**

Add `actionMarkdownEdit` / `actionMarkdownPreview` with `QKeySequence("Ctrl+I")` / `QKeySequence("Ctrl+T")` and `Qt.ShortcutContext.ApplicationShortcut`. Enable only when the current document suffix is `.md`.

```python
def _ensure_markdown_saved(self) -> bool:
    from reader.preview.md_text_view import MarkdownTextView

    document_id = self._current_document_id()
    if document_id is None:
        return False
    document = self._documents[document_id]
    view = document.page.findChild(MarkdownTextView)
    if view is None:
        return document.path.exists()
    if view.path is None or view.dirty:
        self.save_current_tab()
        view = document.page.findChild(MarkdownTextView)
        if view is None or view.path is None or view.dirty:
            return False
    return True
```

`switch_current_tab_to_visual` for `.md`: if `_ensure_markdown_saved()` is False, return; else `_restart_preview(..., "visual")`.

`_restore_markdown_text(..., *, editable: bool = True)` and `load_path(..., editable=editable)`.

Ctrl+I handler: if current `.md` and not text, `_restore_markdown_text`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_window.py::test_ctrl_i_switches_markdown_visual_to_editable_text tests/test_window.py::test_ctrl_t_force_saves_dirty_markdown_then_shows_visual tests/test_window.py::test_ctrl_t_cancelled_save_as_keeps_untitled_editor tests/test_window.py::test_ctrl_i_and_ctrl_t_do_not_toggle_pptx tests/test_window.py::test_caption_press_on_main_window_starts_system_move tests/test_window.py::test_window_buttons_are_client_hits_and_clickable tests/test_title_chrome.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: toggle markdown preview and editor with Ctrl+I and Ctrl+T
```

---

### Task 3: Frozen certify

**Files:** `docs/STATUS.md`; `scripts/smoke_windows.ps1` (comment that product default is now visual)

- [ ] Full `python -m pytest`
- [ ] `scripts/build_windows.ps1` then `scripts/smoke_windows.ps1`
- [ ] Refresh desktop `Reader.lnk` with `overwrite=True`
- [ ] Update STATUS (goal completed; next step = open `.md` is preview, `+` is edit, Ctrl+I/T)
- [ ] Commit + push `origin/main`
