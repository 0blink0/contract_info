---
phase: 14
slug: CTRX-14-build-pipeline
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-29
updated: 2026-05-29
---

# Phase 14 验证策略

**阶段：** 构建流水线  
**日期：** 2026-05-29

## 需求到验证映射

| 需求 | 关键行为 | 自动化命令 | 类型 | 对应计划任务 |
|------|----------|------------|------|--------------|
| BUILD-01 | electron-builder 配置产出 CTRX-Setup-1.2.0.exe（NSIS）和 CTRX-1.2.0.AppImage | `ls dist/ \| grep -E 'CTRX-Setup-1.2.0.exe\|CTRX-1.2.0.AppImage'` | smoke/manual | 14-01 |
| BUILD-01 | extraResources 将后端二进制置于 ASAR 外（resources/electron/resources/ctrx-backend-*） | 解压安装包确认 `resources/electron/resources/ctrx-backend-*` 存在 | smoke/manual | 14-01 |
| BUILD-02 | build.ps1 在 -Version 缺失时 fail-fast（PowerShell Mandatory 强制失败） | `pwsh -NonInteractive -Command "& scripts/build.ps1" 2>&1 \| Select-String 'Mandatory\|Version'` | unit | 14-02 |
| BUILD-02 | build.sh 在 --version 缺失时 fail-fast（exit 2 + 使用说明） | `bash scripts/build.sh 2>&1; [ $? -eq 2 ] && echo PASS` | unit | 14-02 |
| BUILD-02 | 4 步流程串行且任一失败即终止 | build.ps1/build.sh 对各步骤的 $ErrorActionPreference/set -e 机制 | code review | 14-02 |
| BUILD-03 | 产出 CTRX-1.2.0.deb，可通过 dpkg -i 安装并从系统菜单启动 | `dpkg -i CTRX-1.2.0-x64.deb`（Ubuntu 22.04 手工验收） | manual/Linux | 14-01 |

## Wave 0 缺口

- [ ] `build/icon.ico` — NSIS 构建必需（256×256 ICO 占位图标）
- [ ] `build/icon.png` — Linux desktop entry 必需（512×512 PNG 占位图标）
- [ ] `tsconfig.electron.json` — 新文件，tsc 编译 electron/*.ts → dist/electron/
- [ ] 根 `package.json` 字段补齐：`name`、`version`、`main`、`type`、`build`、`devDependencies`
- [ ] `npm install` 在根目录安装：electron、electron-builder、typescript、@types/node

## 采样与门禁

- **每任务完成后：** `node --test electron/tests/**/*.test.mjs`（现有 IPC/生命周期测试，确认打包配置未破坏导入）
- **每 wave 收口：** `node --test frontend/tests/**/*.test.mjs electron/tests/**/*.test.mjs`
- **阶段门禁（Windows）：**
  1. `pwsh -Command "& scripts/build.ps1 -Version 1.2.0"` 成功完成
  2. `ls dist/ | grep CTRX-Setup-1.2.0.exe` 存在
  3. 解压安装包确认 `resources/electron/resources/.backend-manifest.json` 存在
- **阶段门禁（Linux，Ubuntu 22.04）：**
  1. `bash scripts/build.sh --version 1.2.0` 成功完成
  2. `ls dist/ | grep -E 'CTRX-1.2.0.*AppImage|CTRX-1.2.0.*deb'` 存在
  3. `dpkg -i dist/CTRX-1.2.0-x64.deb && ctrx` 可从系统菜单启动

## 人工验收补充

1. Windows 干净 VM 安装 `CTRX-Setup-1.2.0.exe`，确认 Windows Defender 不隔离（--onedir 模式），应用正常启动。
2. Ubuntu 22.04 运行 `CTRX-1.2.0.AppImage`，确认应用完整可用（加载隔屏 → 向导 → 主界面）。
3. Ubuntu 22.04 运行 `dpkg -i CTRX-1.2.0-x64.deb`，确认可从系统菜单启动。
4. 执行 `scripts/build.ps1`（不传 -Version），确认 fail-fast 并打印明确错误。
