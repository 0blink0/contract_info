# Phase 8：路径 B JSON — 实现模式

**映射日期：** 2026-05-26  
**参照：** Phase 7 `subscription_rules`、Phase 6 黄金/规则 CI、`08-CONTEXT.md`

## 与 Phase 7 的关键差异

| 维度 | Phase 7（申赎） | Phase 8（路径 B） |
|------|-----------------|-------------------|
| 产物 | `extraction_result.subscription_fees[]` + xlsx | 独立列 **`path_b_json`**（JSONB） |
| 持久化时机 | 抽取进 `extraction_result`；路径在 **export** | **extract 同次** 写入 `path_b_json` |
| API | `FileResponse` 下载，`status=exported` | `GET .../path-b` 返回 JSON，`status ≥ extracted` |
| 导出层 | `export/` 五表之一 | **无** export 变更 |

## 推荐文件布局

```
backend/app/extract/
├── schemas.py              # PathBDocument / PerformanceFeeModule / OpenDayModule / Tier
├── path_b_assemble.py      # FieldValue → JSON + source_snippets
├── pipeline.py             # 返回 (result, warnings, path_b_dict)
├── rules/path_b_rules.py   # extract_path_b_rules
└── llm/path_b_extract.py   # 可选 tiers refine

backend/app/services/extract_service.py   # persist path_b_json
backend/app/models/contract_file.py     # path_b_json JSONB
alembic/versions/006_path_b_json.py
backend/tests/test_path_b_rules.py
backend/tests/test_api_path_b.py
```

## 集成要点

- **不进** `ExtractionResult` / `merge_extraction`
- **门禁：** 复用 `PREVIEW_STATUSES`（非 `exported` 专用）
- **Alembic：** 仿 `002` JSONB，非 `005` Text 路径列

## 可复用习惯（subscription_rules）

- `(document, windows, fund_name, product_elements)`
- 窗不足 → 扫 `blocks` 段落
- `LlmOff` 于 CI 测试

---

*Phase: 08-path-b-json*
