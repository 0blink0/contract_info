---
phase: CTRX-14-build-pipeline
reviewed: 2026-05-29T05:30:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - package.json
  - tsconfig.electron.json
  - scripts/build.ps1
  - scripts/build.sh
  - .gitignore
findings:
  critical: 1
  warning: 2
  info: 3
  total: 6
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-05-29T05:30:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Five build-pipeline files were reviewed: the root `package.json` (electron-builder config), `tsconfig.electron.json`, the two build dispatcher scripts (`build.ps1`, `build.sh`), and the updated `.gitignore`.

The TypeScript configuration is sound and the version-injection approach in both build scripts is correct. The electron-builder target definitions, NSIS options, and `extraResources` layout are well-structured. One critical defect was found: the `preload.cjs` file is not present in the packaged asar, meaning the app crashes at startup when Electron tries to load the preload script. Two warnings cover exception-unsafe location management in the PowerShell script and a spurious `electron-store` dependency in the frontend package. Three informational items round out the report.

---

## Critical Issues

### CR-01: `preload.cjs` Is Not Packaged — App Crashes at Startup

**File:** `package.json:34`
**Issue:** The `files` array entry `{ "from": "electron/preload.cjs", "to": "dist/electron/preload.cjs" }` does not produce a file inside the asar in electron-builder 26.x. This was verified by inspecting the built `dist/win-unpacked/resources/app.asar`: zero `.cjs` files are present, yet `electron/main.ts` line 253 unconditionally loads:

```ts
preload: path.join(__dirname, 'preload.cjs')
```

Because `__dirname` inside the packaged main process resolves to the `dist/electron` directory within the asar, Electron looks for `dist/electron/preload.cjs` — which does not exist. `BrowserWindow` creation fails with a "preload file not found" fatal error, making the app unusable.

The TSC-compiled `dist/electron/preload.js` (from `preload.ts`) IS present in the asar via the `dist/electron/**` glob, but `main.ts` never references it — it specifically asks for `.cjs`.

Root cause: electron-builder's default `!dist{,/**/*}` exclusion pattern appears to suppress the explicit `{ from, to }` copy when the destination path begins with `dist/`. The copy is silently dropped; no error is raised at build time.

**Fix (option A — change the `to` destination):** Change the `files` entry so the destination does not fall under the `dist/` exclusion, and update `main.ts` to match:

```json
// package.json — change the files entry:
{ "from": "electron/preload.cjs", "to": "preload.cjs" }
```

```ts
// electron/main.ts line 253 — update the preload path:
preload: path.join(app.getAppPath(), 'preload.cjs'),
```

**Fix (option B — use `extraFiles`):** Move the entry to `extraFiles` so it is copied outside the asar alongside `resources/`:

```json
"extraFiles": [
  { "from": "electron/preload.cjs", "to": "resources/preload.cjs" }
]
```

Then update `main.ts` to `path.join(process.resourcesPath, 'preload.cjs')`.

**Fix (option C — minimal):** Add an explicit top-level glob instead of a `{ from, to }` object — electron-builder resolves globs against the project root before applying exclusions:

```json
"files": [
  "dist/electron/**",
  "electron/preload.cjs",
  { "from": "frontend/dist", "to": "frontend/dist", "filter": ["**/*"] },
  "package.json"
]
```

Then in `main.ts` adjust the preload path to wherever it lands (`path.join(app.getAppPath(), 'electron/preload.cjs')`).

Any of the three options resolves the crash. Option A is cleanest because it avoids the `dist/` collision entirely.

---

## Warnings

### WR-01: `Push-Location` / `Pop-Location` Not Exception-Safe in `build.ps1`

**File:** `scripts/build.ps1:20-33`
**Issue:** Steps 2, 3, and 4 use `Push-Location` / `Pop-Location` without any `try/finally` guard. When `$ErrorActionPreference = 'Stop'` is active, any failure inside the block (e.g. `npm run build` exits non-zero) causes the script to terminate immediately and `Pop-Location` is never called. The PowerShell location stack is left in a dirty state for the duration of the session. While the current script terminates immediately on failure so the stack corruption has no downstream effect within this script run, it is a reliability anti-pattern and would become a real bug if any calling script reuses the session after catching the error.

**Fix:** Wrap each `Push-Location` / working block in `try { } finally { Pop-Location }`:

```powershell
Write-Host "=== Step 2: Vite frontend ==="
Push-Location (Join-Path $Root "frontend")
try {
    npm run build
} finally {
    Pop-Location
}
```

Apply the same pattern to Steps 3 and 4. `build.sh` uses a subshell `(cd ... && ...)` idiom which is already exception-safe and does not share this problem.

---

### WR-02: `electron-store` Listed as a Runtime Dependency in the Frontend Package

**File:** `frontend/package.json:18` *(adjacent context — not in the reviewed file list, but discoverable during cross-file analysis)*

**Note:** This file was read as supporting context; the finding is reported as a Warning because it reflects a package dependency that could mislead future contributors and may cause bundler issues.

`frontend/package.json` lists `electron-store: ^10.1.0` in `dependencies`. `electron-store` is a Node.js main-process library that uses `fs`, `crypto`, and `os` — it cannot run in a browser renderer context. No file under `frontend/src/` imports it, confirming it is unused. Vite does not fail the build because the import never occurs, but:

- The dependency is downloaded during `npm install` in the frontend subtree.
- Any future developer seeing it may attempt to use it from renderer code, producing runtime failures.
- Dependency scanners and auditors will flag it unnecessarily.

**Fix:** Remove `electron-store` from `frontend/package.json` dependencies entirely. Settings are accessed via the IPC bridge (`window.api.loadSettings()` / `window.api.saveSettings()`) — the renderer has no legitimate use for this package.

---

## Info

### IN-01: `dist/` Used as Both TSC Output and electron-builder Output Directory

**File:** `package.json:27`, `tsconfig.electron.json:6`
**Issue:** `tsconfig.electron.json` emits compiled files to `dist/electron/`, while electron-builder is configured with `"directories.output": "dist"` — so NSIS installers, `win-unpacked/`, and `latest.yml` also land in `dist/`. The build scripts run TSC before electron-builder (correct order), and electron-builder does not wipe the entire output directory before running, so there is no actual collision today. However, the shared `dist/` root means a `git clean -fd dist/` or a naive `rm -rf dist/` wipes both TSC output and installer artifacts simultaneously, and CI setups that restore `dist/` from a cache could inadvertently include stale packaged installers.

**Fix:** Consider separating outputs: set electron-builder's `directories.output` to `release/` (or `out/`) while keeping TSC output in `dist/electron/`. Update `files` globs accordingly.

---

### IN-02: `shutil` Imported Inside Loop in `package_backend.sh` Inline Python Block

**File:** `scripts/package_backend.sh:94`
**Issue:** The inline Python heredoc imports `shutil` inside the `for` loop body (line 94: `import shutil`). Python resolves duplicate imports from `sys.modules` on subsequent iterations, so there is no correctness problem, but the import belongs at the top of the script with the other imports for clarity and conventional Python style.

**Fix:**
```python
import json
import shutil  # move here
from datetime import datetime, timezone
from pathlib import Path
import sys
# ... rest of script; remove the in-loop import
```

---

### IN-03: Hardcoded Fallback Version String in `main.ts` Will Silently Use Wrong Binary

**File:** `electron/main.ts:57-58` *(supporting context file)*
**Issue:** The `backendEntrypoint()` function falls back to a hardcoded path containing `v1.2.0` if no `.backend-manifest.json` is found:

```ts
const fallback = process.platform === 'win32'
  ? path.join(resourcesDir, 'ctrx-backend-win-x64-v1.2.0', 'ctrx-backend.exe')
  : path.join(resourcesDir, 'ctrx-backend-linux-x64-v1.2.0', 'ctrx-backend')
```

When the app version is bumped to `1.3.0`, the manifest-based path will work correctly — but if the manifest is ever absent or corrupted, the fallback silently resolves to a non-existent `v1.2.0` binary. The app would fail to start with a confusing "ENOENT" rather than a clear manifest-missing error. The fallback also pins a specific version in source, requiring a manual source edit every release.

**Fix:** Remove the hardcoded fallback path. If `manifestPath` cannot be read or parsed, throw a descriptive error immediately so the failure mode is visible:

```ts
// In the catch block:
throw new Error(`Backend manifest missing or unreadable at ${manifestPath}. Re-run the build pipeline.`)
```

This converts a silent wrong-path failure into a clear startup error.

---

_Reviewed: 2026-05-29T05:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
