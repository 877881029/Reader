# PPTX Relationship Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix blank slides caused by `pptx-viewer@0.2.2` confusing `slide`, `slideMaster`, and `slideLayout` relationship types.

**Architecture:** Keep the audited MIT dependency pinned. A repository-owned postinstall script patches the pinned ESM distribution by replacing fuzzy relationship lookup with exact terminal-name lookup and fails if the expected source is absent. The deterministic test deck is reordered to reproduce the relationship ordering found in `canis_handover.pptx`.

**Tech Stack:** Node.js 18+, npm, TypeScript/Vitest/jsdom, `pptx-viewer@0.2.2`, Python 3.12+, python-pptx, PySide6 QtWebEngine, PyInstaller.

## Global Constraints

- Do not commit `canis_handover.pptx` or any internal user content.
- Keep `pptx-viewer` pinned exactly to `0.2.2`; do not copy proprietary Cursor extension code.
- Apply the patch automatically during `npm ci` and fail fast on source drift.
- Patch only the ESM file selected by the package `import` export and used by Vite/Reader.
- Preserve local-only WebEngine restrictions and existing text/Office fallbacks.
- Update `docs/STATUS.md`, commit, and push `origin/main` at every task boundary.

---

### Task 1: Reproduce the relationship-order failure

**Files:**
- Modify: `scripts/generate_pptx_visual_fixture.py`
- Modify: `tests/fixtures/pptx/visual-elements.pptx`
- Modify: `tests/test_pptx_fixture.py`
- Modify: `web/pptx-viewer/src/viewer.test.ts`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Produces a deterministic PPTX whose `ppt/_rels/presentation.xml.rels`
  places `relationships/slide` entries before `relationships/slideMaster`.
- The existing fixture path remains unchanged.

- [ ] **Step 1: Add a Python assertion for adversarial relationship order**

```python
from zipfile import ZipFile

with ZipFile(first) as archive:
    rels = archive.read("ppt/_rels/presentation.xml.rels")
assert rels.index(b"/relationships/slide\"") < rels.index(
    b"/relationships/slideMaster\""
)
```

- [ ] **Step 2: Normalize the generated relationship XML**

Add a helper that extracts direct `<Relationship .../>` tags from
`ppt/_rels/presentation.xml.rels`, stably partitions exact `/slide` tags before
the remaining tags, and replaces only that tag region. Call it from
`_normalize_zip`.

- [ ] **Step 3: Regenerate the committed fixture and update its SHA256**

Run:

```powershell
.venv\Scripts\python.exe scripts\generate_pptx_visual_fixture.py
Get-FileHash tests\fixtures\pptx\visual-elements.pptx -Algorithm SHA256
```

- [ ] **Step 4: Add the failing renderer regression**

Extend the official renderer test:

```typescript
expect(presentation.slideMasters.size).toBe(1);
expect(presentation.slideLayouts.size).toBeGreaterThan(0);
expect(
  presentation.slides[0]?.elements.some((element) =>
    element.text?.paragraphs?.some((paragraph) =>
      paragraph.runs?.some((run) => run.text.includes("Inherited title")),
    ),
  ),
).toBe(true);
```

- [ ] **Step 5: Verify RED**

Run:

```powershell
npm --prefix web/pptx-viewer test -- src/viewer.test.ts
```

Expected: FAIL because `slideMasters` contains parsed slides,
`slideLayouts.size` is zero, or inherited text is missing.

- [ ] **Step 6: Update STATUS and checkpoint**

```powershell
git add scripts/generate_pptx_visual_fixture.py tests/fixtures/pptx/visual-elements.pptx tests/test_pptx_fixture.py web/pptx-viewer/src/viewer.test.ts docs/STATUS.md
git commit -m "test: reproduce PPTX relationship type collision"
git push origin main
```

---

### Task 2: Apply an exact relationship lookup patch

**Files:**
- Create: `web/pptx-viewer/scripts/patch-pptx-viewer.mjs`
- Create: `web/pptx-viewer/scripts/patch-pptx-viewer.test.ts`
- Modify: `web/pptx-viewer/package.json`
- Modify: `web/pptx-viewer/package-lock.json`
- Modify: `web/pptx-viewer/THIRD_PARTY_NOTICES.txt`
- Refresh: `assets/pptx-viewer/**`
- Modify: `docs/STATUS.md`

**Interfaces:**
- `patchRelationshipLookup(source: string): string` returns patched source or
  throws on unsupported source.
- `npm run patch:pptx-viewer` patches
  `node_modules/pptx-viewer/dist/pptx-viewer.js`.
- Root `postinstall` invokes that command after every `npm ci`.

- [ ] **Step 1: Write patch-script tests**

Tests must assert:

```typescript
expect(patchRelationshipLookup(unpatched)).toContain(
  "const l = hn(i);",
);
expect(() => patchRelationshipLookup("unexpected source")).toThrow(
  "Unsupported pptx-viewer@0.2.2 source",
);
expect(patchRelationshipLookup(patched)).toBe(patched);
```

- [ ] **Step 2: Verify patch-script RED**

Run:

```powershell
npm --prefix web/pptx-viewer test -- scripts/patch-pptx-viewer.test.ts
```

Expected: FAIL because the patch module does not exist.

- [ ] **Step 3: Implement deterministic patching**

The script must replace exactly this behavior in the pinned ESM bundle:

```javascript
getByType(i) {
  const l = hn(i);
  return r.get(l) || [];
}
```

It must count the unpatched pattern, reject counts other than one, recognize an
already-patched marker, write UTF-8 without changing unrelated bytes, and print
the patched dependency path.

- [ ] **Step 4: Wire npm lifecycle**

Add:

```json
"postinstall": "npm run patch:pptx-viewer",
"patch:pptx-viewer": "node scripts/patch-pptx-viewer.mjs"
```

Run `npm install --package-lock-only` so the root lock metadata matches
`package.json`.

- [ ] **Step 5: Record the local MIT patch**

Append a notice stating that Reader changes relationship lookup in
`pptx-viewer@0.2.2` from substring matching to exact terminal type matching;
retain both upstream MIT license texts.

- [ ] **Step 6: Verify GREEN and rebuild bundle**

Run:

```powershell
npm --prefix web/pptx-viewer ci
npm --prefix web/pptx-viewer test
npm --prefix web/pptx-viewer run typecheck
npm --prefix web/pptx-viewer run build
```

Copy the notice into `assets/pptx-viewer/` and regenerate
`manifest.sha256` using `scripts/build_windows.ps1` during Task 3.

- [ ] **Step 7: Update STATUS and checkpoint**

```powershell
git add web/pptx-viewer assets/pptx-viewer docs/STATUS.md
git commit -m "fix: match PPTX relationship types exactly"
git push origin main
```

---

### Task 3: Real-deck proof and frozen certification

**Files:**
- Modify: `tests/test_pptx_webengine.py`
- Modify: `docs/STATUS.md`
- Rebuild: `dist/Reader/Reader.exe`
- Refresh: desktop `Reader.lnk`

**Interfaces:**
- The committed adversarial fixture is the permanent automated regression.
- `canis_handover.pptx` is a local-only acceptance input and is never committed.

- [ ] **Step 1: Strengthen real QWebEngine assertions**

After ready, assert the first slide host contains `Inherited title`, the
slide-content/layout layers are non-empty, and the initial blocked URL snapshot
remains empty.

- [ ] **Step 2: Run focused and full verification**

```powershell
npm --prefix web/pptx-viewer test
.venv\Scripts\python.exe -m pytest tests/test_pptx_fixture.py tests/test_pptx_webengine.py -v
.venv\Scripts\python.exe -m pytest -q
```

- [ ] **Step 3: Probe the local real deck**

Open `C:\Users\runqyang\Downloads\canis_handover.pptx` through
`PptxVisualView`; assert seven slides and visible `CANIS handover` text on
slide 1. Do not copy the deck into the repository.

- [ ] **Step 4: Build and frozen smoke**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke_windows.ps1 -ReaderExe dist/Reader/Reader.exe
Get-FileHash dist/Reader/Reader.exe -Algorithm SHA256
```

Refresh and verify desktop shortcut target, working directory, and icon.

- [ ] **Step 5: Final review, STATUS, commit, and push**

Record tests, real-deck proof, bundle manifest hash, executable hash, and final
review result in STATUS.

```powershell
git add tests/test_pptx_webengine.py docs/STATUS.md
git commit -m "test: certify PPTX relationship compatibility"
git push origin main
```

## Self-Review Record

- [x] Spec coverage: exact matching, adversarial ordering, real WebEngine,
  local real-deck proof, frozen build, and process synchronization are covered.
- [x] Placeholder scan: no TBD/TODO/“similar to” implementation gaps.
- [x] Type consistency: patch function, npm commands, fixture path, and viewer
  assertions use existing project interfaces.
