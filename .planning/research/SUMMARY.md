# Research Summary: 合同要素抽取

**Date:** 2026-05-25  
**Scope:** Greenfield in `contract_info/`（参考同仓 `ai_bid_management` 模式，不共用部署）

## Stack（推荐）

| 层 | 选型 | 说明 |
|----|------|------|
| 语言 | Python 3.11+ | venv 在 `contract_info/.venv` |
| API | FastAPI + Uvicorn | 与 bid_tool 一致，上手快 |
| ORM | SQLAlchemy 2 + Alembic | PostgreSQL 按文件建模 |
| docx | python-docx | 首期唯一解析器 |
| xlsx | openpyxl | 按母版填表，保留 sheet 结构 |
| LLM | 项目配置 OpenAI 兼容 API | 结构化 JSON 输出；P1 字段组调用 |
| 前端 | Vue 3 + Vite（或极简 HTML） | 上传/状态/下载 |
| DB | PostgreSQL | 每文件：metadata + parse_json + extract_json + artifact paths |

## Architecture

```
Frontend → FastAPI → [Parse] → [Extract] → [Export XLSX]
                ↓
           PostgreSQL (contract_files)
```

- **Parse** 只产出 Document JSON，不写 Excel。
- **Extract** 读 FIELD_SPEC：规则字段先填，低置信走 LLM。
- **Export** 纯代码写 xlsx，不让 LLM 直接改二进制。

## Pitfalls

1. 在 **bid_management 根** 跑 GSD → 规划进错目录；应固定 `contract_info` 为 project root。
2. 模板 **重复列**（开放日规则、止损线）— 导出时单逻辑源写多列。
3. 费率 **一行一条规则** — 勿合并为一行。
4. LLM 端到端填表 — 枚举/数字错误；必须校验层 + 人工抽检。

## Table Stakes

上传、解析、抽取、下载 xlsx、DB 留痕。

## Deferred

PDF/MinerU、批量 ZIP、路径 B 页面录入、RAG。
