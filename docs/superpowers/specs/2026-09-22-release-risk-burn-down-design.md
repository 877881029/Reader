# Release Risk Burn-down Design

Date: 2026-09-22
Status: Approved by user; risk burn-down active
Progress ledger: `docs/STATUS.md`

## 1. Goal

Before adding another Reader feature, remove foreseeable delivery and handoff
risks so a new Agent can trust Git, run one deterministic quality gate, and
verify the frozen application opens the newest supported format.

This increment turns risk review into a permanent development step rather than
a one-time chat report.

## 2. Confirmed risks

| ID | Risk | Evidence | Impact |
|---|---|---|---|
| R1 | Dirty workspace from local logs | untracked `logs/bvm/bvm.log`; no `/logs/` ignore rule | New Agents can mistake generated data for product work or commit it |
| R2 | Specification status drift | completed specifications still say Draft, awaiting plan, or implementing | New Chats can resume obsolete work or change product direction |
| R3 | Package metadata drift | `pyproject.toml` description lists only four early formats | Release metadata no longer describes the product |
| R4 | No single fast quality gate | Python and two Web projects have separate commands | Agents can validate only a subset and report false readiness |
| R5 | Latest frozen capability lacks acceptance coverage | frozen smoke covers PPTX, Markdown, and IPC, but not `.txt` | Source tests can pass while packaged TXT opening is broken |
| R6 | No remote CI gate | no `.github/workflows/` | A pushed commit can be untested on a clean Windows machine |
| R7 | Startup performance evidence is anecdotal | STATUS records user observations but no stable milestone record | Regressions may be noticed late; strict timing thresholds would be flaky |

## 3. Scope and order

### 3.1 Repository consistency

- Ignore repository-root `logs/` as generated local diagnostics.
- Normalize misleading top-level specification states without rewriting their
  historical content.
- Update package description to the current multi-format Reader.
- Add a regression test that rejects known stale status phrases and missing
  generated-log ignore coverage.

### 3.2 Unified local quality gate

- Add one PowerShell entry point for the repeatable fast gate.
- It runs Python tests plus both locked Web test/typecheck suites.
- It fails on the first failed command and preserves native exit codes.
- Frozen build and GUI smoke remain an explicit release mode because they are
  materially slower.

### 3.3 Frozen TXT acceptance

- Add format-explicit ready telemetry for TXT under a smoke-only environment
  variable; normal runs have no logging side effect.
- Extend frozen smoke with an isolated `.txt` phase.
- Assert the packaged application reports the expected path, `kind`, and
  `文本预览` status before cleanup.

### 3.4 Clean-machine CI and release candidate

- Add a Windows GitHub Actions workflow running the fast gate on pushes and
  pull requests.
- Pin Python 3.12 and Node 22 at the workflow boundary; application dependency
  versions remain governed by existing manifests/locks.
- Run the full local regression, clean frozen build, and frozen smoke before
  declaring this increment complete.
- Record final hashes and any environment-specific skips in `docs/STATUS.md`.

### 3.5 Performance observability

- Keep current user-visible startup fixes unchanged.
- Record milestone durations during release smoke when they can be collected
  without changing production behavior.
- Do not use a strict cross-machine seconds threshold in CI. Correct ordering,
  completion before the existing timeout, and comparison across local releases
  are the stable acceptance criteria.

## 4. Non-goals

- No new document format in this increment.
- No UI redesign.
- No network service or runtime telemetry in normal Reader sessions.
- No deletion or committing of the existing local `logs/bvm/bvm.log`.
- No Office-dependent CI requirement.
- No strict cold-start performance threshold shared across machines.

## 5. TDD and Git boundaries

Every behavior change follows RED → GREEN → REFACTOR:

1. Add the smallest regression test and observe the intended failure.
2. Add the minimum implementation.
3. Run the focused test, then the relevant wider suite.
4. Update `docs/STATUS.md`.
5. Commit and push that one reversible behavior before starting the next.

Documentation-only specification and plan boundaries are committed separately
from implementation.

## 6. Acceptance criteria

- `git status --short` no longer reports repository-root `logs/`.
- No completed specification claims it is Draft, awaiting its plan, or still
  implementing.
- Project metadata describes Reader as a Windows multi-format document viewer.
- One documented fast command validates Python, PPTX Web, and Markdown Web.
- Frozen smoke proves PPTX, Markdown, TXT, and IPC behavior with isolated
  profiles and deterministic cleanup.
- Windows CI executes the fast gate from a clean checkout.
- Full regression, clean build, and frozen smoke pass; final artifact hashes
  and remaining skips are recorded.

## 7. Next feature gate

Only after these criteria pass may a new feature specification begin. The
recommended next feature remains additional code-reading extensions
(`.cpp`/`.hpp` first) because it reuses the existing read-only code pipeline.
