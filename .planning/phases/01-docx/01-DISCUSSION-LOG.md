# Phase 1: 项目骨架与 docx 解析 - Discussion Log

> **Audit trail only.** Decisions are in `01-CONTEXT.md`.

**Date:** 2026-05-25  
**Phase:** 1 — 项目骨架与 docx 解析  
**Areas discussed:** 目录与交付形态, PostgreSQL, docx 解析, 文件存储

---

## 目录与交付形态

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 CLI + pytest | Phase 4 再做 API | ✓ |
| CLI + 最小 FastAPI | 空壳提前 | |
| 以 FastAPI 为主 | Phase 1 即有 upload | |

| Option | Description | Selected |
|--------|-------------|----------|
| contract_info/backend/ | 与 ROADMAP 一致 | ✓ |
| contract_info/src/ | 扁平 | |
| 对齐 bid_tool_agents | 深层目录 | |

## PostgreSQL

| Option | Description | Selected |
|--------|-------------|----------|
| contract_info 独立 docker-compose | 与 bid_tool 解耦 | ✓ |
| 本机 PostgreSQL | 手动建库 | |
| 复用 bid_tool 同一库 | 不推荐 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 元数据字段 | id, status, filename... | ✓ |
| parse_json (jsonb) | 完整 Document | ✓ |
| 章节摘要 outline_preview | 便于查询 | ✓ |
| storage_path | 原文件路径 | （存储区另确认 ✓） |

## docx 解析

| Option | Description | Selected |
|--------|-------------|----------|
| python-docx | 主库 | ✓ |
| ZIP+XML | 无依赖 | |
| 主+兜底 | 双路径 | |

| Option | Description | Selected |
|--------|-------------|----------|
| 中文序号正则 | 基金合同体例 | ✓ |
| Word Heading 样式 | | |
| 混合 | | |

## 文件存储

| Option | Description | Selected |
|--------|-------------|----------|
| uploads/{file_id}/ | 磁盘存原文件 | ✓ |
| data/files/{uuid} | 扁平 | |
| Phase 1 不持久化 | 仅 example | |

| Option | Description | Selected |
|--------|-------------|----------|
| DB 增加 storage_path | 与 uploads 配合 | ✓ |
| 仅 jsonb | 不入路径 | |

## Claude's Discretion

- 正则细节、迁移工具选型、pytest 布局

## Deferred Ideas

- FastAPI stub、bid_tool 共库、Heading 样式 outline、Phase 1 抽取/Excel
