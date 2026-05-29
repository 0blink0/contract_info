---
phase: 14-build-pipeline
plan: "02"
subsystem: build-scripts
tags: [electron-builder, build-dispatcher, powershell, bash, semver-validation, version-injection]
dependency_graph:
  requires:
    - 14-01: package.json electron-builder config, tsconfig.electron.json
  provides:
    - scripts/build.ps1: Windows 4-step NSIS build dispatcher (BUILD-02)
    - scripts/build.sh: Linux 4-step AppImage+deb build dispatcher (BUILD-02)
  affects:
    - Wave 2 (14-03): tsc dry-run uses tsconfig.electron.json compiled by Step 3 of build scripts
tech_stack:
  added: []
  patterns:
    - Mandatory PowerShell parameter enforcement for required -Version flag
    - set -euo pipefail + $ErrorActionPreference=Stop for fail-fast semantics
    - --extraMetadata version injection into electron-builder (no package.json source mutation)
    - Push-Location/Pop-Location (PS) and subshell ( ) isolation (Bash) for directory safety
    - Script-relative root resolution via $PSScriptRoot/..(PS) and BASH_SOURCE[0]/..(Bash)
key_files:
  created:
    - path: scripts/build.ps1
      role: Windows 4-step dispatcher — PyInstaller, Vite, tsc, electron-builder NSIS
    - path: scripts/build.sh
      role: Linux 4-step dispatcher — PyInstaller, Vite, tsc, electron-builder AppImage+deb
  modified: []
decisions:
  - "--extraMetadata used exclusively for version injection — package.json source file never modified (avoids dirty git state during CI)"
  - "Push-Location/Pop-Location pairs in build.ps1 mirror package_backend.ps1 idioms for directory isolation"
  - "Subshell ( cd ... && ) in build.sh mirrors package_backend.sh idioms for safe directory isolation"
  - "Ubuntu 22.04 / glibc 2.35 environment note in build.sh header per D-07 (glibc compatibility requirement)"
metrics:
  duration: "~2 minutes"
  completed: "2026-05-29T02:59:08Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 14 Plan 02: Build Dispatcher Scripts Summary

**One-liner:** Windows (NSIS) and Linux (AppImage+deb) 4-step build dispatchers with Mandatory -Version / --version enforcement, semver regex validation, and --extraMetadata version injection into electron-builder.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Write scripts/build.ps1 (Windows 4-step dispatcher) | ac3bafc | scripts/build.ps1 |
| 2 | Write scripts/build.sh (Linux 4-step dispatcher) | 66fb5fd | scripts/build.sh |

## Verification Results

### scripts/build.ps1

- Mandatory -Version param: PASS (PowerShell parameter enforcement)
- Semver validation: PASS (regex `^\d+\.\d+\.\d+$`, throws with "must be semver" message)
- ErrorActionPreference = "Stop": PASS
- Step 1 — package_backend.ps1 -Platform win-x64: PASS
- Step 2 — npm run build in frontend/ with Push-Location isolation: PASS
- Step 3 — npx tsc -p tsconfig.electron.json with Push-Location isolation: PASS
- Step 4 — electron-builder --win --extraMetadata version injection: PASS
- Push-Location / Pop-Location pairs: PASS (3 occurrences each)

### scripts/build.sh

- Missing --version exits 2 + "Usage" message: PASS (verified live: exit:2)
- Bad semver (1.2) exits 2 + "must be semver" message: PASS (verified live: exit:2)
- Bad semver (notasemver) exits 2 + message: PASS (verified live: exit:2)
- set -euo pipefail: PASS
- Shebang #!/usr/bin/env bash: PASS
- Step 1 — package_backend.sh --platform linux-x64: PASS
- Step 2 — npm run build in frontend/ via subshell: PASS
- Step 3 — npx tsc -p tsconfig.electron.json via subshell: PASS
- Step 4 — electron-builder --linux --extraMetadata version injection: PASS
- Ubuntu 22.04 / glibc 2.35 environment note: PASS

### Content Checks

| Check | build.ps1 | build.sh |
|-------|-----------|----------|
| package_backend.ps1/sh reference | 1 | 1 |
| extraMetadata | 1 | 1 |
| tsconfig.electron.json | 1 | 1 |
| Platform identifier | -Platform win-x64 | --platform linux-x64 |

## Deviations from Plan

None - plan executed exactly as written. Both scripts match the complete target shapes from PATTERNS.md exactly.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The version parameter injection mitigation (T-14-05, T-14-06) was implemented: both scripts validate `--version` / `-Version` against `^\d+\.\d+\.\d+$` before any string interpolation, ensuring only digit-and-dot characters can reach the --extraMetadata JSON argument. T-14-07 (silent step failure) mitigated by `$ErrorActionPreference = "Stop"` and `set -euo pipefail`.

## Known Stubs

None. Scripts are complete thin wrappers. No UI rendering, no placeholder text, no hardcoded empty values.

## Self-Check

- [x] scripts/build.ps1 exists: FOUND
- [x] scripts/build.sh exists: FOUND
- [x] Commit ac3bafc exists: FOUND
- [x] Commit 66fb5fd exists: FOUND

## Self-Check: PASSED
