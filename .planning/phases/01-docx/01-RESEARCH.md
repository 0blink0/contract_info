# Phase 1 Research: 项目骨架与 docx 解析

**Researched:** 2026-05-25  
**Phase:** 01 — docx 解析与 PostgreSQL 留档

## Summary

Greenfield Python 子项目，目标是用 **python-docx** 将基金合同 docx 转为带 **outline + blocks** 的 JSON，并写入 **独立 PostgreSQL**。与 `bid_tool_agents` 解耦；Phase 1 仅 **CLI + pytest**，无 FastAPI。

## Stack（本阶段采用）

| 组件 | 选型 | 理由 |
|------|------|------|
| Python | 3.11+ | 与仓库其他子项目一致 |
| docx | python-docx 1.1+ | CONTEXT D-06；段落+表格稳定 |
| DB | PostgreSQL 16 + SQLAlchemy 2 + Alembic | D-03/D-04；jsonb 存 parse 结果 |
| 配置 | pydantic-settings + `.env` | `DATABASE_URL` |
| 测试 | pytest + pytest-asyncio（若用 async session 则启用） | DEV-02 |
| 容器 | docker-compose 单服务 postgres | 独立卷，避免 bid_tool 口令问题 |

**不采用：** MinerU、FastAPI（Phase 4）、LangChain。

## docx 解析要点

1. **段落**：`document.paragraphs` → `type: paragraph`，保留 `text`。
2. **表格**：`document.tables` → `type: table`，`rows` 为 `list[list[str]]`（单元格 text strip）。
3. **章节 outline（D-07）**：对段落文本用正则匹配，建议模式：
   - `^第[零一二三四五六七八九十百]+章`
   - `^[一二三四五六七八九十]+、`
   - `^\d+、`
   - 可选：`^（[一二三四五六七八九十]+）`
4. **section_id 关联**：维护 `current_section_id`；命中 outline 时更新；后续 paragraph/table 使用该 id。
5. **outline_preview**：从 `outline` 投影 `{title, anchor_id, level}` 列表写入 DB，不必存全文。

## PostgreSQL 模型

表 `contract_files`：

| 列 | 类型 | 说明 |
|----|------|------|
| id | UUID PK | default uuid4 |
| filename | varchar | 原始文件名 |
| status | varchar | pending/parsing/parsed/failed |
| storage_path | text | 相对 contract_info 根 |
| parse_json | jsonb | nullable |
| outline_preview | jsonb | nullable |
| error_message | text | nullable |
| created_at / updated_at | timestamptz | |

索引：`status`, `created_at desc`。

## CLI 流程（D-01）

```
python -m backend.cli parse <path-to.docx> [--persist]
```

1. 若 `--persist`：复制文件到 `uploads/{id}/`，插入行 `status=parsing`。
2. 调用 `parse_docx(path)` → Document dict。
3. 更新 `parse_json`, `outline_preview`, `status=parsed`；失败则 `failed` + `error_message`。
4. 打印 `outline` 条数、`blocks` 条数、输出 JSON 路径（可选 `--out`）。

## 风险与规避

| 风险 | 规避 |
|------|------|
| compose 卷已存在导致口令不一致 | README 链到 troubleshooting doc；`.env` 与 compose 一致 |
| 合同无标准章节号 | 测试用 `example/*.docx`；outline 可为空但 blocks 非空 |
| 大 docx jsonb 过大 | Phase 1 单文件可接受；v2 可考虑截断 blocks |

## Validation Architecture

| 维度 | 策略 |
|------|------|
| 解析正确性 | pytest：`example` docx `len(blocks) > 0`，`outline` 至少 1 条（样例合同） |
| DB 集成 | pytest：插入+读取 roundtrip（可用 test DB 或 transaction rollback） |
| CLI | subprocess 或 Click 测试退出码 0 |
| 回归 | CI 可选：`pytest backend/tests -q` |

## References

- `01-CONTEXT.md` — 锁定决策
- `python-docx` 文档：Document.paragraphs / Document.tables
- `ai_bid_management/bid_tool_agents/docs/troubleshooting-postgres-docker-password.md`
