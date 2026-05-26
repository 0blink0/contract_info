from __future__ import annotations



import re

from typing import Any



from backend.app.extract.rules.subscription_rules import format_subscription_fund_name
from backend.app.extract.schemas import FieldValue, ShareClassRow



_SHARE_CLASS = re.compile(

    r"([A-D])\s*类(?:份额)?(?:[（(]([^）)]+)[）)])?", re.IGNORECASE

)





def _field_text(fv: FieldValue | dict | None) -> str | None:

    if fv is None:

        return None

    if isinstance(fv, dict):

        val = fv.get("value")

    else:

        val = fv.value

    if val is None or str(val).strip() == "":

        return None

    return str(val).strip()





def _share_letters_in_text(text: str) -> set[str]:
    return {m.group(1).upper() for m in _SHARE_CLASS.finditer(text[:150000])}


def is_graded_contract(
    product_elements: dict[str, Any],
    windows: dict[str, str] | None = None,
) -> bool:
    """True when product is graded: explicit fields or 份额分类 / A–D in subscription."""
    structure = _field_text(product_elements.get("份额结构"))
    if structure:
        if "不分级" in structure:
            return False
        if "分级" in structure:
            return True
    struct_type = _field_text(product_elements.get("结构类型"))
    if struct_type and "母子" in struct_type:
        return True
    sub = (windows or {}).get("subscription", "")
    if "份额分类" in sub:
        return True
    return len(_share_letters_in_text(sub)) >= 2





def extract_share_classes_rules(

    document: dict[str, Any],

    windows: dict[str, str],

    *,

    fund_name: str | None,

    fund_code: str | None,

    product_elements: dict[str, Any],

) -> list[ShareClassRow]:

    if not is_graded_contract(product_elements, windows):

        return []



    text = windows.get("subscription", "") + "\n" + windows.get("basic", "")

    for block in document.get("blocks") or []:

        if block.get("type") == "paragraph":

            text += "\n" + str(block.get("text") or "")



    seen: set[str] = set()

    rows: list[ShareClassRow] = []

    for m in _SHARE_CLASS.finditer(text[:150000]):

        code = m.group(1).upper()

        if code in seen:

            continue

        seen.add(code)

        label = f"{code}类份额"
        extra = m.group(2) or ""
        display = format_subscription_fund_name(fund_name, code)
        share_name = display or (label + (f"（{extra}）" if extra else ""))

        rows.append(
            ShareClassRow(
                基金全称=fund_name,
                基金代码=fund_code,
                分级份额名称=share_name,
                分级份额简称=f"{code}类",
                代码类型=label,
            )
        )

    warn = _field_text(product_elements.get("预警线"))
    stop = _field_text(product_elements.get("止损线"))
    established = _field_text(product_elements.get("成立日期"))
    if warn or stop or established:
        enriched: list[ShareClassRow] = []
        for row in rows:
            updates: dict[str, str] = {}
            if warn:
                updates["预警线"] = warn
            if stop:
                updates["止损线"] = stop
            if established:
                updates["实际成立日期"] = established
                updates["投资起始日"] = established
            enriched.append(row.model_copy(update=updates) if updates else row)
        rows = enriched

    if not rows and fund_name:

        rows.append(

            ShareClassRow(

                基金全称=fund_name,

                基金代码=fund_code,

                代码类型="A份额",

            )

        )

    return rows


