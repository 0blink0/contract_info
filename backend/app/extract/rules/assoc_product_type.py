"""Infer 产品类型（协会） from 投资范围/投资限制 80% 规则（协会分类惯例）。

协会分类规则（私募证券基金）:
- 权益类     : ≥80% 总资产（或净资产）投资于股票等权益类资产
- 固定收益类  : ≥80% 总资产投资于固定收益/债券资产
- 期货和衍生品类: ≥80% 投资于期货/衍生品
- 混合类     : 无单一类别 ≥80%；或80% 相对"已投资产（不含现金）"且基金
               将衍生品列为独立投资类别（实际股票占总NAV可能<80%）
- 私募证券投资母基金: 主要投资于其他私募基金/资管产品
"""

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
    r"私募证券投资母基金|主要投资于.*?私募基金",
    re.DOTALL,
)

# 明确的"不低于"类限定词（区分"不超过"等上限约束）
_MIN_QUALIFIER = r"(?:不低于|不得低于|≥|>=|至少|应当达到|须达到|不少于)"

# 各资产类别 ≥80% 的最低约束（正向 + 反向，均要求明确的最低限定词）
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

# 80% 约束相对"已投资产"（非总资产/净资产）
# 说明：80% 分母排除了现金管理工具，实际权益占总NAV可能远低于80%
_RE_INVESTED_ASSETS_80 = re.compile(
    r"已投资产[^。\n]{0,50}(?:80\s*%|百分之八十)"
    r"|(?:80\s*%|百分之八十)[^。\n]{0,50}已投资产",
    re.DOTALL,
)

# 期货/衍生品作为独立投资类别（非仅对冲工具的简单提及）
# 特征：投资范围按"N、期货和衍生品类：金融期货..."格式列举
_RE_DERIV_AS_CATEGORY = re.compile(
    r"(?:\d[、.．]\s*)?期货和衍生品类[：:]\s*(?:金融期货|商品期货|场内期权)"
    r"|(?:\d[、.．]\s*)?商品及金融衍生品类[：:]",
)

# 投资范围按编号列举的资产类别（如"1、权益类：xxx; 2、固定收益类：xxx"）
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
    """返回投资范围中按编号明确列举的资产类别名称。"""
    cats: list[str] = []
    for m in _RE_NUMBERED_CATEGORY.finditer(text):
        cat = m.group(1)
        if cat not in cats:
            cats.append(cat)
    return cats


def infer_assoc_product_type(
    windows: dict[str, str],
) -> tuple[str | None, str | None]:
    """
    按投资范围/限制中的 80% 下限判断协会产品类型。
    返回 (类型, 摘录)；无法依规则判断时返回 (None, None)。

    判断优先级：
    1. 母基金（FOF）特征
    2. 已投资产限定 + 衍生品类别 → 混合类
       （80%权益约束分母不含现金，且基金将期货列为独立类别）
    3. 投资范围列举 ≥3 类或含衍生品的多类别 → 混合类
    4. 单一类别 ≥80% 总资产（含明确不低于限定）→ 对应类别
    5. 多类别各含 80% 约束 → 混合类
    6. 有80%提及但无单类匹配 → 混合类（保守）
    7. 无80%约束但多资产类别明确列举 → 混合类
    """
    text = _investment_source_text(windows)
    if not text.strip():
        return None, None

    # 1. 母基金优先
    m = _RE_MOTHER_FUND.search(text)
    if m:
        return "私募证券投资母基金", excerpt_for_display(m.group(0))

    # 2. "已投资产"限定 + 衍生品类别 → 混合类
    #    典型场景：指数增强/对冲策略，股票80%的分母排除现金，
    #    且将"期货和衍生品类"列为独立投资类别
    has_invested_80 = bool(_RE_INVESTED_ASSETS_80.search(text))
    has_deriv_category = bool(_RE_DERIV_AS_CATEGORY.search(text))
    if has_invested_80 and has_deriv_category:
        m_snip = _RE_INVESTED_ASSETS_80.search(text)
        snip = excerpt_for_display(m_snip.group(0)) if m_snip else ""
        return "混合类", snip

    # 3. 投资范围按编号列举 ≥3 类，或含衍生品的 ≥2 类 → 混合类
    deriv_cats = {"期货和衍生品类", "商品及金融衍生品类"}
    cats = _count_numbered_categories(text)
    if len(cats) >= 3 or (len(cats) >= 2 and any(c in deriv_cats for c in cats)):
        for marker in ("（三）投资范围", "投资范围", "（五）投资限制"):
            pos = text.find(marker)
            if pos >= 0:
                return "混合类", excerpt_for_display(text[pos: pos + 400])
        return "混合类", excerpt_for_display("；".join(cats))

    # 4. 单一类别 ≥80% 总资产（含明确最低限定）
    hits: list[tuple[str, str]] = []
    for label, pat in _CAT_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append((label, excerpt_for_display(m.group(0))))

    if len(hits) == 1:
        return hits[0][0], hits[0][1]

    # 5. 多类别各含 80% 约束（数学上不可能同时满足 → 混合类）
    if len(hits) >= 2:
        combined = excerpt_for_display(
            "；".join(s for _, s in hits[:3]), max_chars=500
        )
        return "混合类", combined or hits[0][1]

    # 6. 有 80% 提及但无单类匹配 → 混合类（保守）
    if re.search(r"80\s*%|百分之八十", text):
        m_80 = re.search(r".{0,40}(?:80\s*%|百分之八十).{0,120}", text, re.DOTALL)
        snip = excerpt_for_display(m_80.group(0)) if m_80 else ""
        return "混合类", snip

    # 7. 无 80% 约束但多资产类别明确提及 → 混合类
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
