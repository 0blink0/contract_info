"""Unit tests for merge_field value validation (LLM-first)."""

from backend.app.extract.merge import merge_field
from backend.app.extract.schemas import FieldValue


def _fv(value: str, confidence: str = "high", source: str = "llm") -> FieldValue:
    return FieldValue(value=value, confidence=confidence, source=source)  # type: ignore[arg-type]


def test_invalid_rule_with_guarantee_llm_wins():
    rule = _fv("私募基金管理人保证所提供的资料真实", source="rule")
    llm = _fv("北京石云科技有限公司")
    out = merge_field(rule, llm, field_name="管理人")
    assert out is llm
    assert out.value == "北京石云科技有限公司"


def test_llm_preferred_over_rule():
    rule = _fv("北京石云科技有限公司", source="rule")
    llm = _fv("其他管理有限公司")
    out = merge_field(rule, llm, field_name="管理人")
    assert out is llm


def test_empty_rule_uses_llm():
    out = merge_field(None, _fv("R4"), field_name="风险等级")
    assert out.value == "R4"
