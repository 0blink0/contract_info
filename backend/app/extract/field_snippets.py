"""Resolve per-field evidence snippets by anchor anywhere in the chapter window."""

from __future__ import annotations

import re

# Order: more specific section headers first
_FIELD_ANCHORS: dict[str, tuple[str, ...]] = {
    "投资目标": ("（二）投资目标", "投资目标"),
    "投资范围": ("（三）投资范围", "投资范围"),
    "投资策略": ("（四）投资策略", "投资策略"),
    "投资限制": ("（五）投资限制", "投资限制"),
    "业绩比较基准": ("（八）业绩比较基准", "业绩比较基准"),
    "风险收益特征": ("（十）风险收益特征", "风险收益特征"),
    "预警线": ("（十一）基金的预警与止损", "基金的预警与止损", "预警线"),
    "止损线": ("（十一）基金的预警与止损", "基金的预警与止损", "止损线"),
    "投资经理": ("（十二）投资经理", "投资经理简介", "本基金的投资经理"),
    "投资经理信息": ("（十二）投资经理", "投资经理简介", "本基金的投资经理"),
    "是否封闭": ("本基金的封闭期", "封闭期"),
    "封闭期": ("本基金的封闭期",),
    "是否支持金额赎回": (
        "基金赎回采用份额申请",
        "基金申购采用金额申请",
        "金额赎回",
    ),
    "开放日规则": ("本基金的开放日为", "开放日"),
}

_SECTION_HEAD = re.compile(r"（[一二三四五六七八九十百]+）")


def _slice_from_anchor(text: str, anchor: str, *, max_len: int = 1200) -> str | None:
    pos = text.find(anchor)
    if pos < 0:
        return None
    start = pos
    if anchor.startswith("（") and pos > 0:
        start = max(0, pos - 8)
    tail = text[pos + len(anchor) : pos + len(anchor) + max_len]
    next_sec = _SECTION_HEAD.search(tail)
    if next_sec and next_sec.start() > 20:
        end = pos + len(anchor) + next_sec.start()
    else:
        end = min(len(text), pos + max_len)
    chunk = text[start:end].strip()
    if len(chunk) > 20:
        return chunk
    return None


def resolve_field_snippet(
    field: str,
    window_text: str,
    value: str | None = None,
) -> str:
    """Locate evidence by heading/keyword in the full window — not the first N characters."""
    if not window_text.strip():
        return ""
    for anchor in _FIELD_ANCHORS.get(field, ()):
        chunk = _slice_from_anchor(window_text, anchor)
        if chunk:
            return chunk[:800]
    if value:
        val = str(value).strip()
        if val in ("无", "不支持", "不封闭", "支持"):
            for anchor in _FIELD_ANCHORS.get(field, ()):
                chunk = _slice_from_anchor(window_text, anchor)
                if chunk and val in chunk:
                    return chunk[:800]
        if len(val) >= 6:
            needle = val[: min(60, len(val))]
            pos = window_text.find(needle)
            if pos >= 0:
                start = max(0, pos - 40)
                end = min(len(window_text), pos + len(needle) + 200)
                return window_text[start:end].strip()[:800]
    return ""
