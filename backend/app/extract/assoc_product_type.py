"""Infer 产品类型（协会） from 投资范围/投资限制 80% 规则（校验用，非抽取主路径）。"""

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

_RE_MOTHER_FUND = re.compile(
    r"私募证券投资母基金|主要投资于.*?私募基金",
    re.DOTALL,
)

_MIN_QUALIFIER = r"(?:不低于|不得低于|≥|>=|至少|应当达到|须达到|不少于)"

_CAT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "权益类",
        re.compile(
            r"(?:股票|股权类资产?|权益类资产?)[^。\n]{0,80}"
            + _MIN_QUALIFIER
            + r"[^。\n]{0,40}(?:80\s*%|百分之八十)"
            r"|"
            + _MIN_QUALIFIER
            + r"[^。\n]{0,40}(?:80\s*%|百分之八十)[^。\n]{0,80}(?:股票|股权类|权益类)",
            re.DOTALL,
        ),
    ),
    (
        "固定收益类",
        re.compile(
            r"(?:固定收益类?资产?|债券)[^。\n]{0,80}"
            + _MIN_QUALIFIER
            + r"[^。\n]{0,40}(?:80\s*%|百分之八十)"
            r"|"
            + _MIN_QUALIFIER
            + r"[^。\n]{0,40}(?:80\s*%|百分之八十)[^。\n]{0,80}(?:固定收益|债券)",
            re.DOTALL,
        ),
    ),
    (
        "期货和衍生品类",
        re.compile(
            r"(?:期货|衍生品|商品及金融衍生品)[^。\n]{0,80}"
            + _MIN_QUALIFIER
            + r"[^。\n]{0,40}(?:80\s*%|百分之八十)"
            r"|"
            + _MIN_QUALIFIER
            + r"[^。\n]{0,40}(?:80\s*%|百分之八十)[^。\n]{0,80}(?:期货|衍生品)",
            re.DOTALL,
        ),
    ),
]

_RE_INVESTED_ASSETS_80 = re.compile(
    r"已投资产[^。\n]{0,50}(?:80\s*%|百分之八十)"
    r"|(?:80\s*%|百分之八十)[^。\n]{0,50}已投资产",
    re.DOTALL,
)

_RE_DERIV_AS_CATEGORY = re.compile(
    r"(?:\d[、.．]\s*)?期货和衍生品类[：:]\s*(?:金融期货|商品期货|场内期权)"
    r"|(?:\d[、.．]\s*)?商品及金融衍生品类[：:]",
)

_RE_NUMBERED_CATEGORY = re.compile(
    r"\d[、.．]\s*(权益类|固定收益类|期货和衍生品类|商品及金融衍生品类|现金管理类)[：:]",
)


def _investment_source_text(windows: dict[str, str]) -> str:
    parts: list[str] = []
    for key in ("investment", "basic"):
        t = (windows.get(key) or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def _count_numbered_categories(text: str) -> list[str]:
    cats: list[str] = []
    for m in _RE_NUMBERED_CATEGORY.finditer(text):
        cat = m.group(1)
        if cat not in cats:
            cats.append(cat)
    return cats


def infer_assoc_product_type(
    windows: dict[str, str],
) -> tuple[str | None, str | None]:
    text = _investment_source_text(windows)
    if not text.strip():
        return None, None

    m = _RE_MOTHER_FUND.search(text)
    if m:
        return "私募证券投资母基金", excerpt_for_display(m.group(0))

    has_invested_80 = bool(_RE_INVESTED_ASSETS_80.search(text))
    has_deriv_category = bool(_RE_DERIV_AS_CATEGORY.search(text))
    if has_invested_80 and has_deriv_category:
        m_snip = _RE_INVESTED_ASSETS_80.search(text)
        snip = excerpt_for_display(m_snip.group(0)) if m_snip else ""
        return "混合类", snip

    deriv_cats = {"期货和衍生品类", "商品及金融衍生品类"}
    cats = _count_numbered_categories(text)
    if len(cats) >= 3 or (len(cats) >= 2 and any(c in deriv_cats for c in cats)):
        for marker in ("（三）投资范围", "投资范围", "（五）投资限制"):
            pos = text.find(marker)
            if pos >= 0:
                return "混合类", excerpt_for_display(text[pos: pos + 400])
        return "混合类", excerpt_for_display("；".join(cats))

    hits: list[tuple[str, str]] = []
    for label, pat in _CAT_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append((label, excerpt_for_display(m.group(0))))

    if len(hits) == 1:
        return hits[0][0], hits[0][1]

    if len(hits) >= 2:
        combined = excerpt_for_display(
            "；".join(s for _, s in hits[:3]), max_chars=500
        )
        return "混合类", combined or hits[0][1]

    if re.search(r"80\s*%|百分之八十", text):
        m_80 = re.search(r".{0,40}(?:80\s*%|百分之八十).{0,120}", text, re.DOTALL)
        snip = excerpt_for_display(m_80.group(0)) if m_80 else ""
        return "混合类", snip

    asset_kws = sum(
        1 for kw in ("股票", "债券", "期货", "衍生品", "固定收益") if kw in text
    )
    if asset_kws >= 2:
        for marker in ("（五）投资限制", "（三）投资范围", "投资限制", "投资范围"):
            pos = text.find(marker)
            if pos >= 0:
                return "混合类", excerpt_for_display(text[pos: pos + 400])
        return "混合类", excerpt_for_display(text[:400])

    return None, None
