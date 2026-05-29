# 合同要素抽取与 Excel 导入生成（CTRX）

## What This Is

面向私募综合业务管理系统的**半自动录入工具**：运营上传基金合同（**docx**），系统解析、抽取字段，生成可导入 Excel（产品要素、运营费率、申赎费率、锁定期、分级份额），并输出**业绩报酬/开放日** JSON 供 CRM 手录；可选 **LLM 校验层** 核对摘录与填值是否一致。

现为 **Electron 桌面应用**，双击 CTRX-Setup-1.2.0.exe 即可安装使用，无需 Python 或 Docker 环境。

独立子项目，根目录 `contract_info/`。

## Core Value

**上传一份 docx → 得到接近人工填写质量的 Excel + 可手录的结构化草稿 + 可解释的校验报告。**

## Current State

- **Shipped:** v1.2（2026-05-29）— 桌面化交付完成
- **Runtime:** FastAPI + Vue + SQLite + Electron 桌面壳（Windows NSIS + Linux AppImage/deb）
- **Deliverable:** `scripts/build.ps1 -Version 1.2.0` → `dist/CTRX-Setup-1.2.0.exe` (133MB NSIS installer)
- **Planning:** v1.3 多文件并行与详情页重构（requirements + roadmap in progress）

## Current Milestone: v1.3 多文件并行与详情页重构

**Goal:** 一次最多上传 3 份 docx 并行解析；将文件详情拆为左侧可导航的六页工作流（五张导入表 + 字段 B），每页可编辑、可摘录核对、可下载；总览页仅作入口。

**Target features:**

- 多文件上传（≤3）与并行解析任务（每文件独立 job + 进度）
- 左侧「文件详情」可折叠子菜单（五表 + 字段 B）
- 六张独立详情页：可编辑导出数据 + 人工核对表（字段/值/页码/原文摘录）+ 单表下载
- 字段 B 页：业绩报酬与开放日建议摘录 + 页码，供人工判断
- 详情 Hub 总览：五表 + 字段 B 摘要与「进入详情」按钮

## Requirements

### Validated (v1.0)

- ✓ docx 解析、P1+ 扩展抽取、4 xlsx、API/UI、PostgreSQL、Docker — v1.0

### Validated (v1.1)

- ✓ 黄金回归基线与回归脚本 — v1.1
- ✓ 申赎费率第五张导入表 — v1.1
- ✓ 路径 B（业绩报酬/开放日）JSON 输出 — v1.1
- ✓ LLM 校验层 API + ValidationPanel UI — v1.1
- ✓ 五表下载 + 左侧菜单路由 — v1.1

### Validated (v1.2)

- ✓ SQLite 替换 PostgreSQL（方言类型全替换，WAL 模式，CTRX_DATA_DIR 路径隔离）— DB-01/02/03/04 — Phase 11
- ✓ PyInstaller Python 运行时打包（--onedir，hiddenimports 审计 CI 门禁，Windows 烟测）— PKG-01/02/03 — Phase 12
- ✓ Electron 主进程生命周期状态机（健康轮询，崩溃重试，SIGTERM→SIGKILL 退出）— ELEC-01 — Phase 13
- ✓ contextBridge 3 通道 IPC + electron-store 配置持久化 — ELEC-02 — Phase 13
- ✓ 首次启动 LLM 设置向导（向导强门禁）— ELEC-03 — Phase 13
- ✓ 应用内 Settings 页面（保存后重启事务 + 失败回滚）— ELEC-04 — Phase 13
- ✓ Windows/Linux 构建流水线（NSIS + AppImage + deb，build.ps1/sh，extraResources）— BUILD-01/02/03 — Phase 14

### Active (v1.3)

- [ ] 多文件上传与并行解析（≤3 份 docx）
- [ ] 文件详情 Hub + 左侧六页导航（五表 + 字段 B）
- [ ] 每表独立页：可编辑 preview + 摘录核对表 + 单表下载
- [ ] 字段 B 建议摘录页（业绩报酬/开放日原文 + 页码）

### Deferred (post-v1.3)

- [ ] **PATHB-EX-01**: 业绩报酬提取方式自动映射到 CRM 枚举值
- [ ] **PATHB-EX-02**: 业绩基准类型与门槛净值枚举精度提升
- [ ] Linux clean-VM 验证（PKG-03 defer）

### Out of Scope（当前）

- 黄金 xlsx 作为线上自动批改器
- CRM 自动录入、PDF、批量队列（见 v2）
- 批量多文件上传/ZIP/队列（v1.3 仅 ≤3 并行；更大批量 → v2）
- PATHB 枚举自动映射（PATHB-EX-01/02 → post-v1.3）
- 自动更新（auto-update）— 需代码签名基础设施
- 系统托盘图标 — 过度工程化，内部工具无需
- Keychain / OS 凭证存储 — config.json 已足够
- Windows 代码签名 — 内部分发暂不需要

## Context

- 开发黄金样例：`example/产品要素 - 副本(1).xlsx`、`example/产品运营费率导入模板.xlsx`、`example/产品申赎费率导入模板.xlsx`
- 字段规格：`FIELD_SPEC.md`
- 归档：`.planning/milestones/` (v1.0, v1.1, v1.2)
- 构建产物：`dist/CTRX-Setup-1.2.0.exe` (Windows), `scripts/build.sh` (Linux)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 黄金样例仅 dev/UAT | 避免把运营手工表当生产真值 | v1.1 采用 |
| 校验层只看摘录 | 可解释、可审计 | v1.1 采用 |
| 路径 B 仍 JSON 手录 | 无 CRM 母版 Excel | v1.1 采用 |
| 申赎费率独立第 5 表 | 业务新增导入模板 | v1.1 采用 |
| --onedir PyInstaller（非 --onefile） | 规避 AV 误报风险 | v1.2 采用 |
| electron-store pin v10 | CommonJS require() 兼容 | v1.2 采用 |
| SQLite 替换 PostgreSQL | 桌面应用无服务器，SQLite 足够 | v1.2 采用 |
| signAndEditExecutable: false | 跳过 winCodeSign 符号链接提取（代码签名超出 v1.2 范围） | v1.2 采用 ✓ |
| allowImportingTsExtensions + rewriteRelativeImportExtensions | TypeScript 6 NodeNext emit 模式双标志（TS5097 修复） | v1.2 采用 ✓ |
| -c.extraMetadata.version=X 语法 | electron-builder 26.x 版本注入（旧 --extraMetadata JSON 语法已弃用） | v1.2 采用 ✓ |

## Evolution

**Milestone v1.2（2026-05-29）：** 从 Docker-only 部署转型为 Electron 桌面应用。4 个阶段（11-14）历时 2 天，57 文件改动，10,908 行插入。Phase 14 完成构建流水线（electron-builder 26.x + TypeScript 6 + NodeNext），产出 CTRX-Setup-1.2.0.exe (133MB)；关键修复：TypeScript 6 allowImportingTsExtensions+rewriteRelativeImportExtensions、electron-builder -c.extraMetadata.version 语法、signAndEditExecutable=false。

**Milestone v1.1（2026-05-26）：** 从「能导出」转向「接近人工填写 + 可校验」，并完成五表、路径 B、校验闭环。

## Constraints

- 输入：docx；LLM 抽取与校验依赖 `.env` API Key（桌面端通过 Settings 页面配置）
- 样例合同与 xlsx 在 `example/`，不提交敏感生产数据
- Linux 构建需在 Ubuntu 22.04（glibc 2.35）环境执行

<details>
<summary>Archived Milestone Notes (v1.1 planning snapshot)</summary>

- 以 `example/` 双合同 + 黄金样例为主验证基线
- 完成 Phase 6–10 全链路（规则、导出、API、前端、文档）
- 子表导出修复与前端导航优化在同一里程碑收口

</details>

---

*Last updated: 2026-05-29 — v1.3 多文件并行与详情页重构 milestone started*
