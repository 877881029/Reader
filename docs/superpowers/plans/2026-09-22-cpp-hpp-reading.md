# C++ Source Reading Implementation Plan

> Every task follows RED -> GREEN -> REFACTOR. After each independently
> verifiable behavior boundary, update `docs/STATUS.md`, commit, and push to
> `origin/main` before starting the next task.

**Goal:** Add consistent `.cpp` and `.hpp` read-only support by extending the
existing C/H code-view path.

**Architecture:** Treat both suffixes as C-family members of `CODE_SUFFIXES`.
Reuse `fmt_code.to_preview`, `CodeTextView`, and `CHighlighter`; wire every
discovery, dialog, association, badge, documentation, and frozen acceptance
surface without adding dependencies.

**Tech Stack:** Python 3.12, PySide6, pytest, PowerShell 5.1, PyInstaller.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Do not add a C++ parser, editor behavior, or third-party package.
- Do not add `.cpp` / `.hpp` to `PROTECTED_EXTENSIONS`.
- Preserve existing C/H/TXT behavior and exact IPC smoke batch assertions.
- Use `C:\venvs\reader-076ca44a\Scripts\python.exe` for this worktree.

## Task 1: Add the C++ suffix contract and production wiring

Status: Complete (`deb9736`)

**Files**

- Modify: `tests/test_formats_code.py`
- Modify: `tests/test_code_view.py`
- Modify: `tests/test_sniff.py`
- Modify: `tests/test_open.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_associate.py`
- Modify: `tests/test_window.py`
- Modify: `tests/test_welcome.py`
- Modify: `src/reader/formats/code.py`
- Modify: `src/reader/preview/syntax.py`
- Modify: `src/reader/sniff.py`
- Modify: `src/reader/preview/pipeline.py`
- Modify: `src/reader/shell/associate.py`
- Modify: `src/reader/shell/window.py`
- Modify: `src/reader/shell/welcome.py`
- Modify: `README.md`
- Modify: `docs/Reader功能全解.md`
- Modify: `docs/STATUS.md`

**RED**

Add parameterized tests for `.cpp` and `.hpp` that require:

- code-format membership, language `"c"`, `kind="code"`, and `代码预览`;
- `CHighlighter` selection and unchanged read-only/gutter behavior;
- sniff, `decide_open`, pipeline, dialog, badge, and association inclusion;
- absence from `PROTECTED_EXTENSIONS`;
- README and feature documentation coverage.

Run the focused test set and record the expected failures before production
changes.

**GREEN**

Add the two suffixes to the existing C-family sets/maps and UI/association
lists. Reuse all current code-view behavior. Run the focused tests, then the
unified fast gate.

**Boundary**

Update STATUS with RED/GREEN evidence, commit, and push before Task 2.

## Task 2: Add frozen C++ acceptance and close the feature

Status: Complete

**Files**

- Modify: `tests/test_packaging.py`
- Modify: `scripts/smoke_windows.ps1`
- Modify: `docs/STATUS.md`

**RED**

Extend packaging contracts to require isolated `.cpp` and `.hpp`
document-ready checks in the frozen smoke. Preserve the current PPTX,
Markdown, TXT, and exact two IPC batches. Run the focused packaging tests and
record the expected failure.

**GREEN**

Create representative temporary C++ source/header files, open each with the
frozen executable, require canonical path plus `kind="code"` and the matching
extension, and clean every process/profile/temp root in `finally`.

Run:

```text
C:\venvs\reader-076ca44a\Scripts\python.exe -m pytest tests\test_packaging.py -q
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1 -Release -Python C:\venvs\reader-076ca44a\Scripts\python.exe
```

Record the final executable and source/frozen bundle hashes, process/root
cleanup counts, and all test totals in STATUS.

**Boundary**

Mark the specification implemented, update STATUS, commit, push, and confirm
`HEAD...origin/main` is `0 / 0`.
