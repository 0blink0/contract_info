# Phase 3: Excel 模板填充 - Context

**Gathered:** 2026-05-25  
**Status:** Ready for planning

<domain>
## Phase Boundary

将 Phase 2 的 **`extraction_result`** 填入官方导入母版，生成 **两个 xlsx**（产品要素、运营费率），表头与 `templates/` 母版一致；路径写入 PostgreSQL；通过 **CLI + pytest** 验证。

**本阶段包含：** openpyxl 填表、列映射（含重复列）、日期格式归一、必填校验 warnings、母版 sheet 保留、DB 路径列与 `exported` 状态、`export` CLI。

**本阶段不包含：** HTTP 下载 API（Phase 4）、前端（Phase 5）、锁定期/分级子表 sheet 填行、ZIP 打包、批量多合同一行文件、基金代码自动抽取。

</domain>

<decisions>
## Implementation Decisions

### 母版与写入策略
- **D-01:** 运行时母版目录 **`contract_info/templates/`**，从 `example/` 复制母版并 **提交到 git**（与官方模板同步，不运行时读 example）。
- **D-02:** 输出 xlsx **保留母版全部 sheet**（数据 sheet + 填写说明 + 字典 sheet），与系统导入模板一致。
- **D-03:** **产品要素模板**：每份合同 **1 行数据**（第 3 行写入，保留第 1–2 行标题/表头）；仅填 extraction 中存在的 **P1 字段**，其余列留空。
- **D-04:** **运营费率模板**：`fee_rates[]` **每种运营费类型一行**（管理费、托管费、投顾等）；数据行从母版表头行之后追加（遵循母版第 3 行表头、第 4 行起示例行的结构）。

### 列映射与格式
- **D-05:** 维护 **列名/别名映射**（模板表头 ↔ `extraction_result` 键，含 `费率（%/年）` ↔ `rate_annual_pct` 等）。
- **D-06:** 模板 **重复列**（开放日规则、止损线各 2 列）：**同一逻辑字段写入两列相同值**。
- **D-07:** 日期字段导出格式 **`yyyy/m/d`**（如 `2020/3/23`），写入前从抽取值归一。
- **D-08:** **基金代码** 合同常无：**留空**（不引入 CLI `--fund-code`，可后续加）。

### 必填缺失与 warnings
- **D-09:** 必填缺失时 **仍生成 xlsx**（空单元格），并将问题 **追加到 `extraction_warnings`**（或专用 export 段），CLI 打印摘要；**不**阻断文件生成。
- **D-10:** 不单独写 `export_validation.json`（本阶段）；校验信息走 **DB warnings + CLI**。

### 输出路径与数据库
- **D-11:** 生成文件目录 **`exports/{file_id}/product_elements.xlsx`** 与 **`exports/{file_id}/fee_rates.xlsx`**（相对 `contract_info/` 根）。
- **D-12:** DB 新增 **`product_xlsx_path`**、**`fee_xlsx_path`**（text，相对路径）。
- **D-13:** `status`：**`extracted` → `exporting` → `exported` | `export_failed`**。

### CLI
- **D-14:** **独立** `export` 子命令（不强制 `run-all`）；**默认从 DB** `--file-id`（需已 `extract --persist`）；支持 **`--from-json`** 调试路径。
- **D-15:** 不新增 `parse→extract→export` 一键命令（Phase 4 编排）；Phase 3 文档写清三步顺序。

### Claude's Discretion
- openpyxl 复制母版方式（shutil 复制后改 vs load_workbook 另存）
- 必填列清单来源（`template_analysis.txt` + FIELD_SPEC 必填列）
- `exporting` 失败时是否保留半成品 xlsx
- pytest 断言：表头 hash 或列名列表对比

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目与范围
- `contract_info/.planning/PROJECT.md` — 路径 A、输出 xlsx
- `contract_info/.planning/REQUIREMENTS.md` — XLS-01–03
- `contract_info/.planning/ROADMAP.md` — Phase 3 成功标准
- `contract_info/.planning/phases/01-docx/01-CONTEXT.md` — `templates/` 目录约定
- `contract_info/.planning/phases/02-extract/02-CONTEXT.md` — `extraction_result` 形状

### 模板与字段
- `contract_info/FIELD_SPEC.md` — 列名、重复列、P1 范围
- `contract_info/template_analysis.txt` — sheet 名、行号、列序
- `contract_info/field_instructions.txt` — 日期/枚举格式
- `contract_info/example/产品要素-2.xlsx` — 母版来源（复制到 templates/）
- `contract_info/example/产品运营费率导入模板-1.xlsx` — 费率母版来源

### 已实现代码
- `contract_info/backend/app/extract/schemas.py` — ExtractionResult / FeeRateRow
- `contract_info/backend/app/services/extract_service.py` — 读取 extraction
- `contract_info/backend/app/models/contract_file.py` — 待扩展 path 列
- `contract_info/backend/cli.py` — 扩展 `export`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **openpyxl** 已在 `requirements.txt`（`export_dicts.py`）。
- **`extraction_result_to_dict`** / DB `extraction_result` jsonb。
- **`dicts/*.json`** — 导出时不必再读 xlsx 字典（母版 sheet 已保留）。

### Established Patterns
- CLI-only；`uploads/{file_id}/` 存 docx；**`exports/{file_id}/`** 为本阶段输出根。
- Warnings 分列：`extraction_warnings`。

### Integration Points
- Phase 4 API 返回 `product_xlsx_path` / `fee_xlsx_path` 下载。
- Phase 5 前端链至下载链接。

</code_context>

<specifics>
## Specific Ideas

- 母版 **提交 git**，避免每台机器手动 copy。
- 运营侧需要 **完整官方 xlsx**（含字典 sheet），不能只导数据 sheet。
- 必填缺失也要给运营 **可编辑 xlsx**，warnings 提示补录。

</specifics>

<deferred>
## Deferred Ideas

- **ZIP 打包** 两个 xlsx — Phase 4/5 下载体验
- **`run-all` 一键** docx→xlsx — API 阶段编排
- **CLI `--fund-code`** — 用户选留空
- **锁定期/分级子表 sheet 填行** — Phase 2 已推迟
- **多合同多行批量** — v2 XLS-10

### Reviewed Todos (not folded)
（无）

</deferred>

---
*Phase: 03-xlsx-export*  
*Context gathered: 2026-05-25*
