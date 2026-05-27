from __future__ import annotations

import re
from typing import Any

from backend.app.extract.rules.share_rules import _share_letters_in_text, is_graded_contract
from backend.app.extract.schemas import FieldValue, ShareClassRow
from backend.app.extract.text_limits import excerpt_for_display

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
_RE_DEFS_SECTION = re.compile(r"^二、释义\s*$|^释义\s*$")
_RE_BASIC_SECTION = re.compile(r"基金的基本情况|四、基金的基本情况")


def _fv(value: str, *, snippet: str) -> FieldValue:
    return FieldValue(
        value=value, confidence="high", source="rule", snippet=excerpt_for_display(snippet)
    )


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
        parts.append(basic)
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


def _graded_snippet_from_basic(windows: dict[str, str]) -> str | None:
    basic = (windows.get("basic") or "").strip()
    if not basic:
        return None
    if "份额分类" in basic or len(_share_letters_in_text(basic)) >= 2:
        return excerpt_for_display(basic)
    return None


def infer_share_structure(
    share_classes: list[ShareClassRow],
    windows: dict[str, str],
) -> FieldValue | None:
    """基本情况份额分类表或 A–D 类份额 → 分级结构；否则不分级。"""
    if share_classes:
        snip = _graded_snippet_from_basic(windows)
        if not snip:
            sub = windows.get("subscription", "")
            snip = (
                excerpt_for_display(sub)
                if "份额分类" in sub or "类份额" in sub
                else ""
            )
        if not snip and share_classes[0].分级份额名称:
            snip = f"分级份额：{share_classes[0].分级份额名称}"
        return _fv("分级结构", snippet=snip or "份额分类/A–D类份额")
    basic_snip = _graded_snippet_from_basic(windows)
    if basic_snip:
        return _fv("分级结构", snippet=basic_snip)
    if not is_graded_contract({}, windows):
        return _fv(
            "不分级",
            snippet=excerpt_for_display(
                windows.get("basic", "")
                or windows.get("subscription", "")
                or "无份额分类"
            ),
        )
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
        elif re.search(r"自主管理|基金管理人.*?管理本基金", search):
            snip_m = re.search(r"自主管理[^\n。]{0,40}", search)
            out["管理类型"] = _fv(
                "自主管理型",
                snippet=snip_m.group(0) if snip_m else "基金管理人管理本基金",
            )

    return out
