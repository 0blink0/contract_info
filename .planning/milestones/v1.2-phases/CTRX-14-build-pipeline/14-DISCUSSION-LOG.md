# Phase 14: 构建流水线 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 14-构建流水线
**Areas discussed:** electron-builder 配置位置, 构建脚本入口模型, Linux 构建环境

---

## electron-builder 配置位置

| Option | Description | Selected |
|--------|-------------|----------|
| 内联到根 package.json build 字段 | Electron 社区惯例，单文件管理。根 package.json 既然要大幅扩展，一并内联配置更简洁。 | ✓ |
| 独立 electron-builder.yml | 跨平台目标多（NSIS + AppImage + deb）时配置更清晰，与 package.json 分离。需要额外维护一个文件。 | |

**User's choice:** 内联到根 package.json build 字段
**Notes:** —

---

### TypeScript 编译输出目录

| Option | Description | Selected |
|--------|-------------|----------|
| dist/electron/ | 根目录下 dist/electron/main.js，与前端 Vite 输出（frontend/dist/）分开。package.json main 字段指向此处。 | ✓ |
| out/ 或 app/ | 部分 Electron 模板用 out/ 或 app/ 存放主进程构建产物，与 Vite 整入同一层级。 | |

**User's choice:** dist/electron/
**Notes:** —

---

### electron-builder renderer 目录

| Option | Description | Selected |
|--------|-------------|----------|
| frontend/dist | Vite 默认在 frontend/ 项目里输出到 dist/，不改变现有 vite.config，electron-builder directories.renderer 设为 frontend/dist。 | ✓ |
| 移动到根 dist/renderer | 改变 Vite outDir，所有构建产物统一到根 dist/。更整洁但需要修改 vite.config。 | |

**User's choice:** frontend/dist（保持现状）
**Notes:** —

---

## 构建脚本入口模型

### Step 1 PyInstaller 处理方式

| Option | Description | Selected |
|--------|-------------|----------|
| 调用现有 scripts/package_backend.ps1 | 构建脚本为薄层调度器，Step 1 调用 package_backend.ps1 -Platform -Version。DRY，逻辑不重复，但依赖两个文件。 | ✓ |
| 内联所有 4 步 | 一个完全自包含脚本，新开发者读一个文件全明白。但 PyInstaller 逻辑与 package_backend.ps1 重复。 | |

**User's choice:** 调用现有 scripts/package_backend.ps1
**Notes:** —

---

### 版本号传入方式

| Option | Description | Selected |
|--------|-------------|----------|
| 脚本参数传入 | build.ps1 -Version 1.2.0 显式传入。可审计，适合手动分发场景。 | ✓ |
| 从根 package.json version 字段读取 | 脚本自动读取 package.json version，无需手动传参，但需要解析 JSON。 | |

**User's choice:** 脚本参数传入
**Notes:** —

---

### 构建脚本存放位置

| Option | Description | Selected |
|--------|-------------|----------|
| 继续放在 scripts/ 目录 | 与现有 package_backend.ps1 保持一致，全部构建工具集中在 scripts/。 | ✓ |
| 放在根目录 | 构建脚本直接在根目录，跑 .\build.ps1 -Version 1.2.0 即可。 | |

**User's choice:** scripts/ 目录
**Notes:** —

---

## Linux 构建环境

**User's choice:** 暂不讨论（"linux暂时不考虑了吧"）
**Notes:** 交由 Claude 酌情决定。推荐 native ubuntu:22.04，遵循 STATE.md glibc 2.35 兼容性约束。

---

## Claude's Discretion

- 根 `package.json` 的 `appId`、`productName`、`author`、`version` 等标识符具体值
- `extraResources` glob 模式与 `asarUnpack` 的具体配置
- Linux `.sh` 脚本的 shebang 与容器化提示注释写法
- electron-builder NSIS/Linux target 的细粒度参数（图标、安装目录、菜单项等）
- Linux 构建环境的具体安排（推荐 native ubuntu:22.04）

## Deferred Ideas

- 自动更新（auto-update）— out-of-scope，v1.2 明确排除
- Windows 代码签名 — 内部分发暂不需要
- Linux 构建 CI 自动化 — v1.3 评估
- Linux clean VM 验收补跑（Phase 12 deferred）— Phase 14 验收时补齐
