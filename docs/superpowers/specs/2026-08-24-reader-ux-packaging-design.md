# Reader UX, Icon, and Packaging Design

Date: 2026-08-24  
Status: Draft for user review  
Depends on: `docs/superpowers/specs/2026-08-21-reader-design.md`

## 1. Goal

Fix daily-use friction in Reader and ship it as a real Windows app:

1. First window is large enough to read (1200×800, centered).
2. Multiple files open as tabs; a Notepad-style **+** adds a blank tab; drag-drop and Open add more tabs.
3. Office documents default to **fast builtin preview**; user can switch a tab to **Office 高保真** when needed.
4. Brand icon is a distinctive blue rounded-ribbon uppercase **R** with transparency inside letter counters and outside the glyph.
5. Users launch **Reader.exe**, not `reader.cmd`. Explorer “Open with” and the desktop shortcut target that exe and show the R icon.

This increment does not add dual pane, translation, or format conversion.

## 2. Non-goals

- Do not change system default apps (`UserChoice`).
- PyInstaller onedir vs onefile debate beyond: use **one-folder** (`onedir`) for faster startup and WebEngine compatibility
- macOS / Linux packaging
- Remembering last window size (user chose fixed 1200×800)
- Auto Office-first preview (user chose builtin-first)

## 3. Window, tabs, and open flow

Approved:

- Default geometry: **1200×800**, centered on the primary screen. Minimum size 800×500 so it cannot collapse to a tiny chrome-only window.
- Tab bar (right side): **+** creates a blank tab titled `未命名`. Blank tab shows a drop hint: “拖入文件，或使用 文件 → 打开”.
- **文件 → 打开** (Ctrl+O): native multi-select dialog filtered to `.docx .pptx .xlsx .md`. Each chosen file becomes a new tab.
- Drag onto window, tab bar, or a blank tab: supported files append as new tabs. Dropping onto a **blank** tab replaces that blank tab with the first file; extra files still add new tabs.
- Same resolved path already open in this window: focus existing tab, do not duplicate.
- Last tab close: window stays empty (blank state, no tabs, or one leftover blank — pick **no leftover blank**: empty drop area until + or Open or drop).
- Running instance: second launch / Open with forwards paths via existing single-instance IPC into the **active** window as new tabs. Multiple files in one argv list → multiple tabs.
- **新建窗口** remains; new window also 1200×800 centered with offset (+32,+32) if it would fully overlap.

## 4. Preview policy

Default `preview(path)` for `.docx`/`.pptx`/`.xlsx` uses **builtin HTML only** (do not call Office COM on open). Markdown stays builtin.

Each loaded Office tab shows a status/action:

- Status: `内置预览`
- Button/menu: **Office 高保真** — enabled only if Office COM is available for that suffix; otherwise disabled with tooltip “未检测到 Microsoft Office”.

Switching to high-fidelity:

- Runs existing COM export on the worker thread.
- On success: status `Office 预览`, replace viewer with PDF/HTML result.
- On failure: keep builtin content, status `内置预览（Office 导出失败）`.

User can switch back to builtin without re-opening the file.

Window must appear immediately; tabs show `正在加载…` until builtin HTML is ready. Do not block GUI on COM.

Serial preview executor stays (COM is not thread-safe); builtin jobs may still share that pool in this increment to avoid a second architecture change.

## 5. Icon

Source: concept **C** — rounded-ribbon blue uppercase **R**.

Requirements:

- Only the blue **R** strokes occupy pixels.
- Interior counters of R and the field around R are **fully transparent** (alpha 0), not a white/gray plate, not a filled circle.
- No shortcut overlay in the source asset (Windows may add one on `.lnk`).
- Master: `assets/icons/reader-r.svg` (vector). Raster: PNG 16/24/32/48/256 plus `assets/icons/reader.ico` (multi-size).
- Applied to: `Reader.exe` (version resource), `QApplication`/`MainWindow` window icon, desktop `.lnk` IconLocation, ProgID DefaultIcon.

Color: saturated blue in the **C** family (approx `#2563EB`), readable on light and dark taskbars.

## 6. Packaging and shell

Ship a **PyInstaller onedir** build:

- Output: `dist/Reader/Reader.exe` plus `_internal` (or PyInstaller default).
- `--windowed` (no console).
- `--icon assets/icons/reader.ico`.
- Include PySide6 WebEngine resources.
- Version info: ProductName `Reader`, FileDescription `Reader`.

`register_open_with` and `create_desktop_shortcut` take the **exe path**:

- Command: `"<exe>" "%1"` (Explorer passes one path per invocation; multi-select becomes multiple launches that IPC coalesces, or one launch with multiple `%1` depending on Windows — handle **all argv files**).
- Shortcut Target: `Reader.exe`; WorkingDirectory: exe directory; IconLocation: exe.
- Do not register `scripts/reader.cmd` once the frozen exe exists.

Development still supports `python -m reader`; first-run association uses `sys.executable` + `-m reader` only when not frozen. Frozen path always uses `sys.executable` as the exe.

Provide `scripts/build_windows.ps1` that: create venv-or-use current, `pip install -e ".[dev]" pyinstaller`, run PyInstaller spec, copy icon.

## 7. Error handling

- Unsupported drop/open: status message, no new content tab (blank tab stays if user dropped nothing valid).
- Association/shortcut write failure: app still runs; non-blocking status or first-run hint.
- High-fidelity failure: builtin remains visible.
- Missing icon file in dev: Qt default icon, tests still pass with a generated fixture ico if needed.

## 8. Testing (TDD)

- Window default size 1200×800 and centered (mock screen geometry).
- `+` creates blank tab; Open dialog injection adds tabs; drop on blank replaces; drop extra files appends.
- Duplicate path focuses; IPC second instance adds tabs.
- Pipeline: Office files without explicit flag never call `office.export`; with flag they do.
- High-fidelity button disabled when `available_for` is false.
- `register_open_with` command quotes exe; DefaultIcon points at exe; never writes UserChoice.
- Icon asset: PNG/ICO alpha at center of a counter and outside glyph is 0 (sample pixels in a generated or committed icon).
- Packaging script/spec exists and references the ico; freeze itself is manual/CI optional, not required on machines without PyInstaller extras.

## 9. Risks

- WebEngine + PyInstaller: must collect QtWebEngineProcess and resources or the viewer is blank.
- Transparent ICO: Windows 11 taskbar sometimes composites poorly; keep a slightly thicker stroke.
- Multi-file “Open with”: Windows may start N processes; IPC must accept rapid sequential connects.

