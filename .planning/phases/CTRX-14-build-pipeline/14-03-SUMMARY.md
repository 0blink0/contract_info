---
phase: 14-build-pipeline
plan: "03"
subsystem: build-smoke-test
tags: [electron-builder, nsis, tsc, typescript6, extraResources, pyinstaller]

requires:
  - phase: 14-01
    provides: package.json electron-builder config, tsconfig.electron.json
  - phase: 14-02
    provides: scripts/build.ps1 + build.sh dispatchers

provides:
  - dist/CTRX-Setup-1.2.0.exe (Windows NSIS installer, 133MB)
  - dist/electron/{main,ipc,store}.js + types/ipc.js (tsc-compiled Electron main)
  - Verified extraResources layout in dist/win-unpacked/resources/electron/resources/

affects:
  - Human verification gate (Task 2): Windows installer launch + Linux build

tech-stack:
  added: []
  patterns:
    - TypeScript 6 + NodeNext: requires allowImportingTsExtensions + rewriteRelativeImportExtensions when using .ts import paths with emit
    - electron-builder 26.x: version injection via -c.extraMetadata.version=<V> (not --extraMetadata JSON)
    - signAndEditExecutable=false skips winCodeSign symlink extraction (required on restricted Windows hosts without Developer Mode)

key-files:
  created:
    - path: dist/CTRX-Setup-1.2.0.exe
      role: Windows NSIS installer (133MB) produced by electron-builder 26.8.1
  modified:
    - path: tsconfig.electron.json
      role: Added allowImportingTsExtensions + rewriteRelativeImportExtensions for TypeScript 6 compatibility
    - path: scripts/build.ps1
      role: Fixed electron-builder version injection flag (--extraMetadata -> -c.extraMetadata.version)
    - path: scripts/build.sh
      role: Same fix as build.ps1 for Linux build
    - path: package.json
      role: Added win.signAndEditExecutable=false to skip code signing on restricted Windows hosts

key-decisions:
  - "allowImportingTsExtensions + rewriteRelativeImportExtensions required in tsconfig.electron.json — TypeScript 6 enforces TS5097 when .ts extensions appear in import paths without allowImportingTsExtensions; rewriteRelativeImportExtensions enables emit (otherwise allowImportingTsExtensions requires noEmit)"
  - "electron-builder 26.x uses -c.extraMetadata.version=X not --extraMetadata JSON blob; old syntax silently treated as unknown argument and printed help text without building"
  - "signAndEditExecutable=false added to package.json win config — electron-builder tries to extract winCodeSign (macOS codesign tools) even on Windows, which requires symlink creation (fails without Developer Mode/admin); code signing is out of scope per REQUIREMENTS.md"

patterns-established:
  - "TypeScript 6 NodeNext emit pattern: allowImportingTsExtensions + rewriteRelativeImportExtensions pair — must both be present for .ts imports to work with file emission"

requirements-completed:
  - BUILD-01
  - BUILD-02
  - BUILD-03

duration: ~25min
completed: "2026-05-29"
---

# Phase 14 Plan 03: Smoke Test and Acceptance Gate Summary

**tsc compiles 4 electron TS files without errors; dist/CTRX-Setup-1.2.0.exe produced (133MB) with correct extraResources layout; 7 Phase 13 electron tests pass; checkpoint reached for human installer verification**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-29T03:00:00Z
- **Completed:** 2026-05-29T03:25:00Z (Task 1); Task 2 is human-verify checkpoint
- **Tasks:** 2/2 complete (Task 1 automated + Task 2 human-approved)
- **Files modified:** 4

## Accomplishments

- Fixed 3 TypeScript compilation blockers (TS5097 on all .ts import paths in main.ts and ipc.ts) by adding allowImportingTsExtensions + rewriteRelativeImportExtensions to tsconfig.electron.json
- Fixed electron-builder version injection (--extraMetadata -> -c.extraMetadata.version=1.2.0) in both build.ps1 and build.sh
- Fixed Windows NSIS build failure (winCodeSign symlink extraction) by adding signAndEditExecutable: false
- Produced dist/CTRX-Setup-1.2.0.exe (133MB) with confirmed extraResources layout: dist/win-unpacked/resources/electron/resources/.backend-manifest.json + ctrx-backend-win-x64-v1.2.0/ present
- All 7 Phase 13 electron tests pass (ipc.test.mjs, lifecycle.test.mjs, settings-restart.test.mjs)

## Task Commits

1. **Task 1: tsc dry-run and Windows build smoke test** - `7019b8d` (feat)

2. **Task 2: Human verify Windows installer behavior and Linux build** — Human-approved ✓

## Files Created/Modified

- `dist/CTRX-Setup-1.2.0.exe` — Windows NSIS installer (133MB, produced by electron-builder 26.8.1)
- `dist/electron/main.js` — tsc-compiled Electron main process (8952 bytes)
- `dist/electron/ipc.js` — tsc-compiled IPC handler (2117 bytes)
- `dist/electron/store.js` — tsc-compiled settings store (1936 bytes)
- `dist/electron/types/ipc.js` — tsc-compiled type exports (11 bytes)
- `tsconfig.electron.json` — Added TypeScript 6 compatibility flags
- `scripts/build.ps1` — Fixed electron-builder version injection flag
- `scripts/build.sh` — Same fix for Linux
- `package.json` — Added win.signAndEditExecutable=false

## Decisions Made

- TypeScript 6 requires explicit `allowImportingTsExtensions: true` when `.ts` extensions are used in import paths. Combined with `rewriteRelativeImportExtensions: true`, the compiler rewrites `./ipc.ts` to `./ipc.js` in emitted output — matching the NodeNext ESM resolution contract.
- electron-builder 26.x changed the CLI interface for config overrides to yargs dot-notation. The documented `--extraMetadata {"version":"X"}` format in electron-builder older docs is no longer valid; the correct form is `-c.extraMetadata.version=X`.
- Code signing is disabled via `signAndEditExecutable: false` in `package.json` build.win config. This is aligned with REQUIREMENTS.md which explicitly puts code signing out of scope for v1.2. The `winCodeSign` tool downloads macOS codesign dylibs and attempts to create symlinks, which fails on Windows without Developer Mode.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TypeScript 6 TS5097 compilation error on .ts import paths**
- **Found during:** Task 1 Step A (tsc --noEmit)
- **Issue:** TypeScript 6 enforces TS5097: "An import path can only end with a '.ts' extension when 'allowImportingTsExtensions' is enabled." — all three electron source files (main.ts, ipc.ts, store.ts) use `./ipc.ts`, `./store.ts`, `./types/ipc.ts` import syntax. tsc exited with 3 errors.
- **Fix:** Added `"allowImportingTsExtensions": true` and `"rewriteRelativeImportExtensions": true` to tsconfig.electron.json compilerOptions. The pair enables TypeScript to accept .ts imports AND rewrite them to .js in emitted output (required since allowImportingTsExtensions alone requires noEmit or emitDeclarationOnly).
- **Files modified:** tsconfig.electron.json
- **Verification:** `npx tsc -p tsconfig.electron.json --noEmit` exits 0; `npx tsc -p tsconfig.electron.json` produces dist/electron/{main,ipc,store}.js + types/ipc.js
- **Committed in:** 7019b8d

**2. [Rule 1 - Bug] electron-builder --extraMetadata flag not recognized in 26.x**
- **Found during:** Task 1 Step D (first build.ps1 run)
- **Issue:** `npx electron-builder --win --extraMetadata '{"version":"1.2.0"}'` printed "Unknown argument: extraMetadata" and displayed the electron-builder help text instead of building. The NSIS step was silently skipped; script exited 0 because PS1 `$ErrorActionPreference=Stop` only triggers on PowerShell errors, not on npx writing to stdout.
- **Fix:** Changed to yargs dot-notation `-c.extraMetadata.version=$Version` in build.ps1 and `-c.extraMetadata.version=$VERSION` in build.sh. Verified the flag is accepted by electron-builder 26.8.1.
- **Files modified:** scripts/build.ps1, scripts/build.sh
- **Verification:** Second build run showed "building target=nsis file=dist\CTRX-Setup-1.2.0.exe" in electron-builder output
- **Committed in:** 7019b8d

**3. [Rule 1 - Bug] winCodeSign symlink extraction fails on restricted Windows host**
- **Found during:** Task 1 Step D (second build.ps1 run after --extraMetadata fix)
- **Issue:** electron-builder downloads winCodeSign-2.6.0.7z containing macOS codesign dylibs, then tries to extract it with 7-Zip using `-snld` (no symlinks). The archive contains macOS symbolic links (libcrypto.dylib, libssl.dylib) which 7-Zip tries to create as NTFS symlinks — failing with "Cannot create symbolic link: Client does not hold the required privileges". This blocks the packaging step even though code signing is not configured (no CSC_LINK or certificate).
- **Fix:** Added `"signAndEditExecutable": false` to `package.json` build.win config. This causes electron-builder to skip both the executable resource update (asar integrity) and the winCodeSign tool download entirely. The NSIS installer itself still builds correctly.
- **Files modified:** package.json
- **Verification:** Build output shows "building target=nsis file=dist\CTRX-Setup-1.2.0.exe archs=x64 oneClick=false perMachine=false" followed by successful NSIS build without winCodeSign errors. dist/CTRX-Setup-1.2.0.exe produced at 133MB.
- **Committed in:** 7019b8d

**4. [Rule 3 - Blocking] npm install missing devDependencies (typescript, electron, electron-builder)**
- **Found during:** Task 1 Step A (npx tsc --noEmit)
- **Issue:** node_modules/.bin/ only contained `semver` — devDependencies (electron, electron-builder, typescript, @types/node) were not installed. The 14-01 SUMMARY reported npm install as completed but on the current working tree the devDependencies were absent.
- **Fix:** Ran `npm install` which added 272 packages including typescript 6.0.3, electron-builder 26.8.1, electron 42.3.0, and @types/node. package-lock.json updated automatically.
- **Files modified:** (package-lock.json updated on disk, already tracked in 14-01 commit 81c5ca8)
- **Verification:** `ls node_modules/.bin/ | grep tsc` returns `tsc`, `tsc.cmd`, `tsc.ps1`
- **Committed in:** Not committed separately — package-lock.json already tracked; no new files

---

**Total deviations:** 4 auto-fixed (3 Rule 1 bugs, 1 Rule 3 blocking)
**Impact on plan:** All auto-fixes necessary for the build to function. No scope creep. signAndEditExecutable=false is explicitly aligned with REQUIREMENTS.md (code signing out of scope for v1.2).

## Verification Results (Task 1)

| Step | Check | Result |
|------|-------|--------|
| A | `npx tsc --noEmit` exits 0 | PASS |
| B | dist/electron/main.js exists (8952 bytes) | PASS |
| B | dist/electron/ipc.js exists (2117 bytes) | PASS |
| B | dist/electron/store.js exists (1936 bytes) | PASS |
| B | dist/electron/types/ipc.js exists (11 bytes) | PASS |
| C | 7/7 electron tests pass | PASS |
| D | scripts/build.ps1 -Version 1.2.0 exits 0 | PASS |
| E | dist/CTRX-Setup-1.2.0.exe exists (133MB) | PASS |
| E | Filename exactly "CTRX-Setup-1.2.0.exe" | PASS |
| E | extraResources: resources/electron/resources/.backend-manifest.json | PASS |
| E | extraResources: resources/electron/resources/ctrx-backend-win-x64-v1.2.0/ | PASS |

## Issues Encountered

- npm install was required on the working tree before any npx commands would work — devDependencies were not pre-installed despite being present in package.json (likely because 14-01 ran in a different context or the node_modules state was reset).

## Known Stubs

None. The NSIS installer is a real artifact. No UI or data stubs.

## Threat Surface Scan

No new network endpoints, auth paths, or trust-boundary file access patterns introduced. The `signAndEditExecutable: false` change actually reduces surface (skips downloading and running winCodeSign tools). T-14-09 (SmartScreen) and T-14-10 (extraResources path) are addressed — extraResources layout verified in win-unpacked.

## Next Phase Readiness

- Phase 14 all three BUILD requirements verified. Phase ready for /gsd:verify-work.
- Linux build (scripts/build.sh) runs on Ubuntu 22.04 — human confirmed acceptance.

## Self-Check

- [x] dist/CTRX-Setup-1.2.0.exe exists (133MB): FOUND
- [x] dist/electron/main.js exists: FOUND
- [x] dist/electron/ipc.js exists: FOUND
- [x] dist/electron/store.js exists: FOUND
- [x] dist/win-unpacked/resources/electron/resources/.backend-manifest.json exists: FOUND
- [x] dist/win-unpacked/resources/electron/resources/ctrx-backend-win-x64-v1.2.0/ exists: FOUND
- [x] Commit 7019b8d exists: FOUND

## Self-Check: PASSED

---
*Phase: 14-build-pipeline*
*Completed: 2026-05-29 — all tasks complete, human verification approved*
