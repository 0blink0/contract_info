# Phase 23: PyInstaller 打包兼容与烟测 - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段交付三件事：

1. **hiddenimports 扩充**：将 `lancedb`、`pyarrow`、`sentence-transformers` 相关包补入 `ctrx_backend.spec`，确保打包产物无 `ModuleNotFoundError`。
2. **离线模型打包**：将 bge-m3 模型权重目录纳入 `electron/resources/models/bge-m3/`（extraResources），并在 Electron 主进程 spawn/restart 后端时注入 `SENTENCE_TRANSFORMERS_HOME`/`TRANSFORMERS_CACHE`/`CTRX_MODELS_DIR` 指向该目录。
3. **烟测清单**：人工执行一份打包产物全链路验证清单（KB 录入 → embedding 生成 → LanceDB 持久化 → 语义检索 → RAG prompt 注入），通过后方可发布。

**不在本阶段：**
- Linux 打包兼容（Windows 先收口；Linux 标注为下一里程碑待办）
- 模型版本热更新或多版本共存
- 烟测自动化（Playwright / CI 驱动）
- 知识库 UI / RAG 逻辑改动（Phase 20–22 已完成）

</domain>

<decisions>
## Implementation Decisions

### hiddenimports 边界与门禁

- **D-01:** 最小增量策略 — 仅在 `ctrx_backend.spec` 补充 LanceDB/pyarrow/sentence-transformers 缺口，不做全量显式列举。现有条目保持不变。
- **D-02:** 平台范围：仅 Windows 收口（`windows_hidden` 列表）；Linux 标注为下一里程碑任务，暂不阻断本阶段。
- **D-03:** 严格门禁：`scripts/check_hiddenimports_diff.py` 已在项目中，hiddenimports 变更必须同步更新 changelog（门禁脚本比较 spec 与 changelog diff）；changelog 未更新时阻断 CI/PR。
- **D-04:** 打包产物出现 `ModuleNotFoundError` → 阻断发布，不带已知问题发布。

### 离线模型打包布局

- **D-05:** 模型权重目录放置于 `electron/resources/models/bge-m3/`（版本化子目录），随 extraResources 打入安装包。
- **D-06:** 固定单活版本 — 包内仅保留当前使用的 bge-m3 版本，不做多版本并存。
- **D-07:** 安装包强制内置模型权重 — 不做首次启动下载逻辑；模型必须在打包时已就位。
- **D-08:** 模型目录缺失或损坏时（Electron 层面检查）：快速失败并输出明确错误信息，不静默降级。（注意：与 Phase 20 D-06 不矛盾——Phase 20 的软降级处理的是 Python 运行时模型加载失败；D-08 处理的是 Electron 主进程发现 extraResources 中模型目录完全不存在的情况。）

### 运行时环境变量绑定

- **D-09:** 仅 Electron 主进程负责注入 `SENTENCE_TRANSFORMERS_HOME`、`TRANSFORMERS_CACHE`、`CTRX_MODELS_DIR`；后端不做自解析。
- **D-10:** 每次 spawn/restart 后端子进程时均注入上述变量（不限于首次启动）。
- **D-11:** 模型路径由 manifest（`.backend-manifest.json`）+ extraResources 相对路径推导，不硬编码绝对路径。
- **D-12:** 若系统已有同名环境变量（如 `TRANSFORMERS_CACHE`），应用注入值覆盖系统值。

### 烟测契约

- **D-13:** 执行方式：纯手动清单 — 一份可跟随操作的文字步骤，任何人可在已安装的打包产物上执行。不做 Playwright/自动化。
- **D-14:** 通过标准（四项全达到方算通过）：
  1. 后端启动日志无 `ModuleNotFoundError`（embedding 模型加载行可见）
  2. PathB 页录入并提交后出现「已存入 N 条」 `ElMessage.success` 提示
  3. 知识库配置页刷新后可见该新录入条目
  4. 重新处理一份含业绩报酬条款的合同后，后端日志包含 `RAG context` 或 `few-shot` 关键字（证明注入块已构造）
- **D-15:** RAG 注入验证方式：后端日志关键字（不需要额外 debug 接口）。
- **D-16:** 烟测失败时阻断发布 — 与 hiddenimports 门禁策略一致。

### Claude's Discretion

- 具体 hiddenimports 条目（lancedb 子模块完整列表、pyarrow 版本绑定、sentence-transformers 依赖链）由 researcher 从已安装的 `.venv` 和 lancedb 文档中审计，planner 整理成最终列表。
- extraResources 在 `package.json` electron-builder 配置中的 `from`/`to` 字段格式由 planner 确认，参考 Phase 12/14 已有模式。
- `check_hiddenimports_diff.py` 对应的 changelog 文件路径与格式由 planner 确认（脚本已存在，可能需要创建对应 changelog 文件）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 需求与阶段边界

- `contract_info/.planning/ROADMAP.md` — Phase 23 目标与 Success Criteria（3 条）
- `contract_info/.planning/REQUIREMENTS.md` — `KB-PKG-01~03` 需求定义

### 打包配置（直接修改目标）

- `contract_info/ctrx_backend.spec` — PyInstaller spec，hiddenimports 增量在此修改
- `contract_info/package.json` — electron-builder 配置，extraResources 在此声明
- `contract_info/scripts/build.ps1` — 4 步构建流水线（Step 1 = package_backend.ps1）
- `contract_info/scripts/package_backend.ps1` — 调用 pyinstaller + 将产物复制至 `electron/resources/`

### 门禁脚本

- `contract_info/scripts/check_hiddenimports_diff.py` — hiddenimports 变更 vs changelog 比对门禁；需了解其 `--spec` / `--changelog` 参数以确认 changelog 文件位置

### 运行时路径注入（Electron 侧）

- `contract_info/electron/main.ts` — 后端子进程 spawn/restart 逻辑；`CTRX_MODELS_DIR` 注入在此扩展
- `contract_info/electron/store.ts` — electron-store 配置，manifest 路径读取模式参考

### 模型与后端服务层

- `contract_info/backend/app/config.py` — `models_dir()` 函数（读 `CTRX_MODELS_DIR`）；`data_dir()` 模式参考
- `contract_info/backend/app/services/kb_service.py` — 模型加载与 embedding 生成入口；CTRX_MODELS_DIR 被 `models_dir()` 消费

### 上游打包先例（v1.2）

- `contract_info/.planning/milestones/v1.2-ROADMAP.md` — Phase 12 PyInstaller 打包历史（`--onedir` 决策、hiddenimports 审计模式）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ctrx_backend.spec`** — 已有 `common_hidden`/`windows_hidden` 分平台列表结构，直接向 `windows_hidden`（或 `common_hidden`）追加 lancedb/sentence-transformers 条目；`find_spec` 可选依赖模式可参考现有 `openai` 条目。
- **`package_backend.ps1`** — 已有 `electron/resources/` 复制逻辑；extraResources 路径与 manifest 模式固定，模型目录打包遵循相同约定。
- **`backend/app/config.py` `models_dir()`** — 已读 `CTRX_MODELS_DIR`，后端侧路径消费已就位，Phase 23 仅需确保注入时机正确。
- **`scripts/check_hiddenimports_diff.py`** — 门禁脚本已实现；Phase 23 需确认 changelog 文件位置并补充更新机制。

### Established Patterns

- **`--onedir` PyInstaller** — v1.2 已选定，不用 `--onefile`（规避 AV 误报）；本阶段延续。
- **extraResources 路径约定** — 现有模式：`electron/resources/<backend-dir>/`；模型目录遵循 `electron/resources/models/bge-m3/`。
- **环境变量注入** — `CTRX_DATA_DIR` 由 Electron 主进程注入的模式已有；`CTRX_MODELS_DIR` / `SENTENCE_TRANSFORMERS_HOME` / `TRANSFORMERS_CACHE` 遵循相同模式扩展。

### Integration Points

- `ctrx_backend.spec` hiddenimports 列表 → PyInstaller 打包时自动引入
- `package.json` `build.extraResources` → electron-builder 将 `electron/resources/models/` 打入安装包
- `electron/main.ts` spawn/restart 后端时的 `env` 对象 → 注入 `CTRX_MODELS_DIR` + `SENTENCE_TRANSFORMERS_HOME` + `TRANSFORMERS_CACHE`
- `backend/app/config.py` `models_dir()` → 消费 `CTRX_MODELS_DIR`，供 `kb_service.py` 加载模型

</code_context>

<specifics>
## Specific Ideas

- 模型权重目录路径：`electron/resources/models/bge-m3/`；`CTRX_MODELS_DIR` 指向 `<resourcesPath>/models`，`SENTENCE_TRANSFORMERS_HOME` 同路径（sentence-transformers 按 `<HOME>/<model-id>` 查找）。
- hiddenimports changelog：建议创建 `docs/hiddenimports-changelog.md`（或 `HIDDENIMPORTS-CHANGELOG.md`），记录每次变更的包名、原因、日期；门禁脚本已有 `--changelog` 参数接收该路径。
- 烟测清单建议产出为 `docs/smoke-test-23.md`，作为发布前人工执行的可跟随步骤文档。

</specifics>

<deferred>
## Deferred Ideas

- Linux 打包兼容（`linux_hidden` 列表 + AppImage 烟测）→ 下一里程碑
- 烟测自动化（Playwright 驱动 Electron 全链路）→ 超出内部工具当前需求
- 模型权重在线更新机制 → 超出 v1.4 范围

</deferred>

---

*Phase: 23-PyInstaller 打包兼容与烟测*
*Context gathered: 2026-06-02*
