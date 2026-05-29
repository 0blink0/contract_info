"""Resolve per-field evidence snippets by anchor anywhere in the chapter window."""

from __future__ import annotations

import re

from backend.app.extract.text_limits import excerpt_for_display

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
    "运作方式": ("运作方式为", "运作方式", "开放式", "封闭式"),
    "产品存续期": ("存续期", "产品存续期"),
    "管理类型": ("管理类型", "主动管理", "被动管理"),
    "份额结构": ("份额结构", "分级", "不分级"),
    "结构类型": ("结构类型",),
    "产品分类": ("产品分类",),
    "默认分红方式": ("分红方式", "默认分红"),
    "最低持有类型": ("最低持有", "最低持有份额", "最低持有金额"),
    "最低持有数量": ("最低持有", "最低持有份额", "最低持有金额"),
    "首次申购起点": ("首次申购", "首次认购", "申购起点"),
    "追加起点": ("追加申购", "追加认购", "追加起点"),
    "计费基准": ("计费基准",),
    "计费频率": ("计费频率",),
    "冷静期回访": ("冷静期", "回访"),
    "基金转换方式": ("基金转换",),
    "基金转换限制": ("基金转换",),
    "金额赎回方式": ("金额赎回",),
}

_SECTION_HEAD = re.compile(r"（[一二三四五六七八九十百]+）")
_STRICT_SECTION_FIELDS = frozenset({"风险收益特征", "业绩比较基准"})
_PLAIN_SECTION_STOP = re.compile(
    r"\n(?:投资目标|投资范围|投资策略|投资限制|业绩比较基准|风险收益特征|"
    r"投资经理|预警止损机制|十二、|七、)(?:\s*\n|\s*$)"
)


def _slice_from_anchor(text: str, anchor: str) -> str | None:
    """From anchor through next numbered subsection (or end of window)."""
    pos = text.find(anchor)
    if pos < 0:
        return None
    start = pos
    if anchor.startswith("（") and pos > 0:
        start = max(0, pos - 8)
    tail = text[pos + len(anchor) :]
    next_sec = _SECTION_HEAD.search(tail)
    if next_sec and next_sec.start() > 20:
        end = pos + len(anchor) + next_sec.start()
    else:
        end = len(text)
    chunk = text[start:end].strip()
    if len(chunk) > 20:
        return chunk
    return None


def _plain_section_body(
    field: str,
    window_text: str,
) -> tuple[str | None, str | None]:
    m = re.search(rf"(?:^|\n){re.escape(field)}\s*\n", window_text)
    if not m:
        return None, None
    tail = window_text[m.end() :]
    stop = _PLAIN_SECTION_STOP.search(tail)
    stop2 = _SECTION_HEAD.search(tail)
    end = len(tail)
    if stop:
        end = min(end, stop.start())
    if stop2 and stop2.start() > 4:
        end = min(end, stop2.start())
    body = re.sub(r"\s+", " ", tail[:end].strip())
    if len(body) < 4:
        return None, None
    snip = excerpt_for_display(f"{field}\n{body}")
    return body, snip


def extract_section_body(
    field: str,
    window_text: str,
) -> tuple[str | None, str | None]:
    """Body text between section anchor and the next numbered subsection header."""
    if not window_text.strip():
        return None, None
    if field not in _STRICT_SECTION_FIELDS:
        plain = _plain_section_body(field, window_text)
        if plain[0]:
            return plain
    anchors = _FIELD_ANCHORS.get(field, ())
    if field in _STRICT_SECTION_FIELDS:
        anchors = tuple(a for a in anchors if a.startswith("（"))
    for anchor in anchors:
        pos = window_text.find(anchor)
        if pos < 0:
            continue
        start = pos + len(anchor)
        tail = window_text[start:]
        tail = re.sub(r"^[：:\s]+", "", tail)
        next_sec = _SECTION_HEAD.search(tail)
        if next_sec and next_sec.start() > 4:
            body = tail[: next_sec.start()].strip()
        else:
            body = tail.strip()
        body = re.sub(r"\s+", " ", body)
        if len(body) < 4:
            continue
        snippet = resolve_field_snippet(field, window_text, body[:80]) or _slice_from_anchor(
            window_text, anchor
        )
        return body, excerpt_for_display(snippet or body)

    return None, None


def resolve_field_snippet(
    field: str,
    window_text: str,
    value: str | None = None,
) -> str:
    """Locate evidence by heading/keyword in the full window."""
    if not window_text.strip():
        return ""
    for anchor in _FIELD_ANCHORS.get(field, ()):
        chunk = _slice_from_anchor(window_text, anchor)
        if chunk:
            return excerpt_for_display(chunk)
    if value:
        val = str(value).strip()
        if val in ("无", "不支持", "不封闭", "支持"):
            for anchor in _FIELD_ANCHORS.get(field, ()):
                chunk = _slice_from_anchor(window_text, anchor)
                if chunk and val in chunk:
                    return excerpt_for_display(chunk)
        min_len = 2 if field in _FIELD_ANCHORS else 6
        if len(val) >= min_len:
            needle = val[: min(60, len(val))]
            pos = window_text.find(needle)
            if pos >= 0:
                start = max(0, pos - 40)
                end = min(len(window_text), pos + len(needle) + 200)
                return excerpt_for_display(window_text[start:end].strip())
    return ""
