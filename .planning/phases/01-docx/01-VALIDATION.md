---
phase: "01"
phase_slug: docx
date: 2026-05-25
---

# Phase 01 Validation Strategy

## Coverage

| Requirement | Validation |
|-------------|------------|
| DOC-02 | pytest: parse 输出含 `outline`, `blocks`, `format==docx` |
| DOC-03 | pytest/CLI --persist: DB 行 status=parsed，jsonb 非空 |
| DEV-01 | README 含 venv、compose、pytest 命令 |
| DEV-02 | `pytest backend/tests` 在 example docx 上通过 |

## Commands

```bash
cd contract_info
docker compose up -d
pytest backend/tests -q
python -m backend.cli parse example/*.docx --persist
```
