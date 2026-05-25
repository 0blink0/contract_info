---
phase: "03"
phase_slug: xlsx-export
created: "2026-05-25"
---

# Phase 3 Validation Strategy

| Dimension | Approach |
|-----------|----------|
| Correctness | 读回 xlsx：基金全称、管理人、管理费类型行 |
| Regression | `test_export_*.py` in CI |
| Integration | `export --file-id` + path columns |
| Security | 不写 formula 宏；路径在 project 内 |

## Commands

```powershell
pytest backend/tests/test_export_product.py backend/tests/test_export_fee.py -q
python -m backend.cli export --from-json path/to/extraction.json --out-dir exports/test
```
