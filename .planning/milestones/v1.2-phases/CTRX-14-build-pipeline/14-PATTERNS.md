# Phase 14: 构建流水线 - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 6 new/modified files
**Analogs found:** 5 / 6 (icon files have no code analog)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `package.json` (root) | config | batch | `frontend/package.json` | role-match (same format; different scope) |
| `tsconfig.electron.json` | config | transform | `frontend/tsconfig.app.json` | role-match (same format; different target) |
| `scripts/build.ps1` | utility | batch | `scripts/package_backend.ps1` | exact (same style: param block, StrictMode, ErrorActionPreference, PSScriptRoot, Write-Host) |
| `scripts/build.sh` | utility | batch | `scripts/package_backend.sh` | exact (same style: set -euo pipefail, while-case arg parsing, ROOT=BASH_SOURCE, echo to stderr) |
| `build/icon.ico` | config | — | none | no analog |
| `build/icon.png` | config | — | none | no analog |

---

## Pattern Assignments

### `package.json` (root) — config, batch

**Analog:** `frontend/package.json` (lines 1-30)

**Structure pattern** (lines 1-30 of frontend/package.json):
```json
{
  "name": "contract-info-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit -p tsconfig.app.json && vite build",
    "preview": "vite preview"
  },
  "dependencies": { ... },
  "devDependencies": {
    "typescript": "~5.7.2",
    "vite": "^6.0.3"
  }
}
```

**What to copy:** Use `"type": "module"` (already in the frontend analog). Add `name`, `version`, `main`, `scripts`, `devDependencies`, and the `build` field. The existing root `package.json` (lines 1-5) currently has only `dependencies: { "electron-store": "^10.1.0" }` — all other fields must be added.

**Complete target shape for root package.json** (derived from RESEARCH.md Pattern 1 + Code Examples):
```json
{
  "name": "ctrx",
  "version": "1.2.0",
  "description": "Contract element extraction — desktop app",
  "author": "blink",
  "license": "UNLICENSED",
  "main": "dist/electron/main.js",
  "type": "module",
  "devDependencies": {
    "electron": "^42.3.0",
    "electron-builder": "^26.8.1",
    "typescript": "^6.0.3",
    "@types/node": "^25.9.1"
  },
  "dependencies": {
    "electron-store": "^10.1.0"
  },
  "scripts": {
    "build:electron": "tsc -p tsconfig.electron.json",
    "dist:win": "electron-builder --win",
    "dist:linux": "electron-builder --linux"
  },
  "build": {
    "appId": "com.ctrx.app",
    "productName": "CTRX",
    "copyright": "Copyright © 2026 blink",
    "directories": {
      "output": "dist",
      "buildResources": "build"
    },
    "files": [
      "dist/electron/**",
      { "from": "frontend/dist", "to": "frontend/dist", "filter": ["**/*"] },
      { "from": "electron/preload.cjs", "to": "dist/electron/preload.cjs" },
      "package.json"
    ],
    "extraResources": [
      {
        "from": "electron/resources",
        "to": "electron/resources",
        "filter": [
          "ctrx-backend-*/**",
          "ctrx-backend-*",
          ".backend-manifest.json"
        ]
      }
    ],
    "win": {
      "target": [{ "target": "nsis", "arch": ["x64"] }],
      "icon": "build/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "perMachine": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "shortcutName": "CTRX",
      "artifactName": "${productName}-Setup-${version}.${ext}"
    },
    "linux": {
      "target": [
        { "target": "AppImage", "arch": ["x64"] },
        { "target": "deb",      "arch": ["x64"] }
      ],
      "category": "Office",
      "artifactName": "${productName}-${version}-${arch}.${ext}"
    }
  }
}
```

**Critical notes:**
- `extraResources.to` must be `"electron/resources"` (not `"."`) so `process.resourcesPath + "/electron/resources"` matches the existing candidate 3 in `main.ts` `backendEntrypoint()` (line 50: `path.join(process.resourcesPath, 'electron', 'resources')`). Zero changes to `main.ts` required.
- `"electron/preload.cjs"` must appear explicitly in `files` as a FileSet with `to: "dist/electron/preload.cjs"` because `dist/electron/**` only catches tsc output. `main.ts` line 253 references `path.join(__dirname, 'preload.cjs')` where `__dirname` resolves to `dist/electron/` after compilation.
- Do NOT add `"directories.renderer"` — this field does not exist in electron-builder's MetadataDirectories interface.

---

### `tsconfig.electron.json` — config, transform

**Analog:** `frontend/tsconfig.app.json` (lines 1-23)

**Structure pattern** (lines 1-23 of frontend/tsconfig.app.json):
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "noEmit": true,
    "strict": true,
    "skipLibCheck": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src/**/*.ts", "src/**/*.vue"]
}
```

**Key divergences from analog** — these must be changed:

| Frontend analog | Electron target | Reason |
|-----------------|-----------------|--------|
| `"module": "ESNext"` | `"module": "NodeNext"` | Node.js ESM requires NodeNext; `main.ts` uses `import.meta.url` |
| `"moduleResolution": "bundler"` | `"moduleResolution": "NodeNext"` | Must match module; Vite bundler resolution not applicable for Node.js |
| `"noEmit": true` | omit (defaults to false) | electron tsconfig MUST emit `.js` files to `dist/electron/` |
| `include: ["src/**/*.ts"]` | `include: ["electron/**/*.ts"]` | Different source root |
| no `outDir` | `"outDir": "dist/electron"` | Required: tsc output destination |
| no `rootDir` | `"rootDir": "electron"` | Keeps output flat in `dist/electron/` |

**Complete target shape for tsconfig.electron.json** (derived from RESEARCH.md Pattern 2):
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist/electron",
    "rootDir": "electron",
    "strict": true,
    "skipLibCheck": true,
    "sourceMap": false,
    "esModuleInterop": true
  },
  "include": ["electron/**/*.ts"],
  "exclude": ["electron/tests/**"]
}
```

**Critical notes:**
- `main.ts` line 7 imports `'./ipc.ts'` with the `.ts` extension. With `module: NodeNext`, TypeScript resolves `.ts` → emits `.js` correctly for Node.js ESM.
- `"exclude": ["electron/tests/**"]` prevents test `.mjs` files from triggering unexpected tsc errors.
- Do NOT copy `"noEmit": true`, `"allowImportingTsExtensions": true`, `"moduleDetection": "force"`, or `"useDefineForClassFields": true` from the frontend analog — none apply here.

---

### `scripts/build.ps1` — utility, batch

**Analog:** `scripts/package_backend.ps1` (lines 1-66, full file)

**Param block pattern** (lines 1-6 of package_backend.ps1):
```powershell
param(
  [Parameter(Mandatory = $true)]
  [string]$Platform,
  [Parameter(Mandatory = $true)]
  [string]$Version
)
```

**Fail-fast pattern** (lines 8-9 of package_backend.ps1):
```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
```

**Root path resolution pattern** (line 11 of package_backend.ps1):
```powershell
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
```

**Precondition check pattern** (lines 18-20 of package_backend.ps1):
```powershell
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
  throw "pyinstaller not found in PATH"
}
```

**Progress reporting pattern** (line 66 of package_backend.ps1):
```powershell
Write-Host "Packaged backend to $TargetDir"
```

**Complete target shape for scripts/build.ps1** (adapted from RESEARCH.md Pattern 4, using analog's established conventions):
```powershell
param(
  [Parameter(Mandatory = $true)]
  [string]$Version
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Validate version format
if (-not ($Version -match '^\d+\.\d+\.\d+$')) {
  throw "Version must be semver (e.g. 1.2.0). Got: '$Version'"
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "=== Step 1: PyInstaller backend ==="
& (Join-Path $PSScriptRoot "package_backend.ps1") -Platform win-x64 -Version $Version

Write-Host "=== Step 2: Vite frontend ==="
Push-Location (Join-Path $Root "frontend")
npm run build
Pop-Location

Write-Host "=== Step 3: tsc electron main process ==="
Push-Location $Root
npx tsc -p tsconfig.electron.json
Pop-Location

Write-Host "=== Step 4: electron-builder (Windows NSIS) ==="
Push-Location $Root
npx electron-builder --win --extraMetadata "{""version"":""$Version""}"
Pop-Location

Write-Host "Build complete. Artifacts in dist/"
```

**Key patterns copied from analog:**
- `param([Parameter(Mandatory = $true)] [string]$Version)` — mirrors analog lines 1-6; PowerShell enforces presence with `-ErrorAction Stop` by default for Mandatory params.
- `Set-StrictMode -Version Latest` + `$ErrorActionPreference = "Stop"` — lines 8-9, fail-fast on any error.
- `$Root = Resolve-Path (Join-Path $PSScriptRoot "..")` — line 11, reliable script-relative root.
- `Push-Location` / `Pop-Location` pairs — idiomatic PowerShell for temporarily changing working directory without side effects.
- `Write-Host "=== Step N: ..."` — consistent progress reporting mirroring analog's single `Write-Host` at end.

**Version injection:** `--extraMetadata` passes the version to electron-builder without modifying `package.json` source. Double-quote escaping `""` in PowerShell string produces the correct JSON.

---

### `scripts/build.sh` — utility, batch

**Analog:** `scripts/package_backend.sh` (lines 1-101, full file)

**Shebang + fail-fast pattern** (lines 1-2 of package_backend.sh):
```bash
#!/usr/bin/env bash
set -euo pipefail
```

**Argument parsing pattern** (lines 4-22 of package_backend.sh):
```bash
PLATFORM=""
VERSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform)
      PLATFORM="${2:-}"
      shift 2
      ;;
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done
```

**Validation + usage pattern** (lines 24-27 of package_backend.sh):
```bash
if [[ -z "$PLATFORM" || -z "$VERSION" ]]; then
  echo "Usage: bash scripts/package_backend.sh --platform <platform> --version <version>" >&2
  exit 2
fi
```

**Root path resolution pattern** (line 29 of package_backend.sh):
```bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
```

**Stderr error reporting pattern** (lines 36-39 of package_backend.sh):
```bash
if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller not found in PATH" >&2
  exit 1
fi
```

**Subshell directory isolation pattern** (implicit in package_backend.sh via pushd-equivalent):
```bash
# Use subshell ( ) to avoid changing caller's $PWD
(cd "$ROOT/frontend" && npm run build)
```

**Complete target shape for scripts/build.sh** (adapted from RESEARCH.md Pattern 5, using analog's established conventions):
```bash
#!/usr/bin/env bash
# scripts/build.sh
# Run on native Ubuntu 22.04 (glibc 2.35) to produce AppImage and .deb.
# Usage: bash scripts/build.sh --version <semver>
set -euo pipefail

VERSION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="${2:-}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Usage: bash scripts/build.sh --version <semver>" >&2
  exit 2
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version must be semver (e.g. 1.2.0). Got: '$VERSION'" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Step 1: PyInstaller backend ==="
bash "$ROOT/scripts/package_backend.sh" --platform linux-x64 --version "$VERSION"

echo "=== Step 2: Vite frontend ==="
(cd "$ROOT/frontend" && npm run build)

echo "=== Step 3: tsc electron main process ==="
(cd "$ROOT" && npx tsc -p tsconfig.electron.json)

echo "=== Step 4: electron-builder (Linux AppImage + deb) ==="
(cd "$ROOT" && npx electron-builder --linux --extraMetadata "{\"version\":\"$VERSION\"}")

echo "Build complete. Artifacts in dist/"
```

**Key patterns copied from analog:**
- `#!/usr/bin/env bash` + `set -euo pipefail` — lines 1-2; fail-fast on unset vars, pipe failures, any non-zero exit.
- `while [[ $# -gt 0 ]]; do case "$1" in` — lines 7-22; same arg-parsing style.
- `if [[ -z "$VERSION" ]]; then ... exit 2` — lines 24-27; same empty-check pattern.
- `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"` — line 29; same root resolution.
- Errors go to `>&2`, exit codes 1/2 match the analog's conventions.

---

### `build/icon.ico` and `build/icon.png` — config, no analog

**No close analog exists.** These are binary image assets, not code files.

**Requirements from RESEARCH.md (Open Questions, item 2):**
- `build/icon.ico`: 256x256, Windows ICO format. Referenced by `win.icon` in the `build` field of `package.json`.
- `build/icon.png`: 512x512, PNG format. Used by Linux desktop entry (AppImage/deb).
- `buildResources` is set to `"build"` in `directories`, so electron-builder looks here by default.
- electron-builder will error if `win.icon` references a missing file.

**Creation approach:** Generate placeholder images programmatically using Python (available on both platforms per RESEARCH.md Environment Availability). A single-color filled square is sufficient for internal distribution.

---

## Shared Patterns

### Fail-Fast Execution Style
**Source:** `scripts/package_backend.ps1` lines 8-9 and `scripts/package_backend.sh` lines 1-2
**Apply to:** `scripts/build.ps1` and `scripts/build.sh`

PowerShell:
```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
```

Bash:
```bash
set -euo pipefail
```

Both scripts stop immediately on first non-zero exit. No error suppression.

### Script-Relative Root Resolution
**Source:** `scripts/package_backend.ps1` line 11 and `scripts/package_backend.sh` line 29
**Apply to:** `scripts/build.ps1` and `scripts/build.sh`

PowerShell:
```powershell
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
```

Bash:
```bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
```

Both patterns work when scripts are called from any working directory — no dependency on `$PWD`.

### Version Semver Validation
**Source:** Established in `scripts/package_backend.sh` line 24 (empty check); extended in RESEARCH.md Pattern 4/5 with regex
**Apply to:** Both build scripts

PowerShell:
```powershell
if (-not ($Version -match '^\d+\.\d+\.\d+$')) {
  throw "Version must be semver (e.g. 1.2.0). Got: '$Version'"
}
```

Bash:
```bash
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version must be semver (e.g. 1.2.0). Got: '$VERSION'" >&2
  exit 2
fi
```

### Version Injection Without Source Mutation
**Source:** RESEARCH.md Code Examples, Pitfall 1
**Apply to:** Step 4 invocation in both build scripts

```powershell
# PowerShell — double-quote escaping inside double-quoted string
npx electron-builder --win --extraMetadata "{""version"":""$Version""}"
```

```bash
# Bash — backslash escape inside double-quoted string
npx electron-builder --linux --extraMetadata "{\"version\":\"$VERSION\"}"
```

Avoids `npm version --no-git-tag-version` which would modify the committed source file.

### ESM Module Configuration
**Source:** `frontend/package.json` line 5, `frontend/tsconfig.app.json` lines 7-9
**Apply to:** root `package.json` (must have `"type": "module"`) and `tsconfig.electron.json` (must NOT use `"moduleResolution": "bundler"`)

The frontend uses `"moduleResolution": "bundler"` which is Vite-specific. The electron tsconfig uses `"module": "NodeNext"` / `"moduleResolution": "NodeNext"` — do not copy the bundler resolution into the electron config.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `build/icon.ico` | config | — | No ICO image files exist in the codebase |
| `build/icon.png` | config | — | No PNG icon files exist in the codebase |

**Planner guidance:** Generate placeholder icons using Python's `Pillow` library or PowerShell's `System.Drawing`. A 256x256 solid-color `.ico` and a 512x512 solid-color `.png` satisfy electron-builder's requirements for internal distribution.

---

## Metadata

**Analog search scope:** `scripts/`, `frontend/`, root `package.json`, `electron/main.ts`
**Files scanned:** 7 (package_backend.ps1, package_backend.sh, package.json root, frontend/package.json, frontend/tsconfig.json, frontend/tsconfig.app.json, electron/main.ts)
**Pattern extraction date:** 2026-05-29
