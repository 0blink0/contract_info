# Requirements: CTRX v1.4 业绩报酬知识库与 RAG 增强

**Defined:** 2026-06-02  
**Milestone:** v1.4  
**Core Value:** 上传 docx → 可导入 Excel + 路径 B 手录辅助 + 可解释校验（本地桌面，无服务器依赖）

## v1.4 Requirements

### 知识库数据层与后端（KB-BE）

- [ ] **KB-BE-01**: 后端初始化 LanceDB 本地向量表（路径在 `CTRX_DATA_DIR` 下），应用启动时自动创建（若不存在）
- [ ] **KB-BE-02**: 后端加载 sentence-transformers 多语言模型（`paraphrase-multilingual-MiniLM-L12-v2` 或同类中文支持模型），启动时预热
- [ ] **KB-BE-03**: `POST /kb/entries` — 接收一批案例（字段名/字段值/原文摘录/来源合同 job_id），生成 embedding 并存入 LanceDB，返回入库 ID 列表
- [ ] **KB-BE-04**: `GET /kb/entries` — 返回全部历史案例列表，支持 `field_name` 查询参数过滤；每条包含 id/字段名/字段值/原文摘录/来源合同文件名/入库时间
- [ ] **KB-BE-05**: `DELETE /kb/entries/{id}` — 删除指定单条案例（LanceDB 行 + 元数据）

### PathB 案例录入表格（KB-ENTRY）

- [ ] **KB-ENTRY-01**: 用户可在 PathB 详情页底部看到一个 3 列可编辑表格（字段名 / 字段值 / 原文摘录），固定展示 4 行对应字段：业绩报酬提取方式 / 业绩基准类型 / 门槛净值类型 / 提取时点
- [ ] **KB-ENTRY-02**: 表格在页面加载时自动预填当前解析结果（字段值 + 原文摘录）；字段名列不可编辑
- [ ] **KB-ENTRY-03**: 用户可手动编辑表格中的字段值和原文摘录单元格
- [ ] **KB-ENTRY-04**: 每行左侧有复选框；用户可逐行勾选要存入知识库的行
- [ ] **KB-ENTRY-05**: 用户点击「存入知识库」按钮，将勾选行批量提交至 `POST /kb/entries`，成功后提示入库条数

### 知识库配置页（KB-UI）

- [x] **KB-UI-01**: 左侧菜单新增「知识库配置」菜单项（在现有导航下方），点击进入知识库列表页
- [x] **KB-UI-02**: 知识库列表页以表格形式展示全部历史案例（字段名 / 字段值 / 原文摘录 / 来源合同 / 入库时间），支持分页或虚拟滚动
- [x] **KB-UI-03**: 用户可按字段名过滤/搜索知识库列表
- [x] **KB-UI-04**: 用户可删除单条案例，删除后列表即时刷新，并二次确认

### RAG 检索与注入（KB-RAG）

- [ ] **KB-RAG-01**: LLM 提取业绩报酬字段（`performance_fee.py` / `chapter_prompts.py`）前，自动对原文摘录进行语义检索，从 LanceDB 取 Top-K 最相似历史案例
- [ ] **KB-RAG-02**: 检索结果作为 few-shot 示例注入 LLM prompt（格式：历史案例参考列表，包含字段名/字段值/原文摘录）
- [ ] **KB-RAG-03**: 知识库为空时，提取流程正常运行（降级：无 few-shot 注入，不报错）
- [ ] **KB-RAG-04**: Settings 页面增加「RAG Top-K」配置项（整数，默认 3，范围 1–10）；配置值持久化至 electron-store

### PyInstaller 打包兼容（KB-PKG）

- [ ] **KB-PKG-01**: LanceDB 相关包（`lancedb`、`pyarrow` 等）纳入 PyInstaller `hiddenimports` 清单与打包 spec
- [ ] **KB-PKG-02**: sentence-transformers 模型权重目录（离线缓存）打包至 `extraResources`，应用启动时通过 `TRANSFORMERS_CACHE` / `SENTENCE_TRANSFORMERS_HOME` 路径变量指向该目录
- [ ] **KB-PKG-03**: 烟测验证打包产物的知识库全链路：入库（含 embedding 生成）→ LanceDB 持久化 → 语义检索 → RAG prompt 注入，全流程无异常

## Future Requirements (deferred)

- 知识库批量导入（CSV/JSON 导入历史案例）
- 知识库版本管理（回滚或快照）
- 多字段组合语义检索（当前仅原文摘录维度）
- 跨里程碑自动迁移 LanceDB schema

## Out of Scope (v1.4)

- 云端知识库同步（纯本地桌面，无服务器上传）
- 向量数据库 UI 可视化（LanceDB 文件直接操作，无单独管理界面）
- 知识库应用于非业绩报酬字段（v1.4 仅针对 PathB 的 4 个字段）
- 自动标注与主动学习（无监督标注流程）

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| KB-BE-01 | Phase 20 | Pending |
| KB-BE-02 | Phase 20 | Pending |
| KB-BE-03 | Phase 20 | Pending |
| KB-BE-04 | Phase 20 | Pending |
| KB-BE-05 | Phase 20 | Pending |
| KB-ENTRY-01 | Phase 20 | Pending |
| KB-ENTRY-02 | Phase 20 | Pending |
| KB-ENTRY-03 | Phase 20 | Pending |
| KB-ENTRY-04 | Phase 20 | Pending |
| KB-ENTRY-05 | Phase 20 | Pending |
| KB-UI-01 | Phase 21 | Complete |
| KB-UI-02 | Phase 21 | Complete |
| KB-UI-03 | Phase 21 | Complete |
| KB-UI-04 | Phase 21 | Complete |
| KB-RAG-01 | Phase 22 | Pending |
| KB-RAG-02 | Phase 22 | Pending |
| KB-RAG-03 | Phase 22 | Pending |
| KB-RAG-04 | Phase 22 | Pending |
| KB-PKG-01 | Phase 23 | Pending |
| KB-PKG-02 | Phase 23 | Pending |
| KB-PKG-03 | Phase 23 | Pending |
