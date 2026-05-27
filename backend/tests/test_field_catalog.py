"""Ensure every extractable product column is covered by rules or LLM windows."""

from backend.app.extract.field_catalog import (
    ALL_PRODUCT_FIELDS,
    CHAPTER_FIELDS,
    MANUAL_ONLY_PRODUCT,
    RULE_PRODUCT_FIELDS,
    SKIP_PRODUCT_FIELDS,
)


def _llm_fields() -> set[str]:
    out: set[str] = set()
    for names in CHAPTER_FIELDS.values():
        out.update(names)
    return out


def test_all_product_fields_accounted_for():
    manual = MANUAL_ONLY_PRODUCT
    covered = RULE_PRODUCT_FIELDS | _llm_fields() | SKIP_PRODUCT_FIELDS
    missing = [f for f in ALL_PRODUCT_FIELDS if f not in manual and f not in covered]
    assert not missing, f"字段未分配到规则、LLM 或 SKIP: {missing}"


def test_no_manual_fields_in_llm_windows():
    llm = _llm_fields()
    overlap = llm & MANUAL_ONLY_PRODUCT
    assert not overlap, f"人工字段误入 LLM: {overlap}"


def test_no_skip_fields_in_llm_windows():
    llm = _llm_fields()
    overlap = llm & SKIP_PRODUCT_FIELDS
    assert not overlap, f"运营录入字段误入 LLM: {overlap}"


def test_operational_dates_in_skip():
    for name in (
        "基金代码",
        "成立日期",
        "备案日期",
        "投资起始日",
        "封闭期起始日",
    ):
        assert name in SKIP_PRODUCT_FIELDS
