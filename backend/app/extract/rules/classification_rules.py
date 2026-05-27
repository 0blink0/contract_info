from __future__ import annotations

import re
from typing import Any

from backend.app.extract.rules.share_rules import is_graded_contract
from backend.app.extract.schemas import FieldValue, ShareClassRow

_ASSOC_PRODUCT_TYPES = (
    "权益类",
    "混合类",
    "固定收益类",
    "期货和衍生品类",
    "私募证券投资母基金",
)

_RE_ASSOC_TYPE = re.compile(
    r"(?:基金的类型|产品类型(?:（协会）)?|产品类型)[：:\s]*("
    + "|".join(re.escape(t) for t in _ASSOC_PRODUCT_TYPES)
    + r")",
    re.IGNORECASE,
)
_RE_MGMT_TYPE = re.compile(
    r"管理类型[：:\s]*(自主管理型|顾问管理型|银行委外合作\(信托通道\)|"
    r"券商委外合作\(信托通道\)|其他)",
    re.IGNORECASE,
)
_RE_FUND_SECURITIES = re.compile(r"私募证券投资基金")
_RE_FUND_EQUITY = re.compile(r"股权投资基金")
_RE_DEFS_SECTION = re.compile(r"^二、释义\s*$|^释义\s*$")
_RE_BASIC_SECTION = re.compile(r"基金的基本情况|四、基金的基本情况")


def _fv(value: str, *, snippet: str) -> FieldValue:
    return FieldValue(value=value, confidence="high", source="rule", snippet=snippet[:800])


def _definitions_text(document: dict[str, Any], windows: dict[str, str]) -> str:
    parts: list[str] = []
    in_defs = False
    for block in document.get("blocks") or []:
        if block.get("type") != "paragraph":
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        if _RE_DEFS_SECTION.search(text):
            in_defs = True
            continue
        if in_defs and re.match(r"^[三四五六七八九十]+、", text):
            break
        if in_defs:
            parts.append(text)
    basic = windows.get("basic", "")
    if basic.strip():
        parts.append(basic[:12000])
    return "\n".join(parts)


def _field_text(product_elements: dict[str, Any], key: str) -> str | None:
    raw = product_elements.get(key)
    if raw is None:
        return None
    if isinstance(raw, dict):
        val = raw.get("value")
    else:
        val = getattr(raw, "value", None)
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()


def infer_share_structure(
    share_classes: list[ShareClassRow],
    windows: dict[str, str],
) -> FieldValue | None:
    """分级份额子表能产出行 → 分级结构；申购章无分级迹象 → 不分级。"""
    if share_classes:
        sub = windows.get("subscription", "")
        snip = sub[:500] if "份额分类" in sub or "类份额" in sub else ""
        if not snip and share_classes[0].分级份额名称:
            snip = f"分级份额：{share_classes[0].分级份额名称}"
        return _fv("分级结构", snippet=snip or "份额分类/A–D类份额")
    if not is_graded_contract({}, windows):
        return _fv("不分级", snippet=windows.get("subscription", "")[:300] or "无份额分类")
    return None


def extract_classification_rules(
    document: dict[str, Any],
    windows: dict[str, str],
    product_elements: dict[str, Any],
) -> dict[str, FieldValue]:
    out: dict[str, FieldValue] = {}
    basic = windows.get("basic", "")
    cover = windows.get("cover_parties", "")
    defs = _definitions_text(document, windows)
    search = "\n".join(filter(None, (basic, defs, cover)))

    title = str((document.get("metadata") or {}).get("title") or "").strip()
    if _RE_FUND_SECURITIES.search(title):
        out["基金类型"] = _fv("私募证券投资基金", snippet=title)
    elif _RE_FUND_EQUITY.search(title):
        out["基金类型"] = _fv("股权投资基金", snippet=title)

    if "基金类型" not in out:
        for block in document.get("blocks") or []:
            text = str(block.get("text") or "")
            if "4、本基金：" in text and _RE_FUND_SECURITIES.search(text):
                out["基金类型"] = _fv("私募证券投资基金", snippet=text[:200])
                break
            if _RE_FUND_SECURITIES.search(text) and "是指" in text:
                out["基金类型"] = _fv("私募证券投资基金", snippet=text[:300])
                break
        if "基金类型" not in out and _RE_FUND_SECURITIES.search(defs):
            m = re.search(r"[^\n]{0,40}私募证券投资基金[^\n]{0,80}", defs)
            snip = m.group(0) if m else "私募证券投资基金"
            out["基金类型"] = _fv("私募证券投资基金", snippet=snip)

    m = _RE_ASSOC_TYPE.search(search)
    if m:
        out["产品类型（协会）"] = _fv(m.group(1), snippet=m.group(0))

    m = _RE_MGMT_TYPE.search(search)
    if m:
        out["管理类型"] = _fv(m.group(1), snippet=m.group(0))
    else:
        advisor = _field_text(product_elements, "投资顾问")
        if advisor:
            out["管理类型"] = _fv(
                "顾问管理型",
                snippet=f"投资顾问：{advisor}",
            )
        elif re.search(r"自主管理|基金管理人.*?管理本基金", search[:80000]):
            snip_m = re.search(r"自主管理[^\n。]{0,40}", search)
            out["管理类型"] = _fv(
                "自主管理型",
                snippet=snip_m.group(0) if snip_m else "基金管理人管理本基金",
            )

    return out
