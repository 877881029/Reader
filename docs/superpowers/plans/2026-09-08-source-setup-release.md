# Source Setup 0.1.0 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. User asked to start in this session — execute inline without review gates.

**Goal:** Colleagues clone the repo, run `scripts/setup.ps1`, and Reader starts from a local venv; git contains no zip/exe.

**Architecture:** Add `VERSION` as the 0.1.0 source of truth. `setup.ps1` finds Python 3.12+, creates `.venv`, `pip install -e .`, then `python -m reader`. README and `release/README.md` document capabilities and the source-only policy.

**Tech Stack:** PowerShell, pytest (script/doc contract tests), existing PySide6 app.

## Global Constraints

- Product version is `0.1.0` (not 1.0.0).
- Git must not contain zip, `bin/`, `Reader.exe`, or `_internal/`.
- `setup.ps1` must not call npm, PyInstaller, or `build_windows.ps1`.
- Do not edit `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Commit + push; update `docs/STATUS.md`.

---

### Task 1: VERSION + setup.ps1

**Files:**
- Create: `VERSION`, `scripts/setup.ps1`
- Modify: `tests/test_packaging.py`, `.gitignore`
- Test: `tests/test_packaging.py`

**Interfaces:**
- Produces: `VERSION` one line `0.1.0`; `scripts/setup.ps1` with `-SkipLaunch` and `-Dev`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_packaging.py`:

```python
def test_version_file_matches_pyproject_and_win32_resource() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version == "0.1.0"
    assert version.splitlines() == ["0.1.0"]
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.0"' in pyproject
    info = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(0, 1, 0, 0)" in info
    assert "StringStruct('FileVersion', '0.1.0')" in info
    assert "StringStruct('ProductVersion', '0.1.0')" in info


def test_setup_script_installs_runtime_venv_and_launches_reader() -> None:
    script = (ROOT / "scripts" / "setup.ps1").read_text(encoding="utf-8")
    assert "param(" in script
    assert "$SkipLaunch" in script
    assert "$Dev" in script
    assert "py -3.12" in script
    assert "winget install Python.Python.3.12" in script
    assert "-m venv" in script
    assert ".venv\\Scripts\\python.exe" in script or '.venv\Scripts\python.exe' in script
    assert 'pip install -e "."' in script or 'pip install -e .' in script
    assert 'pip install -e ".[dev]"' in script
    assert "-m reader" in script
    assert "npm" not in script.lower()
    assert "PyInstaller" not in script
    assert "build_windows.ps1" not in script


def test_gitignore_keeps_dist_and_release_binaries_out_of_git() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "dist/" in ignore
    assert "release/*.zip" in ignore
    assert "release/*.exe" in ignore
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_packaging.py::test_version_file_matches_pyproject_and_win32_resource tests/test_packaging.py::test_setup_script_installs_runtime_venv_and_launches_reader tests/test_packaging.py::test_gitignore_keeps_dist_and_release_binaries_out_of_git -v`

Expected: FAIL (`VERSION` / `setup.ps1` missing).

- [ ] **Step 3: Minimal implementation**

`VERSION` file contents:

```text
0.1.0
```

`.gitignore` append:

```gitignore
release/*.zip
release/*.exe
```

`scripts/setup.ps1`:

```powershell
[CmdletBinding()]
param(
    [switch]$SkipLaunch,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Resolve-Python312 {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        $executable = & $py.Source -3.12 -c "import sys; print(sys.executable)"
        if ($LASTEXITCODE -eq 0 -and $executable) {
            return $executable.Trim()
        }
    }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        $ok = & $python.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return $python.Source
        }
    }
    throw "Python 3.12+ is required. Install with: winget install Python.Python.3.12"
}

$python = Resolve-Python312
$venvDir = Join-Path $Root ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $python -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create .venv (exit $LASTEXITCODE)"
    }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip (exit $LASTEXITCODE)"
}

if ($Dev) {
    & $venvPython -m pip install -e ".[dev]"
} else {
    & $venvPython -m pip install -e .
}
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Reader (exit $LASTEXITCODE)"
}

if (-not $SkipLaunch) {
    & $venvPython -m reader
    if ($LASTEXITCODE -ne 0) {
        throw "Reader failed to start (exit $LASTEXITCODE)"
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```text
feat: add VERSION and Windows setup.ps1 for source launches
```

---

### Task 2: README + release notes

**Files:**
- Modify: `README.md`
- Create: `release/README.md`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Consumes: `scripts/setup.ps1`, `VERSION`
- Produces: Chinese README capability list + source-only 0.1.0 notes

- [ ] **Step 1: Write the failing tests**

```python
def test_readme_documents_formats_and_setup_command() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for token in (".docx", ".pptx", ".xlsx", ".md", ".pdf", r"scripts\setup.ps1"):
        assert token in readme
    assert "0.1.0" in readme
    assert "翻译" in readme or "左右" in readme


def test_release_notes_state_source_snapshot_without_binaries() -> None:
    notes = (ROOT / "release" / "README.md").read_text(encoding="utf-8")
    assert "0.1.0" in notes
    assert "setup.ps1" in notes
    assert "exe" in notes.lower() or "zip" in notes.lower()
    assert "git" in notes.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_packaging.py::test_readme_documents_formats_and_setup_command tests/test_packaging.py::test_release_notes_state_source_snapshot_without_binaries -v`

Expected: FAIL.

- [ ] **Step 3: Minimal implementation**

`README.md` (Chinese): name, 0.1.0, supported formats and behavior, not-in-scope, Windows-only, `setup.ps1` command, `-SkipLaunch` / `-Dev`, local freeze via `build_windows.ps1` without committing `dist/`.

`release/README.md`: 0.1.0 is a source snapshot; no zip/exe in git; run `setup.ps1`; freeze locally if needed.

Update `docs/STATUS.md` current goal to completed after Task 2 tests pass (and a focused pytest of packaging + chrome smoke tests).

- [ ] **Step 4: Run tests to verify they pass**

`python -m pytest tests/test_packaging.py tests/test_window.py::test_caption_press_on_main_window_starts_system_move tests/test_window.py::test_window_buttons_are_client_hits_and_clickable -q`

Expected: PASS.

- [ ] **Step 5: Commit + push**

```text
docs: describe 0.1.0 capabilities and source-only setup
```
