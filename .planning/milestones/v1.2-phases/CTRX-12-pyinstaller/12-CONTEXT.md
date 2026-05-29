# Phase 12: PyInstaller 打包 - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

交付 Python/FastAPI 后端的 `--onedir` 打包与干净机可运行能力：围绕 `desktop_main.py`、PyInstaller spec、hiddenimports、资源布局与烟测验收，确保无 Python 环境机器可完成上传→抽取→下载主链路。

本阶段不扩展新业务能力（如新 UI、新抽取字段、自动更新、系统托盘等）。

</domain>

<decisions>
## Implementation Decisions

### 打包规格策略
- **D-01:** 使用**单一 spec + 平台参数化分支**，不拆 Windows/Linux 两套独立 spec。
- **D-02:** 打包默认**稳定优先**，禁用激进压缩/混淆；先保证可启动与可验收。
- **D-03:** `CTRX_DATA_DIR` / `CTRX_PORT` 的入口保持**desktop_main 单一入口**，不在 runtime hook 重复注入。
- **D-04:** 运行时缺失关键资源（如 `alembic/`、`dicts/`）时采用**fail-fast**，输出明确错误并阻断继续执行。

### hiddenimports 策略
- **D-05:** hiddenimports 采用**宽覆盖已知模块一次到位**作为默认起步策略，优先减少干净机首轮失败。
- **D-06:** 对 `openai/httpx/uvicorn` 等动态导入链采用**手工维护锁定清单**，要求可审计。
- **D-07:** hiddenimports 在 spec 内按**平台分段**维护（Windows/Linux 可差异化）。
- **D-08:** 对 hiddenimports 变更启用**CI 差异门禁**，变更需有说明。

### 资源布局与版本管理
- **D-09:** `electron/resources` 默认只保留**最终可分发 onedir 产物**，不保留中间构建目录。
- **D-10:** 资源目录命名采用**带版本号目录**（例如 `ctrx-backend-win-x64-v1.2.0`）。
- **D-11:** 运行日志与临时文件放在**userData/CTRX_DATA_DIR 外置目录**，不写入安装资源目录。
- **D-12:** 旧版本资源清理策略为**保留当前 + 上一个版本**，支持快速回退。

### 干净机验收（PKG-03）
- **D-13:** Phase 12 验收先覆盖**主链路最小烟测**：上传→抽取→下载。
- **D-14:** 烟测样本采用**固定 1 份黄金合同**，优先稳定可复现。
- **D-15:** 烟测失败默认**阻断发布**，不允许带风险放行。
- **D-16:** 验收沉淀采用**结构化 checklist + 命令 + 截图路径**。

### Claude's Discretion
- 具体 hiddenimports 清单条目与排序。
- spec 内平台分段的实现细节（条件表达式/辅助函数组织方式）。
- checklist 的字段模板与截图命名规范。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 路线与需求
- `contract_info/.planning/ROADMAP.md` — Phase 12 目标、依赖与成功标准。
- `contract_info/.planning/REQUIREMENTS.md` — PKG-01/PKG-02/PKG-03 明确约束与验收口径。
- `contract_info/.planning/PROJECT.md` — v1.2 桌面化总目标与 out-of-scope 边界。
- `contract_info/.planning/STATE.md` — 已锁定的里程碑约束（`--onedir`、SQLite 路径、后续阶段风险提示）。

### 上游阶段（直接依赖）
- `contract_info/.planning/phases/11-sqlite-migration/11-RESEARCH.md` — `desktop_main`、`CTRX_DATA_DIR`、`_MEIPASS`、Alembic 程序化迁移的技术结论与风险。
- `contract_info/.planning/phases/11-sqlite-migration/11-04-SUMMARY.md` — WAL + `desktop_main.py` 已落地行为边界。
- `contract_info/.planning/phases/11-sqlite-migration/11-03-SUMMARY.md` — `data_dir()` 与路径解析传播现状。

### 代码锚点
- `contract_info/desktop_main.py` — 当前桌面入口与迁移启动顺序（Phase 12 打包入口基线）。
- `contract_info/backend/app/config.py` — `data_dir()`/`_bundle_base()` 路径约定。
- `contract_info/alembic/env.py` — 程序化 Alembic connection 分支。
- `contract_info/backend/tests/test_desktop_main.py` — 启动迁移与幂等行为测试锚点。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `desktop_main.py`：已具备 `_get_bundle_base()`、`run_migrations()`、`main()` 启动链，可直接作为 PyInstaller entrypoint。
- `backend/app/config.py`：已固化 `data_dir()` 与 `_bundle_base()`，可支撑 bundled 与 dev 双路径。
- `backend/tests/test_desktop_main.py`：已验证迁移 fresh/idempotent，可作为 PKG-01 的回归锚点。

### Established Patterns
- 通过环境变量先注入再 `get_settings.cache_clear()` 的模式已建立，避免 stale config。
- `_MEIPASS` 仅用于只读资源，运行数据统一走 `CTRX_DATA_DIR` 的边界已建立。
- `alembic` 以程序化调用替代 CLI 子进程，适配 frozen 运行时。

### Integration Points
- PyInstaller spec 需要覆盖 `desktop_main.py` + `alembic/` + `dicts/` 并对 hiddenimports 做平台分段。
- 打包产物需输出到 `electron/resources/`，与后续 Electron 主进程资源定位对齐。
- Phase 12 验收产物需要可被 Phase 13/14 复用（启动稳定性与构建流水线）。

</code_context>

<specifics>
## Specific Ideas

- 不拆双 spec，减少后续维护漂移风险。
- CI 增加 hiddenimports 变更门禁，降低“本地可跑、干净机崩溃”的不可见风险。
- 验收先做最小闭环，确保 PKG-03 可以快速形成可复现通过证据。

</specifics>

<deferred>
## Deferred Ideas

- 并发回归、校验层联动、path-b 细项验收扩展：可在后续阶段（Phase 13/14 或专项质量阶段）追加，不作为 Phase 12 阻断范围。

</deferred>

---

*Phase: 12-PyInstaller 打包*
*Context gathered: 2026-05-28*
