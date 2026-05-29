# CTRX Retrospective

Living retrospective — updated at each milestone close.

---

## Milestone: v1.2 — 桌面化交付

**Shipped:** 2026-05-29
**Phases:** 4 (11–14) | **Plans:** 11 | **Duration:** 2 days

### What Was Built

- Phase 11: SQLite 完整迁移（PostgreSQL 方言类型替换、WAL 模式、CTRX_DATA_DIR 路径隔离、programmatic Alembic）
- Phase 12: PyInstaller 单 spec 打包（hiddenimports 审计基线 + CI 门禁 + Windows 主链路烟测）
- Phase 13: Electron 生命周期状态机 + contextBridge 3 通道 IPC + 首启向导（强门禁）+ Settings 重启事务
- Phase 14: electron-builder 26.x 构建流水线（NSIS + AppImage + deb），产出 CTRX-Setup-1.2.0.exe (133MB)

### What Worked

- **TDD Wave-0 gate（Phase 11）:** 先写 RED 测试再实现，10 个测试用例覆盖 DB-01..DB-04，有效防止假阳性实现。发现了 alembic/env.py module-level `get_settings()` 需要 monkeypatch 的隐藏坑。
- **Wave-based execution:** 波次阻塞关系（Wave 0→1→2）在 Phase 11 和 Phase 14 均有效，确保依赖顺序正确。
- **Auto-fix during plan execution:** Phase 14-03 自动发现并修复了 3 个阻断性 bug（TS5097、extraMetadata 语法、winCodeSign），不扩展范围直接修复。
- **hiddenimports CI gate（Phase 12）:** check_hiddenimports_diff.py 将 hiddenimports 审计制度化，防止后续 CI 中出现 ModuleNotFoundError 回归。
- **Electron restart transaction + rollback（Phase 13）:** save-settings 实现了完整的重启事务（失败时恢复旧配置），对内部工具而言是超预期的健壮性。

### What Was Inefficient

- **REQUIREMENTS.md 未同步更新:** Phase 11–13 完成时 DB-*/PKG-*/ELEC-* 需求未打勾，导致 milestone close 时需要手动批量更新 11 条记录。应在每个 Phase 完成时立即更新 traceability table。
- **Linux 验证环境缺失:** PKG-03 Linux clean-VM 验证无法在当前 Windows 主机完成，成为悬挂的 deferred item。下一个涉及 Linux 的里程碑需要提前准备 WSL2 或 CI Linux runner。
- **ESLint flat config 缺失:** Phase 13 lint 步骤发现 ESLint v10 要求 eslint.config.* 但仓库无此文件，lint 失败。应在 Phase 13 规划时纳入 ESLint 配置迁移。
- **无 v1.2 milestone audit:** 跳过了 `/gsd:audit-milestone`，依赖 SUMMARY 文件证据替代。对于跨 4 个阶段的里程碑，结构化的 audit 能提前发现集成问题。

### Patterns Established

- **electron-builder 26.x 三件套修复:** allowImportingTsExtensions+rewriteRelativeImportExtensions（TS6 NodeNext emit）、-c.extraMetadata.version=X（版本注入）、signAndEditExecutable=false（禁用 winCodeSign）— 这三个修复作为 TypeScript 6 + electron-builder 26.x 组合的标准配置已固化到项目。
- **preload.cjs FileSet 模式:** preload 以 `.cjs` 预编译，不经 tsc，通过 electron-builder FileSet 单独 stage，避免 ESM/CJS 混用问题。
- **desktop_main.py fail-fast 资产断言:** 启动时检查 alembic/dicts/templates 目录是否存在，缺失立即抛错，而非运行到中途才报 ModuleNotFoundError。
- **Wave-0 TDD RED gate:** 先写全红测试基础，再并行实现，最后 Wave 2 聚合验证 — 适用于需要完整功能切换（如数据库迁移）的场景。

### Key Lessons

1. **要求 traceability 同步更新为 phase 执行规则，不在 milestone close 补填。** 11 条遗漏记录是可避免的摩擦。
2. **提前声明 Linux 验证环境依赖。** PKG-03 deferred 的根本原因是环境缺失，不是功能缺失 — 计划阶段应识别并提前解决。
3. **electron-builder 版本锁定很重要。** 26.x 的多个 API 破坏性变更（extraMetadata 语法、winCodeSign 行为）导致了 3 次阻断。在新项目中明确指定 `^26.x` 并测试每一个 CI 步骤。
4. **TypeScript 6 + NodeNext 模式有强制性约束。** allowImportingTsExtensions 单独不能 emit；必须配合 rewriteRelativeImportExtensions。新 electron 项目的 tsconfig 模板应包含这两个标志。
5. **内部工具的"足够好"边界清晰。** code signing、auto-update、keychain 全部正确排除在外 — 避免了 2-3 周额外工作。

### Cost Observations

- Sessions: ~6-8 sessions across 2 days
- Wave structure 减少了阻塞等待（Phase 11 Wave 1 两个 plan 并行）
- Phase 14 auto-fix 3 bugs in single session — efficient; no scope creep

---

## Cross-Milestone Trends

| Metric | v1.0 | v1.1 | v1.2 |
|--------|------|------|------|
| Duration | ~3 days | ~1 day | 2 days |
| Phases | 5 | 5 | 4 |
| Plans | 10 | 15 | 11 |
| Files changed | — | — | 57 |
| Insertions | — | — | 10,908 |
| Milestone audit | ✗ | ✅ | ✗ (skipped) |
| Requirements sync | partial | complete | partial |

**Trend:** 每个里程碑交付质量提升（更结构化的测试、更完整的 IPC 合约、更健壮的构建）。需要强化：需求 traceability 同步、Linux 环境提前准备、milestone audit 制度化。
