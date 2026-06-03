---
phase: CTRX-23-pyinstaller
plan: "01"
subsystem: infra
tags: [pyinstaller, lancedb, sentence-transformers, bge-m3, torch, packaging, gitignore]

requires:
  - phase: CTRX-22-rag-llm
    provides: kb_service.py with SentenceTransformer local_files_only=True pattern

provides:
  - CPU-only torch + lancedb + sentence-transformers + pyarrow installed in .venv
  - electron/resources/models/bge-m3/ in flat SentenceTransformer local-path format (~2.5 GB)
  - .gitignore rule excluding electron/resources/models/ from version control

affects:
  - CTRX-23-pyinstaller 23-02 (hiddenimports audit uses installed packages)
  - CTRX-23-pyinstaller 23-03 (Electron env injection targets electron/resources/models/)
  - CTRX-23-pyinstaller 23-04 (smoke test uses the model loaded via local_files_only=True)

tech-stack:
  added:
    - torch 2.12.0+cpu (CPU-only variant, no CUDA wheels)
    - lancedb 0.33.0
    - pyarrow 24.0.0 (transitive)
    - sentence-transformers 5.5.1
    - BAAI/bge-m3 weights (flat SentenceTransformer format, ~2.5 GB)
  patterns:
    - model.save(str(target)) for flat-directory format (NOT HuggingFace hub cache format)
    - SentenceTransformer(str(path), local_files_only=True) for offline reload
    - trailing-slash .gitignore pattern for large binary directories

key-files:
  created:
    - electron/resources/models/bge-m3/ (runtime asset, git-ignored)
  modified:
    - .gitignore (added electron/resources/models/ exclusion rule)

key-decisions:
  - "bge-m3 weights stored in flat SentenceTransformer local-path format (model.save()), NOT HuggingFace hub cache format — required for local_files_only=True reload without network"
  - "torch installed CPU-only via --index-url https://download.pytorch.org/whl/cpu to avoid 1-3 GB CUDA wheel download"
  - "electron/resources/models/ excluded from git via trailing-slash .gitignore entry — model weights are build-time assets, not source code"

patterns-established:
  - "Wave 0 blocker resolution: install deps first, then populate assets, then configure git exclusion"
  - "Model directory populated via model.save() into electron/resources/models/bge-m3/ — same extraResources tree as ctrx-backend binary"

requirements-completed:
  - KB-PKG-01
  - KB-PKG-02

duration: 45min
completed: 2026-06-03
---

# Phase 23 Plan 01: KB Dependency Installation & Model Download Summary

**CPU-only torch + lancedb 0.33.0 + sentence-transformers 5.5.1 installed in .venv; bge-m3 weights saved to electron/resources/models/bge-m3/ in flat local-path format; model directory git-ignored**

## Performance

- **Duration:** ~45 min (Task 1 + Task 2 human download + Task 3)
- **Started:** 2026-06-03
- **Completed:** 2026-06-03
- **Tasks:** 3 (1 auto + 1 human-action + 1 auto)
- **Files modified:** 1 (.gitignore)

## Accomplishments

- Installed CPU-only torch (no CUDA, saving ~1-3 GB) plus lancedb, sentence-transformers, pyarrow — all importable from .venv
- bge-m3 model (~2.5 GB) downloaded and saved in flat SentenceTransformer local-path format at `electron/resources/models/bge-m3/`; reload with `local_files_only=True` confirmed working, vector shape (1, 1024)
- Added `electron/resources/models/` to .gitignore following existing trailing-slash pattern; `git check-ignore` confirmed exclusion at `.gitignore:15`

## Task Commits

Each task was committed atomically:

1. **Task 1: Install KB dependencies (CPU-only torch)** — no tracked file changes (requirements.txt already declared lancedb/sentence-transformers; pip install only)
2. **Task 2: Download bge-m3 model** — human action (no commit; model files are git-ignored)
3. **Task 3: Add electron/resources/models/ to .gitignore** — `f7b3a28` (chore)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `electron/resources/models/bge-m3/` — bge-m3 weight directory (git-ignored runtime asset); contains config.json, tokenizer.json, model.safetensors, and supporting files
- `.gitignore` — added `electron/resources/models/` exclusion rule at line 15

## Decisions Made

- **Flat local-path format vs. HuggingFace hub cache:** Used `model.save(str(target))` to produce a flat directory compatible with `SentenceTransformer(path, local_files_only=True)`. Hub cache format requires network resolution on first load and fails with `local_files_only=True`.
- **CPU-only torch:** Installed via `--index-url https://download.pytorch.org/whl/cpu` to avoid pulling CUDA wheels (1-3 GB overhead). Project embeds no GPU compute; CPU inference is sufficient.
- **.gitignore placement:** Appended after `dist/` following the established trailing-slash pattern; no reordering of existing entries.

## Deviations from Plan

None — plan executed exactly as written. Task 2 was a human-action checkpoint as designed; the human completed it successfully before this continuation agent was spawned.

## Issues Encountered

None. All three tasks completed without errors. `local_files_only=True` reload returned shape (1, 1024) on first attempt.

## User Setup Required

None — model download was a one-time manual step (Task 2) already completed by the user.

## Next Phase Readiness

Wave 1 plans are now unblocked:

- **23-02-PLAN.md** — hiddenimports audit: lancedb/pyarrow/sentence-transformers/torch packages are now installed in .venv, enabling `pyinstaller --debug=imports` to resolve actual import graph
- **23-03-PLAN.md** — Electron env injection: `electron/resources/models/bge-m3/` exists at the expected path; `backendChildEnv()` CTRX_MODELS_DIR injection can now be verified end-to-end

No blockers or concerns.

---
*Phase: CTRX-23-pyinstaller*
*Completed: 2026-06-03*
