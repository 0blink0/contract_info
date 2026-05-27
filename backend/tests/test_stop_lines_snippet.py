import re

from backend.app.extract.rules.product_rules import (
    _RE_NO_STOP_LINES,
    _stop_lines_snippet,
)


def test_no_stop_lines_match_includes_both_terms():
    text = "（九）基金的预警与止损（如有）：本基金不设置预警线、止损线。"
    m = _RE_NO_STOP_LINES.search(text)
    assert m is not None
    assert "止损线" in m.group(0)
    snippet = _stop_lines_snippet(text, m)
    assert "预警线" in snippet
    assert "止损线" in snippet


def test_no_stop_lines_regex_not_truncated_at_warning_only():
    text = "本基金不设置预警线、止损线。"
    m = _RE_NO_STOP_LINES.search(text)
    assert m is not None
    assert m.group(0).endswith("止损线") or "止损线" in m.group(0)
