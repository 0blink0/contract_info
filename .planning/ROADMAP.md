# Roadmap: CTRX — 合同要素抽取

**Project root:** `contract_info/`  
**Planning:** `contract_info/.planning/`

## Phases

| # | Phase | Goal | Requirements | UI hint |
|---|-------|------|--------------|---------|
| 1 | 项目骨架与 docx 解析 | venv、解析层、DB 模型、示例 docx 测验 | DOC-01–03, DEV-01–02 | no |
| 2 | 字段抽取引擎 | P1 要素 + 费率 JSON，规则+LLM，校验 | EXT-01–04 | no |
| 3 | Excel 模板填充 | 生成可导入 xlsx | XLS-01–03 | no |
| 4 | 后端 API | 上传、状态、下载 | API-01–03 | no |
| 5 | 前端上传与下载 | 运营可用最小界面 | UI-01 | yes |

---

### Phase 1: 项目骨架与 docx 解析

**Goal:** 在 `contract_info/` 下可运行：`parse(docx) → Document JSON`，并写入 PostgreSQL 占位表。

**Requirements:** DOC-01, DOC-02, DOC-03, DEV-01, DEV-02

**Success criteria:**
1. `python -m venv .venv` 与 `pip install -r requirements.txt` 文档化且通过
2. 对 `example/*.docx` 输出含 `blocks`/`outline` 的 JSON
3. `contract_files` 表可插入一条上传记录
4. pytest 或 CLI 对示例合同解析断言非空段落数

**Suggested layout:**
```
contract_info/
  backend/          # FastAPI
  frontend/         # Vue3 或 Vite 静态（Phase 5）
  example/          # 模板与样例（已有）
  templates/        # 运行时复制的 xlsx 母版
  .planning/
```

---

### Phase 2: 字段抽取引擎

**Goal:** `extract(document) → { product_elements, fee_rates[] }` 符合 FIELD_SPEC P1。

**Requirements:** EXT-01, EXT-02, EXT-03, EXT-04

**Success criteria:**
1. 示例合同抽出基金全称、管理人、托管人、管理费/托管费至少各 1 行
2. LLM 调用带 JSON schema；枚举不合规进入 `warnings`
3. 结果 JSON 存入 DB `extraction_result` 字段

---

### Phase 3: Excel 模板填充

**Goal:** `export_xlsx(extraction) → 两个 xlsx 文件`。

**Requirements:** XLS-01, XLS-02, XLS-03

**Success criteria:**
1. 输出 xlsx 可被 Excel 打开，表头与 `example/` 母版一致
2. 必填列非空或在校验报告中标明
3. 文件路径写入 DB 供下载

---

### Phase 4: 后端 API

**Goal:** HTTP 接口串联 上传 → 解析 → 抽取 → 导出。

**Requirements:** API-01, API-02, API-03

**Success criteria:**
1. Postman/curl 上传 docx 返回 job_id
2. 轮询 status 直至 `completed` 或 `failed`
3. 下载接口返回正确 Content-Type 与文件名

---

### Phase 5: 前端上传与下载

**Goal:** 非技术人员可上传并下载 Excel。

**Requirements:** UI-01

**UI hint:** yes

**Success criteria:**
1. 浏览器可选择 docx 上传
2. 展示处理中与完成/失败状态
3. 一键下载产品要素与运营费率 xlsx（或打包 zip）

---

## v2（未排期）

PDF 批量、FIELD_SPEC 全量、锁定期/分级子表、RAG — 见 REQUIREMENTS.md v2。

---
*Roadmap created: 2026-05-25*
