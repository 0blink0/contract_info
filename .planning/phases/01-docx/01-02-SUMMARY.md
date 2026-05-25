---
phase: 01-docx
plan: 02
subsystem: parse
tags: [docx, python-docx, cli, pytest]
provides:
  - parse_docx() → Document JSON with outline and blocks
  - CLI parse command with optional --persist
  - unit tests on example contract
affects: [phase-02-extract, phase-03-xlsx]
tech-stack:
  added: [python-docx, click]
  patterns: [regex chapter outline, block-ordered docx iteration]
key-files:
  created:
    - backend/app/parse/docx_parser.py
    - backend/app/parse/outline.py
    - backend/app/services/parse_service.py
    - backend/cli.py
    - backend/tests/test_docx_parser.py
  modified:
    - README.md
key-decisions:
  - "Outline via Chinese chapter regex only (no Heading styles)"
duration: 30min
completed: 2026-05-25
---

# Phase 01 Plan 02 Summary

**docx 解析与 CLI 可用；示例合同解析出 263 个章节锚点、1261 个 blocks。**

## Accomplishments
- `parse_docx()`：段落 + 表格按文档顺序；章节 `sec_XXX`
- `python -m backend.cli parse <file.docx>` 输出摘要 JSON
- `persist_parse()` + `--persist`（需 PostgreSQL）
- pytest：5 passed（outline + docx_parser）

## Verification
```text
pytest backend/tests/test_outline.py backend/tests/test_docx_parser.py -q  → 5 passed
python -m backend.cli parse example/<合同>.docx  → outline=263 blocks=1261
```
- 集成测试 `test_cli_persist`：需 Docker + `alembic upgrade head`（本机 Docker 未运行时跳过）

## Deviations
- 修正枚举正则：数字条目不匹配 `1.1` 小节号（去掉 ASCII `.` 在序号模式中）

## Next Phase Readiness
- `parse_json` / `outline_preview` 结构稳定，可供 Phase 2 字段抽取
