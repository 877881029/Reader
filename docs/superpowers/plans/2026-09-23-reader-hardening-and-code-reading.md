# Reader Hardening and Code Reading Implementation Plan

> Execute tasks in order. For each task: observe RED, implement GREEN, run the
> focused suite, update `docs/STATUS.md`, commit, and push `origin/main` before
> starting the next task.

**Goal:** Safely upgrade the Web build/test toolchain, complete the common C++
suffix family, and add focused read-only code navigation controls.

**Spec:** `docs/superpowers/specs/2026-09-23-reader-hardening-and-code-reading-design.md`

**Environment:** Windows, Python
`C:\venvs\reader-076ca44a\Scripts\python.exe`, Node 18+ contract, Node 22 CI.

## Guardrails

- Do not run `npm audit fix --force`.
- Keep exact dependency pins and deterministic lockfiles/manifests.
- Do not raise the Node minimum above 18 in this increment.
- Do not add code editing, saving, compilation, diagnostics, or LSP.
- Do not add C++ suffixes to `PROTECTED_EXTENSIONS`.
- Do not modify native hit testing, `begin_window_move`, or `nativeEvent`.
- Preserve existing PPTX, Markdown, TXT, `.cpp/.hpp`, and exact two-batch IPC
  frozen smoke contracts.

## Task 1: Upgrade Web development dependencies

**RED**

Extend `tests/test_pptx_web_assets.py` and `tests/test_md_web_assets.py` to
require exact `vite=6.4.3` and `vitest=3.2.6` manifest and lockfile roots.
Run the focused Python tests and observe failures against `5.4.19` / `2.1.9`.

**GREEN**

Update both package manifests and regenerate both lockfiles with npm. Vite 6.4.3
is the first current-audit-safe release and retains Node 18 support. Do not
change runtime renderer dependencies. Run:

```powershell
C:\venvs\reader-076ca44a\Scripts\python.exe -m pytest `
  tests\test_pptx_web_assets.py tests\test_md_web_assets.py -q
npm --prefix web\pptx-viewer test
npm --prefix web\pptx-viewer run typecheck
npm --prefix web\pptx-viewer run build
npm --prefix web\md-viewer test
npm --prefix web\md-viewer run typecheck
npm --prefix web\md-viewer run build
npm --prefix web\pptx-viewer audit --audit-level=high
npm --prefix web\md-viewer audit --audit-level=high
```

Acceptance: no high/critical audit result; both Web suites and deterministic
asset contracts pass. Record the expected single dev-only moderate residual.

**Commit:** `build: upgrade secure Web test toolchain`

## Task 2: Add C++ suffix family to source behavior

**RED**

Parameterize existing format, highlighter, sniff, open, pipeline, association,
welcome badge, and open-dialog tests for `.cc/.cxx/.hh/.hxx/.inl/.ipp`. Require
`kind="code"`, status `代码预览`, language `"c"`, and `CHighlighter`.

**GREEN**

Extend only the existing suffix sets/maps in:

- `src/reader/formats/code.py`
- `src/reader/sniff.py`
- `src/reader/preview/pipeline.py`
- `src/reader/preview/syntax.py`
- `src/reader/shell/associate.py`
- `src/reader/shell/welcome.py`
- `src/reader/shell/window.py`

Update README and `docs/Reader功能全解.md`. Run the focused code/open/pipeline/
shell suites and then the unified fast gate.

**Commit:** `feat: add common C++ suffix family`

## Task 3: Extend frozen C++ acceptance

**RED**

Extend `tests/test_packaging.py` contracts to require representative frozen
files for the new source, header, and inline/template suffix classes. Observe
the failure before changing the smoke script.

**GREEN**

Extend the existing isolated C++ phase in `scripts/smoke_windows.ps1` so one
Reader process opens all required representative files and document-ready
telemetry validates every canonical path, extension, `kind="code"`, and
`代码预览`. Keep the script ASCII-only and every helper at top level.

Run packaging tests and PowerShell 5.1 syntax parsing.

**Commit:** `test: verify frozen C++ suffix family`

## Task 4: Add code-reading controls

**RED**

Add focused `tests/test_code_view.py` cases that require:

- named toolbar controls and a read-only editor;
- 1-based line jump with range clamping;
- live line/column updates;
- wrap off by default and toggle to `WidgetWidth`;
- 12pt default, 8..24pt bounded font controls;
- updated gutter/tab-stop geometry after font changes;
- controls reset correctly for newly loaded text without losing the
  highlighter.

**GREEN**

Implement the compact toolbar in `src/reader/preview/code_view.py`, expose only
small testable accessors/commands, and keep state per `CodeTextView`. Update
README and the feature guide.

Run `tests/test_code_view.py`, relevant find/window tests, then the unified fast
gate.

**Commit:** `feat: add code reading controls`

## Task 5: Final release candidate

Run the unique release entry:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts\verify.ps1 -Release `
  -Python C:\venvs\reader-076ca44a\Scripts\python.exe
```

Record:

- PPTX/Markdown Web counts;
- Python passed/skipped counts;
- audit residuals;
- frozen ready evidence for all format stages;
- source/frozen manifest hashes;
- EXE size and SHA256;
- Reader/QtWebEngine/temp cleanup counts.

Mark the spec and plan implemented, update `docs/STATUS.md`, commit, and push.

**Commit:** `docs: record Reader hardening completion`
