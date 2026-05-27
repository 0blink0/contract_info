"""Infer 产品类型（协会） from 投资范围/投资限制 80% 规则（协会分类惯例）。"""

from __future__ import annotations

import re

from backend.app.extract.text_limits import excerpt_for_display

_ASSOC_TYPES = (
    "权益类",
    "混合类",
    "固定收益类",
    "期货和衍生品类",
    "私募证券投资母基金",
)

# 母基金 / FOF 优先
_RE_MOTHER_FUND = re.compile(
    r"私募证券投资母基金|主要投资于.*?私募基金|投资于.*?资管产品.*?不低于.*?80%",
    re.DOTALL,
)

_CATEGORY_80_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "权益类",
        re.compile(
            r"(?:股票|股权类|权益类)(?:资产|投资)?[^。\n]{0,120}?"
            r"(?:不低于|≥|>=|至少|应当达到)?[^。\n]{0,30}?"
            r"(?:80\s*%|百分之八十)",
            re.DOTALL,
        ),
    ),
    (
        "固定收益类",
        re.compile(
            r"(?:固定收益|债券)(?:类)?(?:资产|投资)?[^。\n]{0,120}?"
            r"(?:不低于|≥|>=|至少|应当达到)?[^。\n]{0,30}?"
            r"(?:80\s*%|百分之八十)",
            re.DOTALL,
        ),
    ),
    (
        "期货和衍生品类",
        re.compile(
            r"(?:期货|衍生品)(?:及其他衍生品)?(?:类)?(?:资产|投资)?[^。\n]{0,120}?"
            r"(?:不低于|≥|>=|至少|应当达到)?[^。\n]{0,30}?"
            r"(?:80\s*%|百分之八十)",
            re.DOTALL,
        ),
    ),
]

# 反向：80% 在前、资产类别在后
_RE_80_THEN_EQUITY = re.compile(
    r"(?:80\s*%|百分之八十)[^。\n]{0,80}?(?:股票|股权|权益)",
)
_RE_80_THEN_FIXED = re.compile(
    r"(?:80\s*%|百分之八十)[^。\n]{0,80}?(?:固定收益|债券)",
)
_RE_80_THEN_DERIV = re.compile(
    r"(?:80\s*%|百分之八十)[^。\n]{0,80}?(?:期货|衍生品)",
)


def _investment_source_text(windows: dict[str, str]) -> str:
    parts: list[str] = []
    for key in ("investment", "basic"):
        t = (windows.get(key) or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def _match_category(text: str, label: str, pattern: re.Pattern[str]) -> str | None:
    m = pattern.search(text)
    if m:
        return excerpt_for_display(m.group(0))
    if label == "权益类" and _RE_80_THEN_EQUITY.search(text):
        return excerpt_for_display(_RE_80_THEN_EQUITY.search(text).group(0))  # type: ignore[union-attr]
    if label == "固定收益类" and _RE_80_THEN_FIXED.search(text):
        return excerpt_for_display(_RE_80_THEN_FIXED.search(text).group(0))  # type: ignore[union-attr]
    if label == "期货和衍生品类" and _RE_80_THEN_DERIV.search(text):
        return excerpt_for_display(_RE_80_THEN_DERIV.search(text).group(0))  # type: ignore[union-attr]
    return None


def infer_assoc_product_type(
    windows: dict[str, str],
) -> tuple[str | None, str | None]:
    """
    按投资范围/限制中的 80% 下限判断协会产品类型。
    返回 (类型, 摘录)；无法依 80% 规则判断时返回 (None, None)。
    """
    text = _investment_source_text(windows)
    if not text.strip():
        return None, None

    if _RE_MOTHER_FUND.search(text):
        m = _RE_MOTHER_FUND.search(text)
        snip = excerpt_for_display(m.group(0)) if m else "私募证券投资母基金"
        return "私募证券投资母基金", snip

    hits: list[tuple[str, str]] = []
    for label, pat in _CATEGORY_80_PATTERNS:
        snip = _match_category(text, label, pat)
        if snip:
            hits.append((label, snip))

    if len(hits) == 1:
        return hits[0][0], hits[0][1]

    # 多处 80% 约束或全文无单一类别 80% → 混合类
    if len(hits) >= 2:
        combined = excerpt_for_display(
            "；".join(s for _, s in hits[:3]),
            max_chars=500,
        )
        return "混合类", combined or hits[0][1]

    # 合同提及多类资产但无明确 80% 单一类别约束
    if re.search(r"80\s*%|百分之八十", text):
        m = re.search(r".{0,40}(?:80\s*%|百分之八十).{0,120}", text, re.DOTALL)
        snip = excerpt_for_display(m.group(0)) if m else text[:200]
        return "混合类", snip

    vague_multi = (
        sum(1 for kw in ("股票", "债券", "期货", "衍生品", "固定收益") if kw in text)
        >= 2
    )
    if vague_multi:
        for marker in ("（五）投资限制", "（三）投资范围", "投资限制", "投资范围"):
            pos = text.find(marker)
            if pos >= 0:
                return "混合类", excerpt_for_display(text[pos : pos + 400])
        return "混合类", excerpt_for_display(text[:400])

    return None, None
