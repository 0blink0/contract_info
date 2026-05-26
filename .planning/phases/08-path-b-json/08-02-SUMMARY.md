# 08-02 执行摘要

**状态：** 完成  
**日期：** 2026-05-26

## 交付

- Alembic `006_path_b_json`（JSONB）
- `ContractFile.path_b_json`
- `extract_service` 在 `persist_extract` 同次写入 `path_b_json`
- `test_extract_persist` 断言 path_b 字段

## 验证

ORM 列存在；集成测需 DB + `alembic upgrade head`
