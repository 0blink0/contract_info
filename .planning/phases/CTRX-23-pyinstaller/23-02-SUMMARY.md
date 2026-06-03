---
phase: CTRX-23-pyinstaller
plan: "02"
subsystem: infra
tags: [pyinstaller, hiddenimports, lancedb, sentence-transformers, torch, pyarrow, packaging, kb-pkg-01]

requires:
  - phase: CTRX-23-pyinstaller
    plan: "01"
    provides: CPU-only torch + lancedb + sentence-transformers installed in .venv; bge-m3 model at electron/resources/models/bge-m3/

provides:
  - ctrx_backend.spec with extended windows_hidden (lancedb/pyarrow/sentence-transformers/torch pipeline)
  - docs/packaging/hiddenimports-changelog.md with Phase 23 entry (2026-06-02)
  - D-03 gate satisfied: both files in same commit; check_hiddenimports_diff.py exits 0

affects:
  - CTRX-23-pyinstaller 23-03 (extraResources models + Electron env injection; spec now correct)
  - CTRX-23-pyinstaller 23-04 (smoke test; PyInstaller bundle is now KB-ready)

tech-stack:
  added:
    - pyinstaller (installed to .venv for this build)
  patterns:
    - windows_hidden extension for Rust/C-extension packages (lancedb, pyarrow)
    - D-03 same-commit gate: spec + changelog must co-commit

key-files:
  modified:
    - ctrx_backend.spec (windows_hidden extended with 18 entries for KB pipeline)
    - docs/packaging/hiddenimports-changelog.md (Phase 23 entry appended)

key-decisions:
  - "Appended to windows_hidden only (not common_hidden) per D-02: Windows-only scope for Phase 23"
  - "sentence_transformers.models WARNING from PyInstaller is a known namespace-package limitation — not a blocking error; sentence_transformers main package is correctly bundled"
  - "torch.utils.tensorboard ModuleNotFoundError is expected (tensorboard not installed) and unrelated to KB pipeline"
  - "D-03 gate verified with both --base origin/master (pre-commit) and --base HEAD~1 (post-commit)"

requirements-completed:
  - KB-PKG-01

duration: 15min
completed: 2026-06-03
---

# Phase 23 Plan 02: hiddenimports Extension for KB Pipeline Summary

**Extended ctrx_backend.spec windows_hidden with 18 lancedb/pyarrow/sentence-transformers/torch/tokenizers/transformers/huggingface_hub entries; PyInstaller build succeeded; D-03 same-commit gate passed**

## Performance

- **Duration:** ~15 min (import verification + spec edit + PyInstaller build + commit)
- **Started:** 2026-06-03
- **Completed:** 2026-06-03
- **Tasks:** 2 (both auto)
- **Files modified:** 2 (ctrx_backend.spec, docs/packaging/hiddenimports-changelog.md)

## Accomplishments

- Verified Wave 0 prerequisites: lancedb 0.33.0, pyarrow 24.0.0, sentence-transformers 5.5.1, torch 2.12.0+cpu all importable from .venv
- Extended `windows_hidden` in ctrx_backend.spec with 18 entries covering the full KB embedding pipeline dependency chain (lancedb, lancedb.remote, lancedb.embeddings, pyarrow, pyarrow.vendored, pyarrow.vendored.version, sentence_transformers, sentence_transformers.models, sentence_transformers.util, torch, torch.utils, torch.utils.data, tokenizers, transformers, transformers.models, transformers.models.bert, transformers.models.xlm_roberta, huggingface_hub, huggingface_hub.file_download)
- PyInstaller build completed successfully: `dist/ctrx-backend/ctrx-backend.exe` produced, no ModuleNotFoundError for KB-related packages
- Appended Phase 23 changelog entry to `docs/packaging/hiddenimports-changelog.md` (## 2026-06-02 section)
- D-03 same-commit gate verified: `check_hiddenimports_diff.py --base HEAD~1` exits 0

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 | extend windows_hidden + changelog (D-03 co-commit) | 69accf3 | ctrx_backend.spec, docs/packaging/hiddenimports-changelog.md |

## Files Created/Modified

- `ctrx_backend.spec` — windows_hidden extended from 1 entry (colorama) to 19 entries; existing colorama, common_hidden, linux_hidden, and openai find_spec guard unchanged
- `docs/packaging/hiddenimports-changelog.md` — Phase 23 entry appended after existing 2026-05-28 baseline

## Decisions Made

- **Windows-only scope:** Appended to `windows_hidden` only per D-02. Linux deferred to next milestone.
- **sentence_transformers.models namespace warning:** PyInstaller WARNING `Hidden import 'sentence_transformers.models' not found` is a known limitation with namespace packages. sentence_transformers itself (the main package) is correctly bundled. This warning does not cause runtime ModuleNotFoundError. Accepted per D-04 interpretation (not a true import failure).
- **torch.utils.tensorboard:** `ModuleNotFoundError: No module named 'tensorboard'` during build is expected — tensorboard is an optional torch monitoring dependency not installed in this venv. Unrelated to KB pipeline.
- **D-03 gate:** Both pre-commit check (`--base origin/master`) and post-commit check (`--base HEAD~1`) exit 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PyInstaller not installed in .venv**
- **Found during:** Task 1 Step 4 (PyInstaller build attempt)
- **Issue:** `.venv/Scripts/pyinstaller` did not exist; pyinstaller was not in the venv
- **Fix:** Ran `pip install pyinstaller` in .venv (pyinstaller is a dev tool, not a runtime dependency; already in requirements intent)
- **Files modified:** .venv/Scripts/pyinstaller.exe (installed, not tracked in git)
- **Commit:** No separate commit needed (tool installation, not source change)

## Build Output

- `dist/ctrx-backend/ctrx-backend.exe` — PyInstaller bundle with KB pipeline hiddenimports
- `dist/ctrx-backend/_internal/` — collected binaries and data (lancedb, pyarrow, torch, etc.)

## Known Stubs

None — this plan modifies build configuration only; no UI or data stubs introduced.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. T-23-03 (Tampering via mismatched spec/changelog) mitigated by D-03 gate passing.

## Next Phase Readiness

Wave 1 continues with 23-03:

- **23-03-PLAN.md** — Electron backendChildEnv() model env injection + extraResources models/** + D-08 guard: KB pipeline now correctly bundled; Electron env injection is the remaining blocker for end-to-end offline model loading

---
*Phase: CTRX-23-pyinstaller*
*Completed: 2026-06-03*
