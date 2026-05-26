# Phase 8 讨论日志

**日期：** 2026-05-26  
**参与：** 用户 + Claude

## 选定灰区

- JSON 结构
- 抽取策略
- 持久化
- API/前端边界
- source_snippets

## 讨论记录

### JSON 结构

| 问题 | 选项 | 决定 |
|------|------|------|
| 顶层组织 | 两模块 / 扁平 / 你决定 | **两模块** `performance_fee` + `open_day` |
| 业绩报酬分段 | tiers[] / 单文本 / 两者 | **tiers[]** |
| 与产品要素开放日摘要 | 扩展 / 仅复制 / 独立 | **扩展** CRM 细字段 |

### 抽取策略

| 问题 | 选项 | 决定 |
|------|------|------|
| CI 默认 | 仅规则 / 必须 LLM / 你决定 | **仅规则层** |
| LLM | 可选 llm 标记 / 本阶段无 LLM / 你决定 | **可选 @pytest.mark.llm** |
| 窗口 | fees+subscription / 全文 / 你决定 | **fees + subscription**（不足时补扫全文） |

### 持久化

| 问题 | 选项 | 决定 |
|------|------|------|
| 存储位置 | 独立列 / 嵌套 result / 两者 | **`path_b_json` 列** |
| 写入时机 | extract / export / 懒加载 | **extract 阶段** |

### API 边界

| 问题 | 选项 | 决定 |
|------|------|------|
| 前端 | 仅后端 / 最小 UI / 你决定 | **仅后端（Phase 10 做 UI）** |
| API 形态 | 专用 GET / detail 内嵌 / 两者 | **`GET /jobs/{id}/path-b`** |

### source_snippets

| 问题 | 选项 | 决定 |
|------|------|------|
| 格式 | dict / list / 内联 | **扁平 dict，点分路径** |
| 与 FieldValue | 汇总 / 仅 FieldValue / 仅 snippets | **内部 FieldValue，导出汇总到 source_snippets** |
| 缺值 | null 无 snippet / snippet only / 你决定 | **无值则无 snippet + warnings** |

## Claude 酌情

- `tiers[]` 列定义、Alembic 编号、detail 摘要字段命名

## 延后

- 前端 JSON 面板 → Phase 10
- LLM 校验层 → Phase 9
