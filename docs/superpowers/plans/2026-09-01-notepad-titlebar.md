# Notepad-Style Title Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Reader’s system title bar + menu bar + tab-corner Open/+ cluster with a single Notepad-like chrome row (icon | tabs | + | caption | min/max/close) while keeping Ctrl+O, drag-drop, preview actions, and native Windows snap/resize.

**Architecture:** Keep `MainWindow` document/tab lifecycle on `QTabWidget`, but reparent its `QTabBar` into a new `TitleChrome` row. Make the window frameless and answer `WM_NCHITTEST` / `WM_NCCALCSIZE` so caption drag, edge resize, double-click maximize, and Win11 Snap Layouts on the maximize button keep working. Hide the menu bar; keep `QAction`s for Open/NewTab/preview.

**Tech Stack:** Python 3.12+, PySide6 Qt Widgets, ctypes Win32 messages, pytest-qt, existing PyInstaller onedir smoke.

## Global Constraints

- One chrome row only: icon | tabs | + | caption stretch | min | max | close.
- No visible 文件 / 预览 menu; no `tabOpenButton`.
- `+` (`tabNewButton`) always visible immediately after the last tab; click / `actionNewTab` → blank `未命名`.
- Blank hint: `拖入文件，或按 Ctrl+O 打开`.
- Keep `actionOpen` (`QKeySequence.Open`), drag-drop, Explorer Open with, preview `QAction`s (hidden).
- Default size 1200×800, minimum 800×500; status bar stays.
- Windows-only custom title bar; do not change PPTX/Markdown viewers or IPC.
- Commit and push `origin/main` at each task boundary; update `docs/STATUS.md`.

---

## File Structure

- Create: `src/reader/shell/title_chrome.py` — `TitleChrome` widget (icon, tab-bar host, +, caption stretch, window buttons) and Win32 hit-test helpers.
- Create: `tests/test_title_chrome.py` — chrome layout + synthetic `WM_NCHITTEST` coverage.
- Modify: `src/reader/shell/window.py` — frameless setup, install chrome, hide menus, remove corner Open, new blank hint.
- Modify: `tests/test_window.py` — blank hint string; chrome regression (no menu / no open button / + after tabs).
- Modify: `docs/STATUS.md` — progress after each task.
- Optional touch: `docs/superpowers/specs/2026-09-01-notepad-titlebar-design.md` status → Implemented when done.

---

### Task 1: Hide menus, drop Open button, update blank hint

**Files:**
- Modify: `src/reader/shell/window.py`
- Modify: `tests/test_window.py`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Consumes: existing `MainWindow`, `actionOpen`, `actionNewTab`, preview actions, `_build_tab_controls`.
- Produces: no visible menu actions; no `tabOpenButton`; blank hint `拖入文件，或按 Ctrl+O 打开`; `tabNewButton` still present (corner or chrome — Task 2 moves it).

- [ ] **Step 1: Write failing chrome / hint tests**

Append to `tests/test_window.py`:

```python
def test_chrome_hides_menu_and_open_button(qtbot):
    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    assert window.menuBar().isVisible() is False
    assert window.findChild(QWidget, "tabOpenButton") is None
    plus = window.findChild(QWidget, "tabNewButton")
    assert plus is not None
    assert plus.isEnabled()


def test_plus_action_adds_blank_tab_with_drop_hint(qtbot):
    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)

    window.actionNewTab.trigger()

    assert window.tab_count() == 1
    assert window.tab_title(0) == "未命名"
    assert "拖入文件，或按 Ctrl+O 打开" in page_text(window, 0)
    assert window.focus_path() is None
```

Update the existing `test_plus_action_adds_blank_tab_with_drop_hint` hint assertion (replace the old `文件 → 打开` string). Keep `test_open_action_uses_multi_select_and_adds_tabs` and shortcut asserts unchanged.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_window.py::test_chrome_hides_menu_and_open_button tests/test_window.py::test_plus_action_adds_blank_tab_with_drop_hint -v`

Expected: FAIL — menu still visible and/or `tabOpenButton` exists and/or hint still says `文件 → 打开`.

- [ ] **Step 3: Minimal implementation**

In `MainWindow.__init__`:

1. After creating actions, **do not** `menuBar().addMenu(...)`. Instead:
   - `self.addAction(self.actionOpen)` / `self.addAction(self.actionNewTab)` / same for NewWindow and preview actions so shortcuts and tests still find them.
   - `self.menuBar().setVisible(False)` (and `setMaximumHeight(0)` if needed so layout collapses).
2. In `_build_tab_controls`, remove the Open `QToolButton`; keep only `tabNewButton` connected to `add_blank_tab`.
3. In `add_blank_tab`, set hint text to `拖入文件，或按 Ctrl+O 打开`.

Keep `actionNewWindow` as a window action (no visible menu).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_window.py::test_chrome_hides_menu_and_open_button tests/test_window.py::test_plus_action_adds_blank_tab_with_drop_hint tests/test_window.py::test_open_action_uses_multi_select_and_adds_tabs tests/test_window.py::test_ux_packaging_regression_multi_open_duplicate_blank_and_office_failure -v`

Expected: PASS

- [ ] **Step 5: Commit and push**

```powershell
git add src/reader/shell/window.py tests/test_window.py docs/STATUS.md
git commit -m "feat: hide menu chrome and drop tab Open button"
git push origin main
```

Update STATUS: Task 1 done; next Task 2.

---

### Task 2: Single-row TitleChrome with icon, tabs, and +

**Files:**
- Create: `src/reader/shell/title_chrome.py`
- Modify: `src/reader/shell/window.py`
- Modify: `tests/test_window.py`
- Create/Modify: `tests/test_title_chrome.py`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Consumes: `MainWindow._tabs: QTabWidget`, window icon.
- Produces:
  - `class TitleChrome(QWidget)` with object names:
    - `titleChrome`, `titleAppIcon`, `titleTabHost`, `tabNewButton`, `titleCaption`, `titleMinButton`, `titleMaxButton`, `titleCloseButton` (buttons may be stubs until Task 3)
  - `TitleChrome.adopt_tab_bar(tab_bar: QTabBar) -> None`
  - `TitleChrome.set_plus_handler(callback) -> None`
  - Layout order: icon | tab bar | + | caption stretch | (optional buttons)

- [ ] **Step 1: Write failing layout tests**

```python
# tests/test_title_chrome.py
from PySide6.QtWidgets import QTabBar, QTabWidget

def test_title_chrome_orders_icon_tabs_plus_caption(qtbot):
    from reader.shell.title_chrome import TitleChrome

    chrome = TitleChrome()
    qtbot.addWidget(chrome)
    tabs = QTabWidget()
    tabs.addTab(QWidget(), "a.md")
    chrome.adopt_tab_bar(tabs.tabBar())
    chrome.show()
    qtbot.waitExposed(chrome)

    icon = chrome.findChild(QWidget, "titleAppIcon")
    host = chrome.findChild(QWidget, "titleTabHost")
    plus = chrome.findChild(QWidget, "tabNewButton")
    caption = chrome.findChild(QWidget, "titleCaption")
    assert icon is not None and plus is not None and caption is not None
    assert icon.x() < host.x() < plus.x() < caption.x()
```

```python
# tests/test_window.py
def test_plus_button_follows_last_tab_not_far_right_corner(qtbot):
    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)
    window.resize(1200, 800)
    window.show()
    qtbot.waitExposed(window)
    window.actionNewTab.trigger()

    plus = window.findChild(QWidget, "tabNewButton")
    tab_bar = window._tabs.tabBar()
    assert plus is not None
    # + must be near the tab bar, not pinned to the window's far right
    plus_global = plus.mapTo(window, plus.rect().center())
    tab_right = tab_bar.mapTo(window, QPoint(tab_bar.width(), tab_bar.height() // 2))
    assert abs(plus_global.x() - tab_right.x()) < 80
    assert plus_global.x() < window.width() - 120
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_title_chrome.py::test_title_chrome_orders_icon_tabs_plus_caption tests/test_window.py::test_plus_button_follows_last_tab_not_far_right_corner -v`

Expected: FAIL — `TitleChrome` missing and/or + still in far-right corner widget.

- [ ] **Step 3: Implement TitleChrome and wire MainWindow**

`title_chrome.py` sketch:

```python
class TitleChrome(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("titleChrome")
        self.setFixedHeight(36)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 0, 0)
        row.setSpacing(4)

        self._icon = QLabel(self)
        self._icon.setObjectName("titleAppIcon")
        self._icon.setFixedSize(16, 16)
        self._icon.setScaledContents(True)
        row.addWidget(self._icon, 0, Qt.AlignmentFlag.AlignVCenter)

        self._tab_host = QWidget(self)
        self._tab_host.setObjectName("titleTabHost")
        self._tab_host_layout = QHBoxLayout(self._tab_host)
        self._tab_host_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_host_layout.setSpacing(0)
        row.addWidget(self._tab_host, 0, Qt.AlignmentFlag.AlignVCenter)

        self._plus = QToolButton(self)
        self._plus.setObjectName("tabNewButton")
        self._plus.setText("+")
        self._plus.setAutoRaise(True)
        row.addWidget(self._plus, 0, Qt.AlignmentFlag.AlignVCenter)

        self._caption = QWidget(self)
        self._caption.setObjectName("titleCaption")
        self._caption.setMinimumWidth(24)
        row.addWidget(self._caption, 1)

        # Window buttons added in Task 3; reserve empty trailing layout or placeholders.

    def set_window_icon(self, icon: QIcon) -> None:
        self._icon.setPixmap(icon.pixmap(16, 16))

    def adopt_tab_bar(self, tab_bar: QTabBar) -> None:
        tab_bar.setParent(self._tab_host)
        self._tab_host_layout.addWidget(tab_bar)
        tab_bar.show()

    def set_plus_handler(self, callback) -> None:
        self._plus.clicked.connect(callback)
```

In `MainWindow.__init__`:

1. Build `self._tabs` as today (closable, signals).
2. Create `self._title_chrome = TitleChrome(self)`.
3. `self._title_chrome.set_window_icon(self.windowIcon())` (or after icon is set).
4. `self._title_chrome.adopt_tab_bar(self._tabs.tabBar())`.
5. `self._title_chrome.set_plus_handler(self.add_blank_tab)`.
6. Stop calling `setCornerWidget` / delete `_build_tab_controls`.
7. Central widget becomes a container:

```python
container = QWidget(self)
root = QVBoxLayout(container)
root.setContentsMargins(0, 0, 0, 0)
root.setSpacing(0)
root.addWidget(self._title_chrome)
root.addWidget(self._tabs, 1)
self.setCentralWidget(container)
```

Style lightly so selected tabs look like rounded pills (stylesheet on `QTabBar::tab:selected`). Do not add window buttons yet if Task 3 is separate — but keep caption stretch.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_title_chrome.py tests/test_window.py::test_chrome_hides_menu_and_open_button tests/test_window.py::test_plus_action_adds_blank_tab_with_drop_hint tests/test_window.py::test_plus_button_follows_last_tab_not_far_right_corner -v`

Expected: PASS

- [ ] **Step 5: Commit and push**

```powershell
git add src/reader/shell/title_chrome.py src/reader/shell/window.py tests/test_title_chrome.py tests/test_window.py docs/STATUS.md
git commit -m "feat: put tabs and plus on single title chrome row"
git push origin main
```

---

### Task 3: Frameless window + caption buttons

**Files:**
- Modify: `src/reader/shell/title_chrome.py`
- Modify: `src/reader/shell/window.py`
- Modify: `tests/test_title_chrome.py`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Produces: `titleMinButton` / `titleMaxButton` / `titleCloseButton` with clicks → `showMinimized` / toggle maximize / `close`.
- `MainWindow` uses `Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint` (preserve WindowMinimizeButtonHint behavior via custom buttons).
- `TitleChrome.update_maximize_state(is_maximized: bool)` toggles max button glyph.

- [ ] **Step 1: Write failing button tests**

```python
def test_title_chrome_window_buttons_exist(qtbot):
    from reader.shell.title_chrome import TitleChrome
    chrome = TitleChrome()
    qtbot.addWidget(chrome)
    for name in ("titleMinButton", "titleMaxButton", "titleCloseButton"):
        assert chrome.findChild(QWidget, name) is not None


def test_frameless_main_window_has_custom_chrome_buttons(qtbot):
    window = make_window(lambda _path, office=None, mode="builtin": builtin_result())
    qtbot.addWidget(window)
    assert bool(window.windowFlags() & Qt.WindowType.FramelessWindowHint)
    assert window.findChild(QWidget, "titleCloseButton") is not None
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_title_chrome.py::test_title_chrome_window_buttons_exist tests/test_window.py::test_frameless_main_window_has_custom_chrome_buttons -v`

Expected: FAIL

- [ ] **Step 3: Implement buttons + frameless flag**

Add three `QToolButton`s at the end of `TitleChrome` row (after caption). Wire from `MainWindow`:

```python
chrome.min_clicked -> self.showMinimized
chrome.max_clicked -> self.showNormal if maximized else showMaximized
chrome.close_clicked -> self.close
```

Listen to `QEvent.WindowStateChange` on `MainWindow` to refresh max button. Apply compact stylesheet (close hover red). Keep height 32–36px.

Set flags early in `__init__` before show:

```python
self.setWindowFlags(
    Qt.WindowType.Window
    | Qt.WindowType.FramelessWindowHint
)
```

- [ ] **Step 4: Run focused + window smoke subset**

Run: `python -m pytest tests/test_title_chrome.py tests/test_window.py::test_frameless_main_window_has_custom_chrome_buttons tests/test_window.py::test_chrome_hides_menu_and_open_button tests/test_window.py::test_plus_button_follows_last_tab_not_far_right_corner -v`

Expected: PASS

- [ ] **Step 5: Commit and push**

```powershell
git commit -m "feat: frameless window with custom caption buttons"
git push origin main
```

---

### Task 4: Native WM_NCHITTEST / resize / Snap Layouts

**Files:**
- Modify: `src/reader/shell/title_chrome.py` (hit-rect helpers)
- Modify: `src/reader/shell/window.py` (`nativeEvent`)
- Modify: `tests/test_title_chrome.py`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Produces:
  - `BORDER = 8` (physical/device px; scale with `devicePixelRatioF` as needed)
  - `def hit_test(window: MainWindow, global_pos: QPoint) -> int` returning Win32 HT* codes
  - `MainWindow.nativeEvent` handles `WM_NCHITTEST` and `WM_NCCALCSIZE` when frameless

Hit map:
- Outer border (not maximized) → `HTLEFT`/`HTRIGHT`/`HTTOP`/`HTBOTTOM` and corners
- Over `titleCaption` → `HTCAPTION`
- Over `titleMinButton` → `HTMINBUTTON`
- Over `titleMaxButton` → `HTMAXBUTTON` (required for Win11 Snap Layouts)
- Over `titleCloseButton` → `HTCLOSE`
- Over icon / tab bar / + / content → `HTCLIENT`

When returning `HTMINBUTTON`/`HTMAXBUTTON`/`HTCLOSE`, still let Qt buttons receive clicks OR handle `WM_NCLBUTTONDOWN` — prefer returning HT* for hover/snap and keep buttons as real Qt widgets with `HTCLIENT` only if Snap Layouts still appear. Spec requires maximize hover → `HTMAXBUTTON`; implement that even if click routing uses non-client messages (`WM_NCLBUTTONDOWN` → `ShowWindow` / `close`). Practical approach used by many Qt apps: return HT* for those three buttons and also connect Qt clicked as fallback; if double-handling occurs, disable Qt click and handle NC button messages.

Recommended minimal approach that satisfies Snap Layouts:
1. Maximize button region returns `HTMAXBUTTON` from `WM_NCHITTEST`.
2. Handle `WM_NCLBUTTONDOWN` / `WM_NCLBUTTONUP` for min/max/close OR rely on DefWindowProc.
3. Caption returns `HTCAPTION` so drag and double-click maximize work via DefWindowProc.

- [ ] **Step 1: Write synthetic hit-test tests**

```python
def test_hit_test_regions(qtbot):
    window = make_window(...)
    qtbot.addWidget(window)
    window.resize(1200, 800)
    window.show()
    qtbot.waitExposed(window)

    from reader.shell.title_chrome import (
        HTCLIENT, HTCAPTION, HTMAXBUTTON, HTLEFT, hit_test_for_window,
    )

    caption = window.findChild(QWidget, "titleCaption")
    max_btn = window.findChild(QWidget, "titleMaxButton")
    # center of caption -> HTCAPTION
    assert hit_test_for_window(window, caption.mapToGlobal(caption.rect().center())) == HTCAPTION
    assert hit_test_for_window(window, max_btn.mapToGlobal(max_btn.rect().center())) == HTMAXBUTTON
    # content below chrome
    content_pt = window.mapToGlobal(QPoint(window.width() // 2, 200))
    assert hit_test_for_window(window, content_pt) == HTCLIENT
    # left edge
    edge = window.mapToGlobal(QPoint(1, window.height() // 2))
    assert hit_test_for_window(window, edge) == HTLEFT
```

- [ ] **Step 2: Run to verify fail**

Expected: FAIL — helper / nativeEvent missing.

- [ ] **Step 3: Implement hit testing**

Use `ctypes.wintypes.MSG` in `nativeEvent` when `eventType in (b"windows_generic_MSG", "windows_generic_MSG")`. Decode `lParam` screen coordinates for `WM_NCHITTEST`. Call `hit_test_for_window`. Return `(True, ht_code)`.

For `WM_NCCALCSIZE` with `wParam == True`, return `0` so the client covers the full frame (standard frameless pattern).

Disable resize HT* when `window.isMaximized()`.

- [ ] **Step 4: Run focused tests + a broader window slice**

Run: `python -m pytest tests/test_title_chrome.py tests/test_window.py -k "chrome or plus_action or frameless or hit_test or ux_packaging_regression" -v`

Expected: PASS

- [ ] **Step 5: Commit and push**

```powershell
git commit -m "feat: native hit-test for caption drag resize and snap"
git push origin main
```

---

### Task 5: Full regression, frozen build, smoke, desktop shortcut

**Files:**
- Modify: `docs/STATUS.md`
- Modify: `docs/superpowers/specs/2026-09-01-notepad-titlebar-design.md` (status → Implemented)
- Possibly no code if green

- [ ] **Step 1: Full pytest**

Run: `python -m pytest -v`

Expected: all previously green counts still pass (Markdown/PPTX suites unchanged). Fix any fallout from frameless/tab-bar reparenting.

- [ ] **Step 2: Rebuild frozen Reader**

Run: `powershell -File scripts/build_windows.ps1`

Expected: exit 0; `dist/Reader/Reader.exe` exists.

- [ ] **Step 3: Frozen smoke**

Run: `powershell -File scripts/smoke_windows.ps1`

Expected: PPTX visual-ready, Markdown ready, IPC batches succeed.

- [ ] **Step 4: Refresh desktop shortcut**

```powershell
python -c "from pathlib import Path; from reader.shell.associate import create_desktop_shortcut; exe=Path('dist/Reader/Reader.exe').resolve(); create_desktop_shortcut(exe, icon=exe); print(exe)"
```

Verify `Reader.lnk` target/workdir/icon.

- [ ] **Step 5: Final STATUS + commit + push**

Mark current goal completed; next steps = manual Notepad-chrome visual check on desktop Reader. Commit message: `test: certify notepad title bar in frozen Reader`. Push `origin/main`.

---

## Spec coverage checklist

| Spec requirement | Task |
|---|---|
| Single row icon/tabs/+/caption/buttons | 2, 3 |
| Remove menu + Open button | 1 |
| + after last tab, always blank tab | 1, 2 |
| Ctrl+O / drag-drop preserved | 1 (actions) |
| Preview actions kept, not visible | 1 |
| Blank hint Ctrl+O text | 1 |
| Frameless + native drag/resize/snap | 3, 4 |
| Frozen smoke + shortcut | 5 |
| No PPTX/MD viewer changes | all |

## Placeholder scan

No TBD/TODO steps; each task has concrete tests, commands, and implementation sketches.
