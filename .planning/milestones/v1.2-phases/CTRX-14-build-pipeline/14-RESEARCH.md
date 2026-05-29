# Phase 14: 构建流水线 - Research

**Researched:** 2026-05-29
**Domain:** electron-builder packaging — NSIS (Windows), AppImage + deb (Linux), TypeScript compilation, build scripts
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** electron-builder 构建配置内联到根 `package.json` 的 `build` 字段，不拆独立 `electron-builder.yml`。根 package.json 需同步补齐 `name`、`version`、`main`、`devDependencies` 等字段。
- **D-02:** TypeScript 编译（tsc）产物输出到 `dist/electron/`；根 `package.json` 的 `main` 字段指向 `dist/electron/main.js`。
- **D-03:** Vite 前端输出保持在 `frontend/dist/`（不改变现有 vite.config），electron-builder 的 `directories.renderer` 设为 `frontend/dist`。
- **D-04:** 新建 `scripts/build.ps1`（Windows）和 `scripts/build.sh`（Linux）作为 4-step 薄层调度器：Step 1 直接调用 `scripts/package_backend.ps1`（或 `package_backend.sh`）完成 PyInstaller 打包与 manifest 更新，不重复内联 PyInstaller 逻辑。
- **D-05:** 版本号通过脚本参数传入：`scripts/build.ps1 -Version 1.2.0`。两个脚本均需校验版本参数存在，否则 fail-fast。
- **D-06:** 构建脚本保留在 `scripts/` 目录，与现有 `package_backend.ps1` 保持集中。
- **D-07:** Linux 构建环境交由 Claude 酌情决定（推荐 native ubuntu:22.04，遵循 STATE.md glibc 2.35 兼容性约束）。

### Claude's Discretion

- 根 `package.json` 的 `appId`、`productName`、`author`、`version` 等标识符具体值。
- `extraResources` glob 模式（覆盖 `electron/resources/ctrx-backend-*`）与 `asarUnpack` 的具体配置。
- Linux `.sh` 脚本的 shebang 与容器化提示注释写法。
- electron-builder NSIS/Linux target 的细粒度参数（图标、安装目录、菜单项等）。

### Deferred Ideas (OUT OF SCOPE)

- 自动更新（auto-update）：需代码签名基础设施，明确排除在 v1.2 范围之外。
- Windows 代码签名：内部分发暂不需要，out-of-scope。
- Linux 构建的 Docker 化或 CI 自动化：当前以手动 native ubuntu:22.04 为基准，CI 集成可在 v1.3 评估。
- Linux clean VM 验收补跑（Phase 12 deferred）：不阻塞 Phase 14 规划，可在 Phase 14 验收时一并补齐。

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BUILD-01 | electron-builder 配置产出 Windows NSIS 安装包（`.exe`）和 Linux AppImage，`extraResources` 引用 PyInstaller `--onedir` 产物目录，`asarUnpack` 排除大型二进制 | Standard Stack 和 Architecture Patterns 章节覆盖 electron-builder build 字段完整配置 |
| BUILD-02 | 提供 4 步构建脚本（PowerShell `.ps1` 和 Bash `.sh` 各一份）：① PyInstaller → ② Vite → ③ tsc → ④ electron-builder | Code Examples 章节提供两个脚本的完整骨架 |
| BUILD-03 | 构建流水线同时产出 Linux `.deb` 安装包，可通过 `dpkg -i` 安装 | Standard Stack 的 linux.target 配置覆盖 AppImage + deb 双目标 |

</phase_requirements>

---

## Summary

Phase 14 delivers the final distribution packaging for CTRX: a one-command build that produces a Windows NSIS installer, a Linux AppImage, and a Linux .deb package. The technical domain has three independent sub-problems that must be solved in coordination: (1) compiling `electron/main.ts` and sibling `.ts` files to `dist/electron/` using a dedicated tsconfig, (2) configuring electron-builder to correctly assemble all three artifact types — placing the PyInstaller `--onedir` binary outside the ASAR archive via `extraResources`, and (3) writing thin 4-step dispatcher scripts in PowerShell and Bash.

The existing codebase is well-prepared. Phase 12 established the `electron/resources/ctrx-backend-win-x64-v1.2.0` bundle and the `scripts/package_backend.ps1` / `package_backend.sh` wrappers. Phase 13 delivered `electron/main.ts` which already uses ESM syntax (`import.meta.url`) and the production path `app.getAppPath()` to locate `frontend/dist/index.html`. These choices have direct consequences for how the root `package.json` and `tsconfig.electron.json` must be structured.

**Critical finding:** `directories.renderer` is NOT a valid electron-builder configuration field — the `MetadataDirectories` interface only has `app`, `buildResources`, and `output`. The locked decision D-03 to set `directories.renderer = frontend/dist` cannot be implemented literally. Instead, `frontend/dist` must be included via the `files` array as a FileSet with `from: "frontend/dist"` and `to: "frontend/dist"`. The `main.ts` already calls `path.join(app.getAppPath(), 'frontend', 'dist', 'index.html')` which expects this layout inside the ASAR.

**Primary recommendation:** Root `package.json` with `"type":"module"`, `"main":"dist/electron/main.js"`, and a `build` field containing inline electron-builder config. Separate `tsconfig.electron.json` with `"module":"NodeNext"`, `"moduleResolution":"NodeNext"`, `"outDir":"dist/electron"`. Use `extraResources` with a glob FileSet `{from:"electron/resources",to:".",filter:["ctrx-backend-*/**","ctrx-backend-*",".backend-manifest.json"]}` to copy the entire backend bundle outside ASAR. The PyInstaller `--onedir` binary already avoids AV heuristics by not self-extracting; no `asarUnpack` is needed for it because it lives in `extraResources`, not inside the ASAR.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| tsc compilation (electron/*.ts → dist/electron/) | Build Script | — | Offline compile step, not runtime; must precede electron-builder |
| Vite frontend build (frontend/src → frontend/dist/) | Build Script | — | Frontend already built separately; must precede electron-builder |
| PyInstaller backend bundle (ctrx-backend-win/linux) | Build Script | — | Step 1 delegated to existing package_backend.ps1/.sh |
| ASAR packaging (dist/electron/ + frontend/dist/) | electron-builder | — | Handled by files field in build config |
| extraResources (electron/resources/ backend binaries) | electron-builder | — | Binary stays outside ASAR for direct filesystem access |
| NSIS installer generation | electron-builder | Windows OS | Requires Windows host to build Windows targets |
| AppImage + deb generation | electron-builder | Ubuntu 22.04 host | Requires Linux host; cross-compile unreliable for native modules |
| Version propagation (script param → package.json) | Build Scripts | — | Scripts patch version before invoking electron-builder |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| electron | 42.3.0 | Desktop shell framework | Latest stable; already depended on in Phase 13 work [VERIFIED: npm registry] |
| electron-builder | 26.8.1 | Cross-platform packaging and installers | De-facto standard for Electron distribution [VERIFIED: npm registry] |
| typescript | 6.0.3 | Compile electron/*.ts → dist/electron/*.js | Already used in frontend; separate tsconfig for main process [VERIFIED: npm registry] |
| @types/node | 25.9.1 | Type definitions for Node.js builtins used in main.ts | Required for `fs`, `path`, `child_process` imports [VERIFIED: npm registry] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| electron-store | 10.1.0 (pinned) | Settings persistence in main process | Already installed; Phase 13 dependency. Pin to v10 for CommonJS/ESM compatibility [VERIFIED: npm registry] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tsc` direct compile | `esbuild` or `tsup` | esbuild is faster but adds a dev dependency; tsc is already available via frontend devDependencies, so no new install needed |
| `extraResources` for backend binary | `extraFiles` | `extraFiles` copies to app root on Windows/Linux (same directory as the `.exe`); `extraResources` copies to the `resources/` directory — which is what `main.ts` expects via `process.resourcesPath` / `__dirname` relative lookup |

**Installation (root package.json devDependencies additions):**
```bash
npm install --save-dev electron electron-builder typescript @types/node
```

**Version verification (run before writing final plan):**
```bash
npm view electron version          # 42.3.0 confirmed
npm view electron-builder version  # 26.8.1 confirmed
npm view typescript version        # 6.0.3 confirmed
npm view @types/node version       # 25.9.1 confirmed
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| electron | npm | ~10 yrs | Very high | github.com/electron/electron | [OK] | Approved |
| electron-builder | npm | ~9 yrs | Very high | github.com/electron-userland/electron-builder | [OK] | Approved |
| typescript | npm | ~12 yrs | Very high | github.com/microsoft/TypeScript | [OK] | Approved |
| @types/node | npm | ~9 yrs | Very high | github.com/DefinitelyTyped/DefinitelyTyped | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*All four packages passed slopcheck verification.*

---

## Architecture Patterns

### System Architecture Diagram

```
scripts/build.ps1 or scripts/build.sh
  │
  ├── Step 1: package_backend.ps1 / package_backend.sh
  │     └── pyinstaller ctrx_backend.spec → dist/ctrx-backend/
  │           └── copy → electron/resources/ctrx-backend-<platform>-v<version>/
  │                 └── update .backend-manifest.json
  │
  ├── Step 2: npm run build (frontend/)
  │     └── vue-tsc --noEmit && vite build → frontend/dist/
  │
  ├── Step 3: npx tsc -p tsconfig.electron.json
  │     └── electron/*.ts → dist/electron/main.js
  │                          dist/electron/ipc.js
  │                          dist/electron/store.js
  │                          dist/electron/types/ipc.js
  │
  └── Step 4: npx electron-builder [--win | --linux]
        │
        ├── ASAR archive: app.asar
        │     ├── dist/electron/**          (tsc output — main process)
        │     ├── frontend/dist/**          (vite output — renderer)
        │     ├── electron/preload.cjs      (CJS preload — NOT compiled by tsc)
        │     └── package.json
        │
        ├── extraResources → resources/
        │     ├── ctrx-backend-win-x64-v1.2.0/   (onedir bundle)
        │     └── .backend-manifest.json
        │
        ├── Windows output: dist/CTRX-Setup-1.2.0.exe  (NSIS)
        └── Linux output:   dist/CTRX-1.2.0.AppImage
                            dist/CTRX-1.2.0.deb
```

### Recommended Project Structure

```
contract_info/
├── electron/
│   ├── main.ts              # source (compiled by tsc)
│   ├── ipc.ts               # source (compiled by tsc)
│   ├── store.ts             # source (compiled by tsc)
│   ├── preload.cjs          # CJS — already exists, NOT compiled by tsc
│   ├── types/ipc.ts         # source (compiled by tsc)
│   └── resources/
│       ├── .backend-manifest.json
│       └── ctrx-backend-win-x64-v1.2.0/   (Phase 12 output)
├── frontend/
│   ├── package.json         # separate vite project
│   └── dist/                # vite build output — included in ASAR via files[]
├── scripts/
│   ├── package_backend.ps1  # existing — called by Step 1
│   ├── package_backend.sh   # existing — called by Step 1
│   ├── build.ps1            # NEW — 4-step dispatcher (Windows)
│   └── build.sh             # NEW — 4-step dispatcher (Linux)
├── dist/
│   ├── ctrx-backend/        # pyinstaller temp output (pre-copy)
│   └── electron/            # tsc output — main.js, ipc.js, store.js ...
├── tsconfig.electron.json   # NEW — tsc config for electron/*.ts
└── package.json             # ROOT — add name/version/main/build/devDeps
```

### Pattern 1: Root package.json build field (electron-builder inline config)

**What:** All electron-builder configuration lives in the `build` key of the root `package.json`. No external `electron-builder.yml`.

**When to use:** Always (locked by D-01).

```json
{
  "name": "ctrx",
  "version": "1.2.0",
  "description": "Contract element extraction and Excel export",
  "author": "blink",
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
    "dist": "electron-builder"
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
      "frontend/dist/**",
      "electron/preload.cjs",
      "package.json"
    ],
    "extraResources": [
      {
        "from": "electron/resources",
        "to": ".",
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
        { "target": "deb", "arch": ["x64"] }
      ],
      "category": "Office",
      "artifactName": "${productName}-${version}-${arch}.${ext}"
    }
  }
}
```

**Source:** [CITED: electron.build/docs/configuration/] [CITED: electron.build/nsis.html]

### Pattern 2: tsconfig.electron.json for ESM main process

**What:** Separate tsconfig that compiles only `electron/*.ts` to `dist/electron/`, targeting Node.js ESM.

**When to use:** Step 3 of the build script. The frontend's `tsconfig.json` uses `"noEmit": true` and `"moduleResolution": "bundler"` — it cannot compile the main process. A dedicated config is required.

**Critical constraint from code inspection:** `main.ts` uses `import.meta.url` (ESM) and imports `.ts` files with extensions (`import './ipc.ts'`). TypeScript must emit `.js` files that preserve the ESM semantics. With `"module": "NodeNext"` and `"type": "module"` in package.json, TypeScript emits `import './ipc.js'` for `import './ipc.ts'` — correct for Node.js ESM resolution.

```json
// tsconfig.electron.json  (Source: [CITED: TypeScript NodeNext module docs])
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

**Note:** Do NOT include `"noEmit": true` — that is the frontend tsconfig pattern. The electron tsconfig must emit files.

**Source:** [CITED: electronjs.org/docs/latest/tutorial/esm], [CITED: typescriptlang.org/tsconfig/]

### Pattern 3: extraResources for PyInstaller --onedir binary

**What:** `extraResources` copies `electron/resources/` content to the installed app's `resources/` directory, accessible at `process.resourcesPath` at runtime.

**When to use:** Always for external native binaries. The PyInstaller `--onedir` bundle is a directory tree with hundreds of files — it must live outside ASAR so Node.js can spawn the executable directly.

**Why NOT asarUnpack:** `asarUnpack` is for files that are inside ASAR but need filesystem presence at runtime. Since the backend bundle goes via `extraResources`, it never enters the ASAR — no `asarUnpack` entry needed for it.

**Path at runtime:** The `main.ts` already has three candidate resolution paths:
1. `path.join(__dirname, 'resources')` — development fallback
2. `path.join(app.getAppPath(), 'electron', 'resources')` — development source path
3. `path.join(process.resourcesPath, 'electron', 'resources')` — this path is wrong for production

**Critical:** With the `extraResources` config above (`from: "electron/resources"`, `to: "."`), the backend bundle lands at `<resources>/ctrx-backend-win-x64-v1.2.0/` and `.backend-manifest.json` lands at `<resources>/.backend-manifest.json`. The production path should be `process.resourcesPath` directly (not `process.resourcesPath/electron/resources`). The `main.ts` `backendEntrypoint()` function checks for `.backend-manifest.json` via `fs.existsSync` — the manifest lookup at `process.resourcesPath` will succeed if `to: "."` is used.

**Source:** [CITED: electron.build/docs/contents/]

### Pattern 4: build.ps1 4-step dispatcher

**What:** Thin PowerShell wrapper that validates version, runs 4 steps in sequence, and stops on first failure.

**When to use:** On Windows host to produce the NSIS installer.

```powershell
# scripts/build.ps1  (Source: [ASSUMED] — based on existing package_backend.ps1 style)
param(
  [Parameter(Mandatory = $true)]
  [string]$Version
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Validate version format (basic check)
if (-not ($Version -match '^\d+\.\d+\.\d+')) {
  throw "Version parameter must be in semver format (e.g. 1.2.0). Got: '$Version'"
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
npx electron-builder --win
Pop-Location

Write-Host "Build complete. Artifacts in dist/"
```

### Pattern 5: build.sh 4-step dispatcher

**What:** Bash equivalent for Linux host to produce AppImage + deb.

**When to use:** On Ubuntu 22.04 host (glibc 2.35 baseline per STATE.md).

```bash
#!/usr/bin/env bash
# scripts/build.sh
# Run on native Ubuntu 22.04 (glibc 2.35) to produce AppImage and .deb
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

# Validate semver
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
(cd "$ROOT" && npx electron-builder --linux)

echo "Build complete. Artifacts in dist/"
```

### Anti-Patterns to Avoid

- **`directories.renderer` in build config:** This field does NOT exist in electron-builder's `MetadataDirectories` interface. The locked decision D-03 means `frontend/dist` content — use `files` FileSet instead. [VERIFIED: electron.build/app-builder-lib.Interface.MetadataDirectories.html returned 404 confirming it is not documented]
- **`asarUnpack` for the backend binary:** The binary lives in `extraResources`, not inside ASAR. Adding it to `asarUnpack` does nothing and may confuse future maintainers.
- **`"type":"commonjs"` in root package.json:** The existing `main.ts` uses ESM syntax. Root package must have `"type":"module"` (or the compiled `.js` files must use `.mjs` extensions). With `"type":"module"` and `"module":"NodeNext"` in tsconfig, `.js` output is valid ESM.
- **Building Linux targets on Windows host:** electron-builder can attempt cross-build but the PyInstaller binary must be built on Linux. Step 1 of `build.sh` runs `package_backend.sh` which requires Python+pyinstaller on a Linux machine. Always run `build.sh` on a native Ubuntu 22.04 machine.
- **Including `electron/resources/**` in `files`:** The `electron/resources/` backend bundle belongs in `extraResources`, not in the ASAR `files`. Including it in `files` would pack hundreds of MB of binary files into the ASAR, making startup extremely slow.
- **Forgetting `electron/preload.cjs` in `files`:** The preload script is a `.cjs` file (not compiled by tsc). It must appear in the `files` array explicitly, because the `dist/electron/**` glob won't catch it.
- **`electron-builder --win --linux` from a single machine:** Windows-only machines can only build Windows targets. Linux-only machines can only build Linux targets. Split the build runs per platform.
- **Version in package.json not matching the -Version parameter:** electron-builder reads `version` from package.json for `${version}` in `artifactName`. The build scripts must patch `package.json` version before invoking electron-builder, or pass it via `--extraMetadata version=$VERSION`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NSIS installer creation | Custom NSIS script | `electron-builder` win.target nsis | electron-builder generates NSIS installer scripts, handles UAC, uninstaller, shortcuts, registry; manual NSIS is weeks of work |
| AppImage / deb packaging | Manual fakeroot/dpkg scripts | `electron-builder` linux.target | Handles desktop file, AppDir structure, fakeroot, compression, architecture metadata |
| File globbing and staging for packaging | Custom copy scripts | `electron-builder files[]` and `extraResources[]` | electron-builder handles all staging, ASAR creation, native module unpacking automatically |
| TypeScript compilation | webpack or babel | `tsc` with tsconfig.electron.json | tsc is already in the frontend devDependencies (typescript 5.7.3); no new tool needed |
| Cross-platform path resolution in main.ts | Manual env var | Already done in `backendEntrypoint()` with multi-candidate lookup | Phase 13 already solved this; `process.resourcesPath` is the canonical production path |

**Key insight:** electron-builder's abstraction over NSIS/AppImage/deb handles 10+ edge cases per format (architecture detection, symlinks, permissions, desktop environment integration). Custom scripts for any of these would require months of maintenance.

---

## Runtime State Inventory

> SKIPPED — This is a greenfield packaging phase, not a rename/refactor phase. No runtime state needs migration.

---

## Common Pitfalls

### Pitfall 1: Version mismatch between script parameter and package.json

**What goes wrong:** `artifactName` uses `${version}` from package.json. If the script passes `--version 1.2.0` to package_backend but does not update root `package.json`'s `version` field, the installer filename will use whatever version was previously in package.json.

**Why it happens:** electron-builder resolves `${version}` from package.json metadata at build time; the script `-Version` parameter only controls the backend bundle directory name.

**How to avoid:** Build scripts must update `package.json` version field before running electron-builder. Use `npm version --no-git-tag-version 1.2.0` in the build script, or use `--extraMetadata '{"version":"$VERSION"}'` on the electron-builder CLI. The `--extraMetadata` approach is safer as it doesn't modify the source file.

**Warning signs:** Installer filename does not match the expected pattern `CTRX-Setup-1.2.0.exe`.

### Pitfall 2: preload.cjs path breaks after packaging

**What goes wrong:** `main.ts` references `path.join(__dirname, 'preload.cjs')`. After tsc compiles to `dist/electron/main.js`, `__dirname` points to `dist/electron/`. If `preload.cjs` is not included in the `files` array, it won't exist in the packaged app and Electron will throw a preload load error (silent in some cases — renderer runs without context bridge).

**Why it happens:** `dist/electron/**` copies compiled `.js` files but not the `.cjs` source file from `electron/preload.cjs`. electron-builder only includes what the `files` patterns match.

**How to avoid:** Explicitly include `"electron/preload.cjs"` in the `files` array AND add a FileSet to place it at `dist/electron/preload.cjs`:
```json
{
  "from": "electron/preload.cjs",
  "to": "dist/electron/preload.cjs"
}
```
Or alternatively, copy `preload.cjs` to `dist/electron/preload.cjs` in Step 3 of the build script before electron-builder runs.

**Warning signs:** Renderer process has no `window.api` object; IPC calls fail silently.

### Pitfall 3: Windows Defender SmartScreen on unsigned NSIS installer

**What goes wrong:** Windows Defender SmartScreen shows "Windows protected your PC" dialog when users run the installer. This is the SmartScreen reputation check (not an AV detection) — any new/unsigned `.exe` triggers it.

**Why it happens:** SmartScreen assigns reputation based on signing certificate and download count. An unsigned installer from an unknown publisher has zero reputation.

**How to avoid per project decisions:** Code signing is out-of-scope for v1.2 (internal distribution). The `--onedir` PyInstaller mode (already locked) prevents the AV false-positive triggered by self-extracting `.exe` files. For internal distribution, users can click "More info → Run anyway". Document this in README. NSIS `perMachine: false` (per-user install) avoids UAC elevation which also reduces Defender scrutiny slightly.

**Warning signs:** Users report a blue SmartScreen prompt on first install. This is expected behavior for unsigned apps in internal distribution — not a build error.

### Pitfall 4: Linux build runs on wrong glibc version

**What goes wrong:** AppImage or .deb built on Ubuntu 24.04 (glibc 2.39) requires glibc >= 2.39 on the target machine, causing `GLIBC_2.38 not found` crash on Ubuntu 22.04 target.

**Why it happens:** electron-builder links to the system glibc on the build host. The binary's minimum glibc requirement equals the build host's glibc version.

**How to avoid:** Build exclusively on Ubuntu 22.04 (glibc 2.35). This is already captured in STATE.md as a constraint. The build.sh script should include a comment or `uname -r` / `ldd --version` check.

**Warning signs:** AppImage launches then immediately crashes with a glibc error on target Ubuntu 22.04 machine.

### Pitfall 5: Electron ESM + electron-store CJS conflict

**What goes wrong:** With `"type": "module"` in root package.json, `require('electron-store')` in preload.cjs or any CJS file may fail because the resolution changes.

**Why it happens:** electron-store v10 supports both CJS and ESM. The ESM entry is used when the package is imported via `import` in a module context. But `preload.cjs` uses `require()` in CJS mode (`.cjs` extension overrides `"type":"module"`). The existing `store.ts` uses `import Store from 'electron-store'` which is ESM — this is fine in the main process. The `preload.cjs` does NOT import electron-store, so there is no conflict.

**How to avoid:** Keep `preload.cjs` as CJS (`.cjs` extension). Do not attempt to use `electron-store` in the preload. The existing code already follows this pattern correctly.

**Warning signs:** `require is not defined` or `Cannot use import statement in a module` errors at Electron startup.

### Pitfall 6: tsc includes electron/tests in compilation

**What goes wrong:** `tsconfig.electron.json` with `include: ["electron/**/*.ts"]` also picks up `electron/tests/*.test.mjs`. Test utilities may import non-existent modules, causing tsc errors during build.

**Why it happens:** Glob `**/*.ts` is broad. The tests directory contains `.mjs` files (not `.ts`), so it may not be an issue, but it's worth being explicit.

**How to avoid:** Add `"exclude": ["electron/tests/**"]` to `tsconfig.electron.json`.

---

## Code Examples

Verified patterns from official sources and project analysis:

### Complete root package.json build field

```json
// Source: [CITED: electron.build/docs/configuration/] + project code analysis
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
        "to": ".",
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

### tsconfig.electron.json

```json
// Source: [CITED: electronjs.org/docs/latest/tutorial/esm] + [CITED: typescriptlang.org/tsconfig/]
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

### Version injection in build.ps1 before electron-builder

```powershell
# Source: [ASSUMED] — electron-builder --extraMetadata flag
# Pass version to electron-builder without modifying package.json source
npx electron-builder --win --extraMetadata "{\"version\":\"$Version\"}"
```

### Version injection in build.sh before electron-builder

```bash
# Source: [ASSUMED] — electron-builder --extraMetadata flag
npx electron-builder --linux --extraMetadata "{\"version\":\"$VERSION\"}"
```

### Verify extraResources path at runtime (existing main.ts pattern)

```typescript
// Source: electron/main.ts (existing code — this already works correctly)
// The manifest is checked at process.resourcesPath (after packaging) or
// electron/resources (in development). The three-candidate lookup handles both.
const resourcesCandidates = [
  path.join(__dirname, 'resources'),                         // dev: dist/electron/resources
  path.join(app.getAppPath(), 'electron', 'resources'),      // dev: project source
  path.join(process.resourcesPath, 'electron', 'resources'), // WRONG for prod with to:"."
]
// With extraResources to:".", manifest lands at process.resourcesPath/.backend-manifest.json
// The current code checks __dirname/resources first — in production __dirname = dist/electron/
// inside asar, so it won't find it there. Need to add process.resourcesPath as a candidate.
```

**Important:** The `backendEntrypoint()` function in `main.ts` currently tries `process.resourcesPath/electron/resources` as candidate 3. With `extraResources to: "."`, the actual path is `process.resourcesPath` directly. The plan must add `process.resourcesPath` as a candidate, or change `to: "electron/resources"` to match the existing code's expectation.

**Recommended resolution:** Use `"to": "electron/resources"` in the extraResources config so the existing `main.ts` candidate 3 (`process.resourcesPath/electron/resources`) matches. This requires zero changes to `main.ts`.

```json
// Revised extraResources to match existing main.ts path resolution:
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
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `electron-builder.yml` separate config | `package.json "build"` field inline | Supported since early versions; now both work | D-01 locked the inline approach |
| CommonJS Electron main process | ESM with `"type":"module"` | Electron 28+ (2023) | Requires `module: NodeNext` tsconfig; preload stays `.cjs` |
| `--onefile` PyInstaller | `--onedir` | v1.2 start decision | Eliminates self-extraction AV heuristic trigger |
| Code signing for distribution | Unsigned (internal only) | v1.2 decision | SmartScreen warning expected but acceptable |
| `directories.renderer` (never existed) | `files[]` FileSet for renderer | N/A | The renderer directory is included via `files`, not `directories` |

**Deprecated/outdated:**

- `electron-builder.Interface.NsisOptions.installerFilename`: Not a valid field — use `artifactName` on the `nsis` block. [ASSUMED — could not reach the NsisOptions API docs page]
- `sourceDir` / `app` in directories: `directories.app` is only used when your package.json is in a subdirectory (two-package structure). Not applicable here — root package.json is the app.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `electron-builder --extraMetadata '{"version":"1.2.0"}'` is the correct CLI syntax for version override | Code Examples | Build scripts would need to use `npm version --no-git-tag-version` instead; minor change |
| A2 | `nsis.installerFilename` is not valid; `nsis.artifactName` is the correct field | Standard Stack / Code Examples | If `installerFilename` exists as alias, both work and there's no issue |
| A3 | `directories.renderer` is not a valid electron-builder field; `files[]` FileSet is the correct mechanism for including `frontend/dist` | Architecture Patterns / Critical finding | If `directories.renderer` is silently accepted but ignored, the frontend dist would not be packaged — same outcome, same fix |
| A4 | `extraResources to: "electron/resources"` correctly maps to `process.resourcesPath + "/electron/resources"` at runtime | Code Examples | If to-path doesn't create the subdirectory, manifest lookup fails; fallback in main.ts catches this |
| A5 | Linux AppImage and deb build requires `fakeroot` and `rpmbuild` system tools on Ubuntu 22.04 | Environment Availability | Without system tools, electron-builder will error; must be installed before Step 4 |

---

## Open Questions

1. **`directories.renderer` vs `files[]` FileSet**
   - What we know: `MetadataDirectories` has only `app`, `buildResources`, `output` per multiple official sources
   - What's unclear: Whether electron-builder silently ignores unknown fields (may not error) or treats `renderer` as a custom target directory
   - Recommendation: Use `files[]` FileSet approach, which is the documented mechanism for including non-standard source directories

2. **Icon files for NSIS and Linux**
   - What we know: `win.icon` expects an `.ico` file; Linux desktop entries expect a `.png`; electron-builder looks for icons in `buildResources/` (defaults to `build/`)
   - What's unclear: Whether placeholder icons are needed now or if electron-builder can proceed without them
   - Recommendation: Create `build/icon.ico` (Windows, 256x256) and `build/icon.png` (Linux, 512x512) in Wave 0; electron-builder will error without them if the `win.icon` field references them

3. **Version patching strategy**
   - What we know: `${version}` in artifactName reads from package.json
   - What's unclear: Whether `--extraMetadata` is the correct CLI flag in electron-builder 26+
   - Recommendation: Verify with `npx electron-builder --help | grep extraMetadata` before finalizing scripts; fallback is `npm version --no-git-tag-version $VERSION` before Step 4

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Step 2 (npm run build), Step 3 (npx tsc), Step 4 (npx electron-builder) | ✓ | v24.15.0 | — |
| npm | Steps 2-4 | ✓ | bundled with Node 24 | — |
| TypeScript (tsc) | Step 3 | ✓ (via frontend/node_modules) | 5.7.3 | Must install as devDependency in root |
| Python + pyinstaller | Step 1 (via package_backend.ps1) | ✓ on Windows dev machine (Phase 12 confirmed) | Python 3.11 | Linux: must install on Ubuntu 22.04 |
| fakeroot | Linux deb build (electron-builder) | ✗ (not checked — Windows machine) | — | Must install on Ubuntu 22.04: `apt install fakeroot` |
| electron-builder | Step 4 | ✗ (not yet in root package.json) | — | Install as devDependency |
| electron | Step 4 | ✗ (not yet in root package.json) | — | Install as devDependency |

**Missing dependencies with no fallback:**

- `electron-builder` — must be added to root package.json devDependencies (this is the deliverable of Wave 0)
- `electron` — must be added to root package.json devDependencies
- `typescript` (in root) — frontend has it but root tsconfig.electron.json needs it accessible from root; add to root devDependencies

**Missing dependencies with fallback:**

- `fakeroot` on Linux — required for deb build; install with `sudo apt install fakeroot` on Ubuntu 22.04 before running Step 4 on Linux
- Icon files (`build/icon.ico`, `build/icon.png`) — electron-builder will use defaults or error; create placeholder icons in Wave 0

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Node.js built-in test runner (`node --test`) |
| Config file | none — invoked directly via `node --test` |
| Quick run command | `node --test electron/tests/**/*.test.mjs` (from frontend/ per package.json) |
| Full suite command | `node --test frontend/tests/**/*.test.mjs frontend/tests/router/**/*.test.mjs electron/tests/**/*.test.mjs` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUILD-01 | electron-builder config produces correct artifact names | smoke/manual | Run build, check dist/ for `CTRX-Setup-1.2.0.exe` / `.AppImage` / `.deb` | ❌ Wave 0 (manual acceptance) |
| BUILD-01 | extraResources places backend binary outside ASAR | smoke/manual | Unzip installer, verify `resources/electron/resources/ctrx-backend-*` exists | ❌ Wave 0 (manual acceptance) |
| BUILD-02 | build.ps1 fails fast when -Version missing | unit | `pwsh -Command "& scripts/build.ps1" 2>&1 | Select-String "Mandatory"` | ❌ Wave 0 |
| BUILD-02 | build.sh fails fast when --version missing | unit | `bash scripts/build.sh 2>&1; echo "exit:$?"` | ❌ Wave 0 |
| BUILD-03 | .deb installs via dpkg | manual | `dpkg -i CTRX-1.2.0-x64.deb` on Ubuntu 22.04 | ❌ Linux manual |

### Sampling Rate

- **Per task commit:** `node --test electron/tests/**/*.test.mjs` (existing IPC/lifecycle tests — verify packaging didn't break imports)
- **Per wave merge:** Full test suite including frontend router tests
- **Phase gate:** Full build + installer smoke test before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `build/icon.ico` — placeholder icon required for NSIS build (256x256 ICO)
- [ ] `build/icon.png` — placeholder icon required for Linux desktop entry (512x512 PNG)
- [ ] Root `package.json` — needs `name`, `version`, `main`, `type`, `build`, `devDependencies` fields (currently only has `dependencies: {electron-store}`)
- [ ] `tsconfig.electron.json` — new file in project root
- [ ] `npm install` in root — installs electron, electron-builder, typescript, @types/node

*(Existing electron/tests/**/*.test.mjs cover the main process behavior from Phase 13 — no new test files needed for Phase 14, which is primarily a build configuration phase)*

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes (limited) | Build scripts validate version param format |
| V6 Cryptography | no | — |

### Known Threat Patterns for Build Pipelines

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unsigned NSIS installer triggers SmartScreen | Repudiation | Acceptable for v1.2 internal distribution; document "More info → Run anyway" |
| PyInstaller --onefile AV false positive | — | Already mitigated by --onedir decision from v1.2 start |
| extraResources binary not code-signed | Tampering | Internal distribution only; out-of-scope per REQUIREMENTS.md |
| Build script injection via Version parameter | Tampering | Validate version format with regex before passing to subcommands |

---

## Sources

### Primary (HIGH confidence)

- [electron.build/docs/configuration/](https://www.electron.build/docs/configuration/) — top-level build config fields, directories, extraResources, files
- [electronjs.org/docs/latest/tutorial/esm](https://www.electronjs.org/docs/latest/tutorial/esm) — ESM in Electron, preload script constraints, `"type":"module"` requirements
- `electron/main.ts` (codebase) — existing production path resolution in `backendEntrypoint()` and `loadRenderer()`
- `scripts/package_backend.ps1` / `package_backend.sh` (codebase) — verified Step 1 interface: `-Platform`, `-Version` params
- npm registry: `npm view electron version` → 42.3.0, `npm view electron-builder version` → 26.8.1

### Secondary (MEDIUM confidence)

- [electron.build/nsis.html](https://www.electron.build/nsis.html) — NSIS target options (WebFetch returned empty body; info from search snippets)
- [pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/](https://www.pythonguis.com/faq/problems-with-antivirus-software-and-pyinstaller/) — AV false positive mitigation techniques
- [github.com/electron-userland/electron-builder issues](https://github.com/electron-userland/electron-builder/issues/6347) — NSIS Windows Defender false positive pattern

### Tertiary (LOW confidence)

- WebSearch results about `directories.renderer` non-existence — confirmed by multiple sources failing to find it in MetadataDirectories
- `--extraMetadata` CLI flag syntax for version override [ASSUMED based on electron-builder docs pattern]

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — package versions verified via npm view; slopcheck [OK] for all 4 packages
- Architecture: HIGH — based on direct inspection of main.ts, package_backend.ps1, and electron/resources structure
- electron-builder config: MEDIUM — primary docs pages returned empty bodies; config derived from search snippets + cross-reference with project code
- `directories.renderer` non-existence: HIGH — MetadataDirectories consistently documented with 3 fields only; no source confirms `renderer` field
- Pitfalls: MEDIUM — based on GitHub issue search and project-specific code analysis

**Research date:** 2026-05-29
**Valid until:** 2026-07-01 (electron-builder and electron release frequently; re-verify package versions before execution)
