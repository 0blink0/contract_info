# Phase 10：集成与文档 — 调研

**调研日期：** 2026-05-26  
**领域：** 前端 v1.1 集成、preview 申赎扩展、运营文档  
**置信度：** HIGH（后端 API 已就绪）/ MEDIUM（preview 申赎需补）

<user_constraints>
## 用户约束（10-CONTEXT.md）

- 5 并列下载；Path B 折叠 + 复制/下载 JSON
- ValidationPanel 独立；默认 fail+warn；懒加载
- extracted+ 可见 path B/校验；不阻止导出
- ExportPreview 申赎 Tab；README + FIELD_SPEC + .env
</user_constraints>

<phase_requirements>
| ID | 描述 | 调研结论 |
|----|------|----------|
| UI-01 | 5 下载 + path B + 校验摘要 | JobDetail + 3 组件 |
| UI-02 | LLM 配置说明 | README + .env.example |
| API-02 | path-b + validation 消费 | 已有 GET 端点，前端 client 封装 |
| VAL-04 | 校验高亮 | ValidationPanel status 着色 |
| TEST-03 | 文档更新 | FIELD_SPEC + README |
</phase_requirements>

## 摘要

后端 **已具备**：5 表下载（含 `subscription-fee-rates`）、`GET /path-b`、`GET /validation`、`JobDetailResponse` 摘要字段。  
**缺口**：`preview_service` 无 `subscription_*`；前端 `types`/`client`/组件未接。

## 推荐波次

| Wave | 计划 | 内容 |
|------|------|------|
| 0 | 10-01 | preview 申赎 + API schema + 测试 |
| 1 | 10-02 | client/types + JobDetail + PathBPanel + ValidationPanel |
| 2 | 10-03 | ExportPreview Tab + 文档 + 10-VERIFICATION |

## Preview 扩展要点

- 常量：`SUBSCRIPTION_SHEET`、`SUBSCRIPTION_HEADER_ROW`、`SUBSCRIPTION_DATA_START_ROW`（`column_map.py`）
- xlsx 路径：`record.subscription_xlsx_path`
- extraction 兜底：`_subscription_from_extraction` 仿 `_fee_from_extraction`
- `JobPreviewResponse` 增加 `subscription_columns`、`subscription_rows`

## 前端组件

```
JobDetail.vue
  ├── WarningsList（不变）
  ├── ValidationPanel.vue  ← 新建
  ├── PathBPanel.vue       ← 新建
  └── ExportPreview.vue    ← +申赎 Tab
```

## 可见性

```typescript
const PREVIEW_PLUS = ['extracted', 'exporting', 'exported', 'export_failed']
const DOWNLOAD_ONLY = status === 'exported'
```

---
*Phase 10 research — ready for planning*
