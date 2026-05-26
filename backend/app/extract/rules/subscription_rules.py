from __future__ import annotations

import re
from typing import Any

from backend.app.extract.schemas import ShareClassRow, SubscriptionFeeRow

_SHARE_COL = re.compile(r"([A-D])\s*类(?:份额)?", re.IGNORECASE)
_RATE_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_SHARE_LETTER = re.compile(r"^([A-D])\s*类", re.IGNORECASE)

_REDEEM_LT = re.compile(
    r"[（(]t[）)]?\s*[<＜]\s*(\d+)\s*日[^。\n]{0,120}?短期赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)
_REDEEM_RANGE = re.compile(
    r"(\d+)\s*日\s*[≤<=]\s*[（(]t[）)]?\s*[<＜]\s*(\d+)\s*日[^。\n]{0,120}?短期赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)
_REDEEM_GTE = re.compile(
    r"[（(]t[）)]?\s*[≥>＞=]\s*(\d+)\s*日[^。\n]{0,80}?不收取短期赎回"
)


def format_subscription_fund_name(full_name: str | None, share_letter: str) -> str:
    """石云：全称+份额字母；福禄：截至「一号」+ X类。"""
    if not full_name:
        return share_letter
    letter = share_letter.upper()
    if "福禄" in full_name and "一号" in full_name:
        idx = full_name.index("一号")
        return f"{full_name[: idx + 2]}{letter}类"
    if "证券投资基金" in full_name:
        return f"{full_name}{letter}"
    return f"{full_name}{letter}类"


def _parse_rate_cell(cell: object) -> str | None:
    if cell is None:
        return None
    text = str(cell).strip()
    if not text:
        return None
    m = _RATE_PCT.search(text)
    if m:
        return m.group(1)
    return None


def _share_letter_from_row(row: ShareClassRow) -> str | None:
    for raw in (row.分级份额简称, row.分级份额名称, row.代码类型):
        if not raw:
            continue
        m = _SHARE_LETTER.match(str(raw).strip())
        if m:
            return m.group(1).upper()
    return None


def _letters_from_share_classes(share_classes: list[ShareClassRow]) -> list[str]:
    letters: list[str] = []
    seen: set[str] = set()
    for row in share_classes:
        letter = _share_letter_from_row(row)
        if letter and letter not in seen:
            seen.add(letter)
            letters.append(letter)
    return letters


def _parse_share_fee_table(document: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Parse 份额分类表 → {letter: {认购费, 申购费, 赎回费}}."""
    out: dict[str, dict[str, str]] = {}
    for block in document.get("blocks") or []:
        if block.get("type") != "table":
            continue
        rows = block.get("rows") or []
        if len(rows) < 2:
            continue
        header = [str(c or "").strip() for c in rows[0]]
        col_letters: dict[int, str] = {}
        for idx, cell in enumerate(header):
            if idx == 0:
                continue
            m = _SHARE_COL.search(cell)
            if m:
                col_letters[idx] = m.group(1).upper()
        if len(col_letters) < 2:
            continue
        has_sub = any("认购" in str(r[0]) for r in rows[1:] if r)
        if not has_sub:
            continue
        for row in rows[1:]:
            if not row:
                continue
            label = str(row[0] or "").strip()
            fee_key: str | None = None
            if "认购" in label:
                fee_key = "认购费"
            elif "申购" in label:
                fee_key = "申购费"
            elif "赎回" in label:
                fee_key = "赎回费"
            else:
                continue
            for col_idx, letter in col_letters.items():
                if col_idx >= len(row):
                    continue
                rate = _parse_rate_cell(row[col_idx])
                if rate is None:
                    continue
                out.setdefault(letter, {})[fee_key] = rate
        if out:
            return out
    return out


def _extract_redeem_tiers(subscription_text: str) -> list[dict[str, str]]:
    if "短期赎回" not in subscription_text:
        return []
    tiers: list[dict[str, str]] = []
    for m in _REDEEM_LT.finditer(subscription_text):
        tiers.append(
            {
                "计费基准": "区间（P＜A）",
                "区间结束": m.group(1),
                "时间区间单位": "天",
                "费率": m.group(2),
            }
        )
    for m in _REDEEM_RANGE.finditer(subscription_text):
        tiers.append(
            {
                "计费基准": "区间（A≤P＜B）",
                "区间开始": m.group(1),
                "区间结束": m.group(2),
                "时间区间单位": "天",
                "费率": m.group(3),
            }
        )
    for m in _REDEEM_GTE.finditer(subscription_text):
        tiers.append(
            {
                "计费基准": "区间（P≥A）",
                "区间开始": m.group(1),
                "时间区间单位": "天",
                "费率": "0",
            }
        )
    return tiers


def extract_subscription_fees_rules(
    document: dict[str, Any],
    windows: dict[str, str],
    *,
    fund_name: str | None,
    share_classes: list[ShareClassRow],
    product_elements: dict[str, Any],
) -> list[SubscriptionFeeRow]:
    del product_elements  # reserved for future fund-code lookup
    table_rates = _parse_share_fee_table(document)
    letters = _letters_from_share_classes(share_classes) or sorted(table_rates.keys())
    if not letters and fund_name:
        letters = ["A"]

    rows: list[SubscriptionFeeRow] = []
    code_by_letter: dict[str, str | None] = {}
    for sc in share_classes:
        letter = _share_letter_from_row(sc)
        if letter:
            code_by_letter[letter] = sc.分级份额代码 or sc.基金代码

    for letter in letters:
        rates = table_rates.get(letter, {})
        display_name = format_subscription_fund_name(fund_name, letter)
        fund_code = code_by_letter.get(letter)
        for fee_type in ("认购费", "申购费"):
            rate = rates.get(fee_type)
            if rate is None:
                rate = "0"
            rows.append(
                SubscriptionFeeRow(
                    基金名称=display_name,
                    基金代码=fund_code,
                    申赎费类型=fee_type,
                    费率=rate,
                    费率类型="百分比",
                )
            )
        table_redeem = rates.get("赎回费")
        if table_redeem is not None:
            rows.append(
                SubscriptionFeeRow(
                    基金名称=display_name,
                    基金代码=fund_code,
                    申赎费类型="赎回费",
                    费率=table_redeem,
                    费率类型="百分比",
                )
            )

    sub_text = windows.get("subscription", "") or ""
    if "短期赎回" not in sub_text:
        for block in document.get("blocks") or []:
            if block.get("type") == "paragraph":
                chunk = str(block.get("text") or "")
                if "短期赎回" in chunk:
                    sub_text += "\n" + chunk
    tiers = _extract_redeem_tiers(sub_text)
    if tiers and fund_name:
        parent_code: str | None = None
        for sc in share_classes:
            if sc.基金代码:
                parent_code = sc.基金代码
                break
        for tier in tiers:
            rows.append(
                SubscriptionFeeRow(
                    基金名称=fund_name,
                    基金代码=parent_code,
                    申赎费类型="赎回费",
                    费率类型="百分比",
                    **tier,
                )
            )

    return rows
