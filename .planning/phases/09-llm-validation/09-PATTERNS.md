# Phase 9：LLM 校验层 — 实现模式

**映射日期：** 2026-05-26

## 包布局

```
backend/app/validate/          # 新建（勿与 extract/validate.py 混淆）
├── __init__.py
├── schemas.py                 # ValidationItem, ValidationResult
├── evidence.py                # collect_validation_candidates
├── llm_validator.py           # run_llm_validation (async)
└── prompts.py                 # build_validation_messages

backend/app/services/
└── validation_service.py      # persist_validation

backend/app/extract/validate.py  # 不动 — validate_enums only
```

## 集成顺序

`persist_extract` → 写 extraction/path_b/warnings → **`persist_validation`** → status=extracted

`run_pipeline` 无需改（extract 已含校验）

## API 模式

同 Phase 8 `GET /path-b`：`PREVIEW_STATUSES` + 404 if missing

---

*Phase: 09-llm-validation*
