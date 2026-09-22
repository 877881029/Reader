# Release Risk Burn-down Implementation Plan

Date: 2026-09-22
Status: Approved; execution started
Spec: `docs/superpowers/specs/2026-09-22-release-risk-burn-down-design.md`

## Task 1: Enforce repository consistency

Status: Complete (`1d5a379`)

**Files**

- Modify: `.gitignore`
- Modify: `pyproject.toml`
- Modify: completed files in `docs/superpowers/specs/`
- Create: `tests/test_project_hygiene.py`
- Modify: `docs/STATUS.md`

**RED**

Add tests that require:

- `/logs/` is ignored;
- the package description identifies a Windows multi-format document viewer;
- top-level specification headers do not contain `Draft for user review`,
  `awaiting implementation plan`, or `implementing`.

Run:

```text
python -m pytest tests/test_project_hygiene.py -v
```

Expected RED: all three contracts fail against the current repository.

**GREEN**

- Add `/logs/` to `.gitignore`.
- Update project description.
- Normalize only the top-level status line of completed specifications.
- Re-run the focused test and `git diff --check`.

**Boundary**

Update STATUS, commit, and push before Task 2.

## Task 2: Add one fast quality gate

Status: Complete (`3252f9e`)

**Files**

- Create: `scripts/verify.ps1`
- Modify: `tests/test_packaging.py`
- Modify: `README.md`
- Modify: `docs/STATUS.md`

**RED**

Add packaging tests requiring a strict PowerShell script. The initial proposed
order was:

1. Python `pytest`;
2. PPTX `npm ci`, test, and typecheck;
3. Markdown `npm ci`, test, and typecheck.

It must stop on native non-zero exit and offer an explicit release switch that
adds `build_windows.ps1` and `smoke_windows.ps1`.

Real execution proved that Python supply-chain tests inspect installed Web
dependencies and generated bundle manifests. The accepted order is therefore
PPTX Web install/test/typecheck/build, Markdown Web
install/test/typecheck/build, deterministic PPTX notice/manifest restoration,
then Python `pytest`.

**GREEN**

Implement `scripts/verify.ps1`, document the quick and release commands, run
the focused packaging tests, then run the quick gate itself.

**Boundary**

Update STATUS, commit, and push before Task 3.

## Task 3: Prove frozen TXT opening

Status: Complete (`b37976c`)

**Files**

- Modify: `src/reader/smoke.py`
- Modify: `src/reader/shell/window.py`
- Modify: `scripts/smoke_windows.ps1`
- Modify: `tests/test_smoke.py`
- Modify: `tests/test_window.py`
- Modify: `tests/test_packaging.py`
- Modify: `docs/STATUS.md`

**RED**

Add tests for smoke-only generic document-ready telemetry and a frozen TXT
phase. The event must include canonical path, `kind="code"`, extension
`.txt`, and status `文本预览`; no environment variable means no side effect.

**GREEN**

Emit the event only after the guarded current document content is installed.
Extend frozen smoke with an isolated TXT file/profile/namespace, wait for the
exact event, then prove process and temporary-root cleanup.

Run focused smoke/window/packaging tests followed by the fast gate.

**Boundary**

Update STATUS, commit, and push before Task 4.

## Task 4: Add clean Windows CI

Status: Complete; pending boundary commit

**Files**

- Create: `.github/workflows/quality.yml`
- Modify: `tests/test_project_hygiene.py`
- Modify: `README.md`
- Modify: `docs/STATUS.md`

**RED**

Add a repository test requiring a Windows workflow with checkout, Python 3.12,
Node 22, pip editable dev install, and the unified fast gate.

**GREEN**

Add the workflow with least-privilege read permissions, concurrency
cancellation, dependency caches, and no Office requirement. Validate YAML
structure through the regression test and run the fast gate locally.

**Boundary**

Update STATUS, commit, and push before Task 5.

## Task 5: Release-candidate verification

**Files**

- Modify: `docs/STATUS.md`
- Update generated Web bundles only if the build deterministically changes them

Run:

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1 -Release
```

Acceptance:

- Python full suite passes;
- both Web suites and typechecks pass;
- clean PyInstaller build succeeds;
- frozen smoke reports PPTX 4 slides, Markdown ready, TXT text preview, and
  exactly two IPC batches;
- no Reader/QtWebEngine process or isolated smoke root remains;
- STATUS records final executable and bundle hashes.

Commit and push the final STATUS/hash update.

## Task 6: Start the next feature only after risk closure

Create a separate specification and TDD plan for `.cpp`/`.hpp` reading. Do not
combine that feature with release-risk commits.
