# Requirements: 合同要素抽取（CTRX）

**Defined:** 2026-05-25  
**Core Value:** 上传 docx → 得到可导入的 Excel，减少手抄模板

## v1 Requirements

### Document Ingest

- [ ] **DOC-01**: 用户可上传单个 `.docx` 合同文件
- [ ] **DOC-02**: 系统将 docx 解析为结构化 Document JSON（段落、表格、章节锚点）
- [ ] **DOC-03**: 每个上传文件在 PostgreSQL 有唯一记录（id、文件名、状态、时间戳）

### Extraction

- [ ] **EXT-01**: 按 `FIELD_SPEC.md` P1 抽取产品要素字段（规则 + LLM）
- [ ] **EXT-02**: 按 P1 抽取运营费率行（管理费、托管费等，可多行）
- [ ] **EXT-03**: 抽取结果含字段级置信度与原文溯源（block/章节）
- [ ] **EXT-04**: 枚举字段对照模板字典 sheet 校验（业绩基准、销售机构等）

### Excel Export

- [ ] **XLS-01**: 基于 `example/产品要素-2.xlsx` 模板填充「产品要素模板」sheet
- [ ] **XLS-02**: 基于 `example/产品运营费率导入模板-1.xlsx` 填充费率 sheet
- [ ] **XLS-03**: 用户可下载生成的 xlsx；文件路径或 blob 与 DB 记录关联

### API & Frontend

- [ ] **API-01**: `POST /upload` 接收 docx，创建任务并异步/同步处理
- [ ] **API-02**: `GET /jobs/{id}` 返回解析/抽取状态与错误信息
- [ ] **API-03**: `GET /jobs/{id}/download/product-elements` 与 `.../fee-rates` 下载 Excel
- [ ] **UI-01**: 前端页面上传文件、展示任务状态、提供 Excel 下载链接

### DevEx

- [ ] **DEV-01**: `contract_info` 下 README 说明 venv 创建、依赖安装、运行测验
- [ ] **DEV-02**: 至少一个针对示例合同的 CLI 或 pytest，验证解析→抽取→xlsx 链路

## v2 Requirements

### Document Ingest

- **DOC-10**: 支持 PDF（MinerU 或 PyMuPDF）
- **DOC-11**: 批量 ZIP 上传、任务队列

### Extraction

- **EXT-10**: FIELD_SPEC P2 全量 77 字段
- **EXT-11**: 份额锁定期、分级份额子表
- **EXT-12**: 可选 RAG：相似历史合同推荐填法

### Excel Export

- **XLS-10**: 多产品合并 batch xlsx

## Out of Scope

| Feature | Reason |
|---------|--------|
| CRM 页面自动录入（业绩报酬、开放日） | 无导入模板；路径 B |
| 与 ai_bid_management 共用部署 | 独立子项目 |
| 首期 PDF | 用户明确 docx 测试 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DOC-01 | Phase 1 (01-02) | Complete |
| DOC-02 | Phase 1 (01-02) | Complete |
| DOC-03 | Phase 1 (01-01, 01-02) | Complete* |
| DEV-01 | Phase 1 (01-01) | Complete |
| DEV-02 | Phase 1 (01-02) | Complete |

\* DOC-03 `--persist` 需本机 Docker + `alembic upgrade head` 后手测确认。
| EXT-01 | Phase 2 | Pending |
| EXT-02 | Phase 2 | Pending |
| EXT-03 | Phase 2 | Pending |
| EXT-04 | Phase 2 | Pending |
| XLS-01 | Phase 3 | Pending |
| XLS-02 | Phase 3 | Pending |
| XLS-03 | Phase 3 | Pending |
| API-01 | Phase 4 | Pending |
| API-02 | Phase 4 | Pending |
| API-03 | Phase 4 | Pending |
| UI-01 | Phase 5 | Pending |

**Coverage:** v1 = 16 requirements, mapped = 16, unmapped = 0

---
*Requirements defined: 2026-05-25*
