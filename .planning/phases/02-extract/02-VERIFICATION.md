# Phase 2 Verification

**Date:** 2026-05-25  
**Verdict:** PASS (code + unit tests); DB migration 待本机 Docker

## Success criteria (ROADMAP)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | 示例合同抽出全称、管理人、托管人、费率 | PASS — 规则层 pytest + CLI |
| 2 | LLM JSON schema + warnings | PASS — Pydantic + validate_enums |
| 3 | 结果 JSON 存 DB | PARTIAL — 代码就绪；`alembic upgrade` + `--persist` 需 Docker |

## Requirements

| ID | Status |
|----|--------|
| EXT-01 | Complete (code) |
| EXT-02 | Complete (fee_rates) |
| EXT-03 | Complete (block_id/section_id/snippet) |
| EXT-04 | Complete (dicts + warnings) |
| DEV-02 | Complete (pytest + CLI extract) |

## Manual follow-up

```powershell
docker compose up -d
alembic upgrade head
python -m backend.cli parse example\*.docx --persist
python -m backend.cli extract --file-id <uuid> --persist
```
