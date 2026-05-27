"""Unit tests for merge_field mis-extract handling (QUAL-04)."""

from backend.app.extract.merge import merge_field
from backend.app.extract.schemas import FieldValue


def _fv(value: str, confidence: str = "high", source: str = "rule") -> FieldValue:
    return FieldValue(value=value, confidence=confidence, source=source)  # type: ignore[arg-type]


def test_invalid_rule_with_guarantee_llm_wins():
    rule = _fv("私募基金管理人保证所提供的资料真实")
    llm = _fv("北京石云科技有限公司", source="llm")
    out = merge_field(rule, llm, field_name="管理人")
    assert out is llm
    assert out.value == "北京石云科技有限公司"


def test_valid_party_rule_beats_llm():
    rule = _fv("北京石云科技有限公司")
    llm = _fv("其他管理有限公司", source="llm")
    out = merge_field(rule, llm, field_name="管理人")
    assert out is rule


def test_warning_line_stays_wu():
    rule = _fv("无")
    llm = _fv("0.8", source="llm")
    out = merge_field(rule, llm, field_name="预警线")
    assert out is rule
    assert out.value == "无"


def test_long_text_prefers_longer():
    rule = _fv("力争获得投资回报。" * 3)
    llm = _fv("力争获得投资回报。" * 20, source="llm")
    out = merge_field(rule, llm, field_name="投资目标")
    assert out is rule

    out_risk = merge_field(rule, llm, field_name="风险收益特征")
    assert out_risk is rule


def test_empty_rule_uses_llm():
    out = merge_field(None, _fv("R4", source="llm"), field_name="风险等级")
    assert out.value == "R4"
