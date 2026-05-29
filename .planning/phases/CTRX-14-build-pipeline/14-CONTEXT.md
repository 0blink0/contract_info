# Phase 14: 构建流水线 - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

交付可分发安装包的构建流水线：electron-builder 产出 Windows NSIS 安装包（`.exe`）、Linux AppImage 和 `.deb`；配套 `.ps1` / `.sh` 构建脚本执行 4 步流程（PyInstaller → Vite → tsc → electron-builder）。

本阶段不扩展新业务功能（如 auto-update、代码签名、系统托盘）。

</domain>

<decisions>
## Implementation Decisions

### electron-builder 配置

- **D-01:** electron-builder 构建配置**内联到根 `package.json` 的 `build` 字段**，不拆独立 `electron-builder.yml`。根 package.json 需同步补齐 `name`、`version`、`main`、`devDependencies` 等字段。
- **D-02:** TypeScript 编译（tsc）产物输出到 **`dist/electron/`**；根 `package.json` 的 `main` 字段指向 `dist/electron/main.js`。
- **D-03:** Vite 前端输出保持在 **`frontend/dist/`**（不改变现有 vite.config），electron-builder 的 `directories.renderer` 设为 `frontend/dist`。

### 构建脚本入口模型

- **D-04:** 新建 `scripts/build.ps1`（Windows）和 `scripts/build.sh`（Linux）作为 4-step 薄层调度器：Step 1 直接调用 **`scripts/package_backend.ps1`**（或 `package_backend.sh`）完成 PyInstaller 打包与 manifest 更新，不重复内联 PyInstaller 逻辑。
- **D-05:** 版本号通过**脚本参数**传入：`scripts/build.ps1 -Version 1.2.0`。两个脚本均需校验版本参数存在，否则 fail-fast。
- **D-06:** 构建脚本**保留在 `scripts/` 目录**，与现有 `package_backend.ps1` 保持集中。

### Linux 构建环境

- **D-07:** Linux 构建环境**交由 Claude 酌情决定**（推荐 native ubuntu:22.04，遵循 STATE.md glibc 2.35 兼容性约束）。

### Claude's Discretion

- 根 `package.json` 的 `appId`、`productName`、`author`、`version` 等标识符具体值。
- `extraResources` glob 模式（覆盖 `electron/resources/ctrx-backend-*`）与 `asarUnpack` 的具体配置。
- Linux `.sh` 脚本的 shebang 与容器化提示注释写法。
- electron-builder NSIS/Linux target 的细粒度参数（图标、安装目录、菜单项等）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 路线与需求

- `contract_info/.planning/ROADMAP.md` — Phase 14 目标、成功标准（安装包文件名、VM 验收要求）。
- `contract_info/.planning/REQUIREMENTS.md` — BUILD-01/02/03 硬性约束（NSIS + AppImage + deb、4-step 脚本、extraResources/asarUnpack 要求）。
- `contract_info/.planning/PROJECT.md` — v1.2 桌面化总目标与 out-of-scope 边界（自动更新、代码签名、系统托盘均不在范围内）。
- `contract_info/.planning/STATE.md` — glibc 兼容性约束（ubuntu:22.04 for glibc 2.35）。

### 上游阶段（直接依赖）

- `contract_info/.planning/phases/CTRX-13-electron-ipc/13-CONTEXT.md` — Electron 主进程结构、IPC 架构、electron-store 使用方式。
- `contract_info/.planning/phases/CTRX-12-pyinstaller/12-CONTEXT.md` — `--onedir` 约定、`electron/resources/` 目录布局、manifest 格式。
- `contract_info/.planning/phases/CTRX-12-pyinstaller/12-01-SUMMARY.md` — PyInstaller spec/hiddenimports 实际落地情况。

### 代码锚点

- `contract_info/electron/main.ts` — Electron 主进程入口（tsc 编译目标）。
- `contract_info/electron/preload.cjs` — Preload 脚本（CJS，已存在）。
- `contract_info/electron/resources/.backend-manifest.json` — 后端资源清单（electron-builder extraResources 需包含此文件）。
- `contract_info/scripts/package_backend.ps1` — PyInstaller 封装脚本（Step 1 调用目标）。
- `contract_info/scripts/package_backend.sh` — PyInstaller Bash 版本（build.sh Step 1 调用目标）。
- `contract_info/ctrx_backend.spec` — PyInstaller spec 文件（package_backend 的直接入参）。
- `contract_info/frontend/package.json` — Vite 构建配置（`npm run build` 产出 `frontend/dist/`）。
- `contract_info/package.json` — 根 package.json（需扩展 electron-builder build 字段 + devDependencies）。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `scripts/package_backend.ps1` / `scripts/package_backend.sh`：已完整封装 PyInstaller 调用 + manifest 写入 + 版本目录管理，构建脚本 Step 1 直接调用即可。
- `electron/resources/ctrx-backend-win-x64-v1.2.0`：Phase 12 产物，已在正确目录，electron-builder `extraResources` 可直接引用 `electron/resources/ctrx-backend-*`。
- `electron/resources/.backend-manifest.json`：主进程定位后端二进制的索引，需包含在 extraResources 中。

### Established Patterns

- `--onedir` PyInstaller 约定已锁定（无论 Windows/Linux），避免 AV 误杀与打包复杂度。
- `electron/resources/` 作为后端产物落地点的约定已在 Phase 12 建立，Phase 14 沿用。
- fail-fast 风格（资源缺失即阻断、错误信息明确）贯穿 Phase 11-13，构建脚本继续沿用。

### Integration Points

- electron-builder `files` 字段需覆盖 `dist/electron/` 主进程产物和 `frontend/dist/` 渲染器产物。
- electron-builder `extraResources` 引用 `electron/resources/ctrx-backend-*`，确保安装后二进制在 `resources/` 下可访问。
- tsc 编译步骤须先于 electron-builder 执行，保证 `dist/electron/main.js` 存在。

</code_context>

<specifics>
## Specific Ideas

- 成功标准已在 ROADMAP.md 明确文件名：`CTRX-Setup-1.2.0.exe`、`CTRX-1.2.0.AppImage`、`CTRX-1.2.0.deb`，productName 应为 `CTRX`，version `1.2.0`。
- Linux 构建需在 ubuntu:22.04 环境运行（glibc 2.35），避免高版本 glibc 依赖导致目标机无法运行。
- 4-step 脚本需"无人值守可运行"（REQUIREMENTS.md BUILD-02 约束），每步失败即终止并报告。

</specifics>

<deferred>
## Deferred Ideas

- 自动更新（auto-update）：需代码签名基础设施，明确排除在 v1.2 范围之外。
- Windows 代码签名：内部分发暂不需要，out-of-scope。
- Linux 构建的 Docker 化或 CI 自动化：当前以手动 native ubuntu:22.04 为基准，CI 集成可在 v1.3 评估。
- Linux clean VM 验收补跑（Phase 12 deferred）：不阻塞 Phase 14 规划，可在 Phase 14 验收时一并补齐。

</deferred>

---

*Phase: 14-构建流水线*
*Context gathered: 2026-05-29*
