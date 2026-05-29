---
phase: 14-build-pipeline
verified: 2026-05-29T06:30:00Z
status: human_needed
score: 8/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Install CTRX-Setup-1.2.0.exe on a clean Windows 11 VM and confirm app launches past loading screen"
    expected: "Installer completes without Windows Defender quarantine; CTRX loading screen ('CTRX 正在启动后端，请稍候...') appears and app progresses to main interface; resources\\electron\\resources\\.backend-manifest.json present in install directory"
    why_human: "Cannot run installer or observe runtime behavior programmatically; SmartScreen disposition requires human eyes"
  - test: "Run 'bash scripts/build.sh --version 1.2.0' on native Ubuntu 22.04 and verify AppImage and deb artifacts"
    expected: "Build completes; dist/CTRX-1.2.0-x64.AppImage and dist/CTRX-1.2.0-x64.deb are produced; AppImage launches without glibc errors; dpkg -i succeeds and app appears in system menu"
    why_human: "Linux build requires Ubuntu 22.04 host (glibc 2.35 baseline); this verification was run on Windows; Linux artifacts cannot be built or tested here"
---

# Phase 14: Build Pipeline Verification Report

**Phase Goal:** Package and distribute the CTRX desktop app — produce NSIS installer (Windows), AppImage + deb (Linux), with fail-fast 4-step build scripts
**Verified:** 2026-05-29T06:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | package.json has all required fields: name, version, main, type, devDependencies, build with electron-builder config | VERIFIED | `name:"ctrx"`, `main:"dist/electron/main.js"`, `type:"module"`, devDependencies has electron/electron-builder/typescript/@types/node; `build.appId:"com.ctrx.app"` |
| 2 | tsconfig.electron.json compiles electron/*.ts to dist/electron/ with NodeNext, without noEmit | VERIFIED | `module:"NodeNext"`, `moduleResolution:"NodeNext"`, `outDir:"dist/electron"`, `rootDir:"electron"`, noEmit absent; also has `allowImportingTsExtensions` + `rewriteRelativeImportExtensions` (TypeScript 6 requirement — auto-fixed in 14-03) |
| 3 | electron-builder build field covers NSIS (Windows), AppImage (Linux), deb (Linux) with correct artifactName patterns | VERIFIED | `win.target:[{target:"nsis",arch:["x64"]}]`, `linux.target:[AppImage+deb x64]`, `nsis.artifactName:"${productName}-Setup-${version}.${ext}"`, `linux.artifactName:"${productName}-${version}-${arch}.${ext}"` |
| 4 | extraResources targets electron/resources -> electron/resources matching main.ts backendEntrypoint() candidate 3 | VERIFIED | `build.extraResources[0].from:"electron/resources"`, `build.extraResources[0].to:"electron/resources"` — matches `path.join(process.resourcesPath, 'electron', 'resources')` in main.ts |
| 5 | preload.cjs staged at dist/electron/preload.cjs via files[] FileSet | VERIFIED | `{from:"electron/preload.cjs",to:"dist/electron/preload.cjs"}` present in `build.files[]` |
| 6 | scripts/build.ps1 fails fast on missing -Version; has 4 steps, delegates Step 1 to package_backend.ps1 -Platform win-x64, uses -c.extraMetadata.version injection | VERIFIED | Mandatory PowerShell param enforced; `$ErrorActionPreference="Stop"`; Step 1 calls `package_backend.ps1 -Platform win-x64`; Step 4 uses `npx electron-builder --win "-c.extraMetadata.version=$Version"` |
| 7 | scripts/build.sh fails fast with exit 2 on missing --version; has 4 steps, delegates Step 1 to package_backend.sh --platform linux-x64, uses -c.extraMetadata.version injection | VERIFIED | Live-tested: missing --version exits 2 with "Usage" message; bad semver exits 2 with "must be semver"; `set -euo pipefail`; Step 4 uses `npx electron-builder --linux "-c.extraMetadata.version=$VERSION"` |
| 8 | dist/CTRX-Setup-1.2.0.exe exists, produced by scripts/build.ps1 -Version 1.2.0, with correct extraResources layout inside win-unpacked | VERIFIED | File exists at 133MB (139,949,437 bytes); `dist/win-unpacked/resources/electron/resources/.backend-manifest.json` exists; `dist/win-unpacked/resources/electron/resources/ctrx-backend-win-x64-v1.2.0/` exists |
| 9 | CTRX-Setup-1.2.0.exe installs and runs on a clean Windows 11 VM without Windows Defender quarantine | UNCERTAIN | Cannot verify programmatically — requires human |
| 10 | CTRX-1.2.0-x64.AppImage runs on Ubuntu 22.04 (glibc 2.35) | UNCERTAIN | No AppImage in dist/ — Linux build must run on Ubuntu 22.04; this machine is Windows; requires human |
| 11 | CTRX-1.2.0-x64.deb installs via dpkg -i and app appears in system menu | UNCERTAIN | No .deb in dist/ — same reason as AppImage; requires human |

**Score:** 8/11 truths verified (3 require human — SC-1, SC-2, SC-3 from ROADMAP)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `package.json` | electron-builder inline config, devDependencies, name/version/main/type | VERIFIED | All 14 plan acceptance criteria pass; added `win.signAndEditExecutable:false` (code signing out of scope per REQUIREMENTS.md) |
| `tsconfig.electron.json` | tsc compile config for electron/*.ts -> dist/electron/ | VERIFIED | NodeNext module/resolution, outDir correct, noEmit absent; added `allowImportingTsExtensions`+`rewriteRelativeImportExtensions` for TypeScript 6 |
| `build/icon.ico` | Windows NSIS installer icon (non-zero) | VERIFIED | 783 bytes — Pillow-generated placeholder |
| `build/icon.png` | Linux desktop entry icon (non-zero) | VERIFIED | 1881 bytes — Pillow-generated placeholder |
| `scripts/build.ps1` | Windows 4-step dispatcher with Mandatory -Version and fail-fast | VERIFIED | Exists; contains all required patterns; `package_backend.ps1`, `-Platform win-x64`, `electron-builder --win`, `extraMetadata`, `ErrorActionPreference` |
| `scripts/build.sh` | Linux 4-step dispatcher with --version enforcement and fail-fast | VERIFIED | Exists; live-tested fail-fast (exit:2 on both missing and invalid version); contains `package_backend.sh`, `--platform linux-x64`, `electron-builder --linux`, `extraMetadata` |
| `dist/CTRX-Setup-1.2.0.exe` | Windows NSIS installer (>1MB) | VERIFIED | 133MB (139,949,437 bytes) |
| `dist/electron/main.js` | tsc-compiled Electron main process | VERIFIED | 8952 bytes |
| `dist/electron/ipc.js` | tsc-compiled IPC handler | VERIFIED | 2117 bytes |
| `dist/electron/store.js` | tsc-compiled settings store | VERIFIED | 1936 bytes |
| `dist/electron/types/ipc.js` | tsc-compiled type exports | VERIFIED | 11 bytes |
| `dist/CTRX-1.2.0-x64.AppImage` | Linux AppImage | NOT PRESENT | Linux build must run on Ubuntu 22.04; not produced on Windows |
| `dist/CTRX-1.2.0-x64.deb` | Linux deb package | NOT PRESENT | Linux build must run on Ubuntu 22.04; not produced on Windows |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `package.json build.extraResources[0].to` | `electron/main.ts backendEntrypoint() candidate 3` | `process.resourcesPath + '/electron/resources'` | VERIFIED | `to:"electron/resources"` matches the production path in main.ts exactly |
| `package.json build.files[] FileSet` | `electron/main.ts createMainWindow() preload path` | `path.join(__dirname, 'preload.cjs')` | VERIFIED | FileSet `{from:"electron/preload.cjs",to:"dist/electron/preload.cjs"}` present |
| `package.json main` | `dist/electron/main.js` | electron entry point | VERIFIED | `"main":"dist/electron/main.js"` and file exists at 8952 bytes |
| `scripts/build.ps1 Step 1` | `scripts/package_backend.ps1` | `& package_backend.ps1 -Platform win-x64 -Version $Version` | VERIFIED | Pattern present in build.ps1 line 17 |
| `scripts/build.sh Step 1` | `scripts/package_backend.sh` | `bash package_backend.sh --platform linux-x64 --version $VERSION` | VERIFIED | Pattern present in build.sh line 29 |
| `scripts/build.ps1/build.sh Step 4` | electron-builder artifactName | `-c.extraMetadata.version` flag | VERIFIED | Both scripts use `-c.extraMetadata.version=$Version/$VERSION` — correct syntax for electron-builder 26.x (changed from --extraMetadata JSON blob; auto-fixed in 14-03) |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces build scripts and configuration files, not components that render dynamic data.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| build.sh exits 2 with usage when --version omitted | `bash scripts/build.sh 2>&1; echo "exit:$?"` | "Usage: bash scripts/build.sh --version \<semver\>" + exit:2 | PASS |
| build.sh exits 2 with semver error on bad version | `bash scripts/build.sh --version notasemver 2>&1; echo "exit:$?"` | "Version must be semver (e.g. 1.2.0)..." + exit:2 | PASS |
| NSIS installer produced at correct path and size | `ls dist/CTRX-Setup-1.2.0.exe` | 139,949,437 bytes | PASS |
| tsc output files exist | `ls dist/electron/main.js dist/electron/ipc.js dist/electron/store.js` | All present (8952/2117/1936 bytes) | PASS |
| extraResources layout correct in win-unpacked | `ls dist/win-unpacked/resources/electron/resources/` | `.backend-manifest.json` + `ctrx-backend-win-x64-v1.2.0/` present | PASS |

### Probe Execution

No probe scripts defined for this phase. Step 7c: SKIPPED (no `scripts/*/tests/probe-*.sh` for Phase 14).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BUILD-01 | 14-01, 14-03 | electron-builder config produces Windows NSIS (.exe) and Linux AppImage; extraResources references PyInstaller --onedir output | PARTIALLY SATISFIED | NSIS config verified in package.json; dist/CTRX-Setup-1.2.0.exe produced and extraResources layout confirmed in win-unpacked; AppImage config exists in package.json but AppImage artifact not produced on this Windows machine |
| BUILD-02 | 14-02, 14-03 | 4-step build scripts (.ps1 and .sh): PyInstaller → Vite → tsc → electron-builder | SATISFIED | scripts/build.ps1 and build.sh both exist with correct 4-step structure, fail-fast semantics verified; Windows build ran to completion producing CTRX-Setup-1.2.0.exe; Linux build requires Ubuntu 22.04 (script is correct, runtime verification deferred to human) |
| BUILD-03 | 14-01, 14-03 | Linux .deb produced by build pipeline; dpkg -i installable | PARTIALLY SATISFIED | deb target present in package.json linux.target array; no .deb artifact in dist/ (Linux-only build); requires human verification on Ubuntu 22.04 |

All three requirement IDs declared in PLAN frontmatter are accounted for against REQUIREMENTS.md entries.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | No TBD/FIXME/XXX/TODO/PLACEHOLDER markers found | — | — |

No debt markers, no unreferenced stubs, no hardcoded empty data in any Phase 14 file. `build/icon.ico` and `build/icon.png` are acknowledged placeholder icons for internal distribution — documented in SUMMARY and REQUIREMENTS.md explicitly places code signing out of scope.

### Notable Deviations (Auto-Fixed — Not Gaps)

These were discovered during execution and auto-fixed per plan Rule 1/3. They deviate from the PLAN spec but represent correct behavior:

1. **tsconfig.electron.json** — Added `allowImportingTsExtensions:true` and `rewriteRelativeImportExtensions:true`. The 14-01 PLAN spec said not to add `allowImportingTsExtensions`. TypeScript 6 enforces TS5097 error on `.ts` import paths without this flag. The pair is required for emit to work with `.ts` extension imports. The plan must-haves are still satisfied: `module:"NodeNext"`, `outDir:"dist/electron"`, `noEmit` absent.

2. **scripts/build.ps1 and build.sh** — Use `-c.extraMetadata.version=$Version` instead of `--extraMetadata {"version":"..."}` JSON. The plan's key_links pattern said "extraMetadata" — the string "extraMetadata" still appears in both scripts (embedded in `-c.extraMetadata.version`). electron-builder 26.x changed the CLI interface to yargs dot-notation; the old `--extraMetadata` flag silently printed help text. The fix was verified to work (installer produced at 133MB).

3. **package.json** — Added `win.signAndEditExecutable:false`. Not in original plan spec but required to suppress winCodeSign tool download/symlink creation on restricted Windows hosts without Developer Mode. Code signing is explicitly out of scope per REQUIREMENTS.md.

### Human Verification Required

#### 1. Windows Installer Acceptance Test

**Test:** On a clean Windows 11 VM (or current dev machine), run `dist/CTRX-Setup-1.2.0.exe`. If SmartScreen appears, click "More info" then "Run anyway". Complete the installation wizard. Launch CTRX from Start menu or desktop shortcut.

**Expected:**
- Installation completes without errors
- CTRX loading screen appears in Chinese ("CTRX 正在启动后端，请稍候...")
- Application progresses past loading screen to onboarding wizard or main interface (backend starts successfully)
- In installation directory (typically `C:\Users\<user>\AppData\Local\Programs\CTRX`): `resources\electron\resources\.backend-manifest.json` exists and `resources\electron\resources\ctrx-backend-win-x64-v1.2.0\` directory exists

**Why human:** Cannot run an NSIS installer or observe runtime application behavior (Electron window, backend process, UI) programmatically. SmartScreen disposition requires human observation.

**Evidence already available (reduces manual work):** The `dist/win-unpacked/` tree already confirms extraResources layout — `.backend-manifest.json` and `ctrx-backend-win-x64-v1.2.0/` are present. The installer itself is the packaged form of this tree.

#### 2. Linux Build + AppImage + deb Acceptance Test

**Test:** On a **native Ubuntu 22.04** machine (NOT Ubuntu 24.x — glibc baseline requirement), run:
```
bash scripts/build.sh --version 1.2.0
```
Prerequisites: Python + PyInstaller, Node.js, `fakeroot` (`sudo apt install fakeroot`).

**Expected:**
- Build completes through all 4 steps without error
- `dist/CTRX-1.2.0-x64.AppImage` exists
- `dist/CTRX-1.2.0-x64.deb` exists
- `chmod +x dist/CTRX-1.2.0-x64.AppImage && ./dist/CTRX-1.2.0-x64.AppImage` — application launches without glibc version errors
- `sudo dpkg -i dist/CTRX-1.2.0-x64.deb` exits 0; app visible in system application menu

**Why human:** Linux artifacts require a Linux build host (glibc 2.35 baseline; building on Ubuntu 24.x would produce binaries incompatible with 22.04 users). This machine is Windows. The build script is syntactically correct and the electron-builder config is verified, but the end-to-end Linux build must run on Ubuntu 22.04.

### Gaps Summary

No code gaps. All implemented artifacts are present, substantive, and wired. The three UNCERTAIN items are platform-constrained human verifications:

- SC-1 (Windows installer runtime behavior) — artifact exists, runtime acceptance requires human
- SC-2 (AppImage on Ubuntu 22.04) — build script correct but must run on Ubuntu 22.04 to produce artifact
- SC-3 (deb via dpkg) — same constraint as SC-2

These are not code gaps — they are environment-gated acceptance tests that cannot be automated from a Windows development machine. The 14-03 SUMMARY states "Human-approved" but this verification cannot confirm that claim from code inspection alone.

---

_Verified: 2026-05-29T06:30:00Z_
_Verifier: Claude (gsd-verifier)_
