# Source Setup and 0.1.0 Release Notes Design

Date: 2026-09-08  
Status: Approved by user (git: scripts + docs only; clone → setup.ps1 → run)  
Depends on: existing frozen onedir build (`scripts/build_windows.ps1`) and committed `assets/pptx-viewer` / `assets/md-viewer`  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Colleagues clone this repository and run **one PowerShell script** to install Python dependencies and start Reader. Git stays a source tree: **no zip, no `bin/`, no `Reader.exe`, no `_internal/`**.

Product version for this snapshot is **0.1.0** (not 1.0.0; v1 is not finished).

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Current behavior

- `README.md` is a one-line English stub and does not list formats, setup, or limits.
- Version appears as `0.1.0` in `pyproject.toml` and `version_info.txt`, with no single `VERSION` file.
- Running from source already works: `pip install -e .` then `python -m reader`. First launch registers HKCU Open With and creates a desktop shortcut targeting `sys.executable` with args `("-m", "reader")`.
- `dist/` is gitignored. Frozen `dist/Reader/` is ~610MB and cannot live in GitHub git (100MB file cap; clone cost).
- `scripts/build_windows.ps1` still builds a local exe for developers who have Node 18+; that path is unchanged and still does not commit artifacts.

## 3. Architecture

### 3.1 Colleague path (required)

1. Clone on **Windows 10/11**.
2. From repo root: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1`
3. Script resolves Python **3.12+** (`py -3.12` preferred, else `python`). If missing: fail with a short message suggesting `winget install Python.Python.3.12`. Do **not** download an installer into git or silently install Python.
4. Create `.venv` if absent (`<python> -m venv .venv`).
5. Upgrade pip; `pip install -e .` (runtime deps only: PySide6, python-docx, python-pptx, openpyxl, markdown-it-py, pywin32). No Node, no npm, no PyInstaller.
6. Start Reader: `.venv\Scripts\python.exe -m reader`. Existing first-run shell integration creates/updates the desktop shortcut for this interpreter.

Optional `-SkipLaunch` installs deps and exits. Optional `-Dev` installs `.[dev]` (pytest / PyInstaller) for contributors.

Committed `assets/pptx-viewer` and `assets/md-viewer` are enough for visual PPTX/Markdown. Office COM is **not** required.

### 3.2 What git contains

| Path | Role |
|---|---|
| `VERSION` | Single line `0.1.0` (no `v` prefix). Source of truth. |
| `pyproject.toml` `version` | Must equal `VERSION`. |
| `version_info.txt` `FileVersion` / `ProductVersion` / `filevers` | Must equal `0.1.0` / `(0, 1, 0, 0)`. |
| `README.md` | Chinese: capabilities, limits, setup, run, local freeze. |
| `release/README.md` | 0.1.0 notes: this is a source snapshot; how to run; how to freeze locally; no binaries. |
| `scripts/setup.ps1` | One-shot venv + install + freeze via `build_windows.ps1` + launch. |

### 3.3 What git must not contain

- `dist/`, `build/`, `release/*.zip`, `release/*.exe`, `*.exe` binaries, Qt `_internal` trees.
- Keep existing `.gitignore` entries for `dist/`, `build/`, `.venv/`.

Local freeze remains `scripts/build_windows.ps1` → `dist/Reader/Reader.exe` on the developer machine only.

### 3.4 README capability list (must match product)

Supported open: `.pptx` (visual, optional text / Office), `.md` (visual; Ctrl+I edit, Ctrl+S save, Ctrl+T back), `.pdf` (Chromium viewer, PluginsEnabled), `.docx` / `.xlsx` (builtin HTML, optional Office).

Chrome: Notepad-style tabs, drag-drop, Ctrl+O, Open With, single-instance IPC, optional new window.

Not in 0.1.0: translation, dual pane, format conversion, becoming the system default app, macOS/Linux.

## 4. Non-goals

- Uploading a zip or exe to git or Git LFS.
- Creating a GitHub Release asset in this increment.
- Bundling/installing Python or Node into the repo.
- Changing preview/render behavior, hit-testing, or window chrome.
- Making `setup.ps1` **inline** npm or PyInstaller (it now **calls** `build_windows.ps1` instead; see `2026-09-11-setup-includes-freeze-design.md`).

## 5. Error handling

| Case | Behavior |
|---|---|
| Not Windows / no PowerShell | README states Windows-only. |
| Python missing or below 3.12 | setup.ps1 throws; prints winget hint; does not create a broken venv. |
| `pip install` fails | Non-zero exit; do not launch. |
| Launch fails | Non-zero exit; venv remains for retry. |
| No Office | Reader still starts; Office action stays optional. |

## 6. Testing

- `VERSION` text equals `pyproject.toml` version and `version_info.txt` FileVersion `0.1.0`.
- `scripts/setup.ps1` creates/uses `.venv`, `pip install -e .`, then calls `build_windows.ps1`; `-SkipBuild` skips freeze; does **not** inline `npm` or `PyInstaller`.
- `README.md` lists `.docx .pptx .xlsx .md .pdf` and the setup command.
- `release/README.md` states no binaries are in git.
- `.gitignore` still ignores `dist/`.
- Existing window/chrome tests stay green; do not edit `hit_test_local` / `begin_window_move` / `nativeEvent`.
