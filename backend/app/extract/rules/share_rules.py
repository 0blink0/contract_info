from __future__ import annotations

import re
from typing import Any

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


def _is_graded_product(product_elements: dict[str, Any]) -> bool:
    structure = _field_text(product_elements.get("份额结构"))
    if structure:
        if "不分级" in structure:
            return False
        if "分级" in structure:
            return True
    struct_type = _field_text(product_elements.get("结构类型"))
    return bool(struct_type and "母子" in struct_type)


def extract_share_classes_rules(
    document: dict[str, Any],
    windows: dict[str, str],
    *,
    fund_name: str | None,
    fund_code: str | None,
    product_elements: dict[str, Any],
) -> list[ShareClassRow]:
    if not _is_graded_product(product_elements):
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
        rows.append(
            ShareClassRow(
                基金全称=fund_name,
                基金代码=fund_code,
                分级份额名称=label + (f"（{extra}）" if extra else ""),
                分级份额简称=f"{code}类",
                代码类型=label,
            )
        )

    if not rows and fund_name:
        rows.append(
            ShareClassRow(
                基金全称=fund_name,
                基金代码=fund_code,
                代码类型="A份额",
            )
        )
    return rows
