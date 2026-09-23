# Reader Hardening and Code Reading Experience

Date: 2026-09-23
Status: Approved
Progress ledger: `docs/STATUS.md`

## 1. Goal

Deliver three ordered increments on the verified Reader release baseline:

1. reduce the known Web development-tool vulnerability surface without
   weakening Node 18 compatibility or deterministic Web bundles;
2. complete the common C++ source/header suffix family through every existing
   read-only discovery, preview, shell, documentation, and frozen-validation
   surface;
3. add focused code-reading controls for line navigation, cursor position,
   wrapping, and font size while keeping Reader read-only and non-IDE.

Each increment is an independent TDD and Git boundary. The release gate must
remain green after every boundary.

## 2. Increment A: Web dependency security

### 2.1 Audit result

Both `web/pptx-viewer` and `web/md-viewer` currently report the same four npm
audit entries:

- `vite` high, with transitive `esbuild` moderate;
- `vitest` critical, with transitive `@vitest/mocker` moderate.

All four are development/build tools. The frozen Reader ships only their
generated static assets and does not run a Vite or Vitest server.

### 2.2 Approved upgrade policy

| Package | Current | Target | Reason |
|---|---:|---:|---|
| `vite` | `5.4.19` | `6.4.3` | First release above all current Vite advisory ranges; remains Node 18 compatible |
| `vitest` | `2.1.9` | `3.2.6` | Fixes the critical server issue and remains Node 18 compatible |

The initial npm suggestion of `vite@5.4.21` is insufficient for advisories
published after that patch: current audit data marks all Vite versions through
`6.4.2` vulnerable. `vite@6.4.3` declares
`^18.0.0 || ^20.0.0 || >=22.0.0`, so it closes the high-risk chain without
raising Reader's Node floor.

`vitest@4.1.11` is not selected because it requires Node 20 and would silently
break the documented Node 18+ contract. One dev-only moderate
`@vitest/mocker` advisory may therefore remain. It must be documented as
non-runtime and reconsidered only in a separate Node 20 baseline migration.

### 2.3 Acceptance

- Both package manifests and lockfiles resolve the approved versions.
- `npm audit` has no high or critical findings in either tree.
- Existing Web tests, type checks, builds, third-party notices, and bundle
  manifests remain deterministic.
- Python supply-chain and frozen-resource contracts still pass.
- No `npm audit fix --force` and no dependency-range widening.

## 3. Increment B: common C++ suffix family

Add these suffixes together:

- sources: `.cc`, `.cxx`;
- headers: `.hh`, `.hxx`;
- inline/template implementation: `.inl`, `.ipp`.

Every suffix must:

- belong to `CODE_SUFFIXES` and `SUPPORTED_EXTENSIONS`;
- map to the existing `"c"` language family and `CHighlighter`;
- route through `kind="code"` with status `代码预览`;
- appear in pipeline routing, current-user Open With registration, the open
  dialog, welcome/recent badges, README, and the feature guide;
- remain outside `PROTECTED_EXTENSIONS`;
- have representative frozen document-ready coverage without weakening the
  existing PPTX, Markdown, TXT, `.cpp/.hpp`, or exact two-batch IPC contracts.

Badge labels are the uppercase suffix without the dot: `CC`, `CXX`, `HH`,
`HXX`, `INL`, and `IPP`.

## 4. Increment C: code-reading controls

### 4.1 UI

`CodeTextView` gains a compact toolbar above the existing read-only
`CodeEditor`:

- a 1-based line-number spin box and `跳转` button;
- a checkable `换行` control, off by default;
- `A-` and `A+` controls with the current point size;
- a live `行 N，列 M` label.

The existing global status bar remains hidden. Controls are local to each code
tab so each tab preserves its own reading state.

### 4.2 Behavior

- line jump clamps to `1..blockCount`, moves to the start of the requested
  block, and centers the cursor when practical;
- position is 1-based and updates on every cursor move and after loading text;
- wrap toggles between `NoWrap` and `WidgetWidth`;
- font size starts at 12 pt, is bounded to 8..24 pt, updates tab-stop and gutter
  geometry, and cannot exceed the bounds;
- all existing selection, copy, find, syntax highlighting, line numbers, and
  current-line highlighting remain functional.

### 4.3 Non-goals

- editing or saving code/text files;
- compilation, diagnostics, symbol navigation, or LSP;
- persistent global preferences or cross-tab synchronization;
- changing Markdown editing behavior;
- changing native window hit testing, `begin_window_move`, or `nativeEvent`.

## 5. TDD and release acceptance

1. Every increment starts with focused RED tests that fail for the missing
   behavior.
2. GREEN changes are the smallest implementation satisfying those tests.
3. Each increment updates `docs/STATUS.md`, commits independently, and pushes
   to `origin/main` before the next increment begins.
4. The final release gate runs Web tests/type checks/builds, the full Python
   suite, PyInstaller, and all frozen GUI smoke stages in one invocation.
5. Final status records audit counts, test counts, generated manifests, EXE
   size/hash, cleanup counts, and any residual risk.
