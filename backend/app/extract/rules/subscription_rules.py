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
_RE_RANGE_BEFORE_LT = re.compile(r"\d+\s*日\s*[≤<=]")
_RE_PURCHASE_RATE = re.compile(r"申购费率为\s*(\d+(?:\.\d+)?)\s*%")
_RE_SUBSCRIBE_RATE = re.compile(r"认购费率为\s*(\d+(?:\.\d+)?)\s*%")
_RE_REDEEM_HOLD_LT = re.compile(
    r"持有期低于\s*(\d+)\s*天[^。]{0,200}?赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)
_RE_REDEEM_HOLD_RANGE = re.compile(
    r"持有期在\s*(\d+)\s*天及以上但低于\s*(\d+)\s*天[^。]{0,120}?赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)
_RE_REDEEM_HOLD_GTE = re.compile(
    r"持有期在\s*(\d+)\s*天及以上[^。]{0,100}?赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
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


def _tier_from_redeem_line(line: str) -> dict[str, str] | None:
    """Parse one numbered short-redemption bullet; avoid matching t<360 inside 180≤t<360."""
    text = line.strip()
    if "短期赎回" not in text and "t" not in text.lower():
        return None

    m = _REDEEM_GTE.search(text)
    if m:
        return {
            "计费基准": "区间（P≥B）",
            "区间开始": m.group(1),
            "时间区间单位": "天",
            "费率": "0",
        }

    m = _REDEEM_RANGE.search(text)
    if m:
        return {
            "计费基准": "区间（A≤P＜B）",
            "区间开始": m.group(1),
            "区间结束": m.group(2),
            "时间区间单位": "天",
            "费率": m.group(3),
        }

    if _RE_RANGE_BEFORE_LT.search(text):
        return None
    m = _REDEEM_LT.search(text)
    if m:
        return {
            "计费基准": "区间（P＜A）",
            "区间结束": m.group(1),
            "时间区间单位": "天",
            "费率": m.group(2),
        }
    return None


def _collect_short_redemption_lines(
    subscription_text: str, document: dict[str, Any]
) -> list[str]:
    lines: list[str] = []
    if subscription_text.strip():
        lines.extend(subscription_text.splitlines())
    for block in document.get("blocks") or []:
        if block.get("type") != "paragraph":
            continue
        chunk = str(block.get("text") or "").strip()
        if "短期赎回" in chunk:
            lines.extend(chunk.splitlines())
    return lines


def _extract_redeem_tiers(
    subscription_text: str, document: dict[str, Any]
) -> list[dict[str, str]]:
    lines = _collect_short_redemption_lines(subscription_text, document)
    if not any("短期赎回" in ln for ln in lines):
        return []
    tiers: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for line in lines:
        tier = _tier_from_redeem_line(line)
        if not tier:
            continue
        key = (
            tier.get("计费基准", ""),
            tier.get("区间开始", ""),
            tier.get("区间结束", ""),
            tier.get("费率", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        tiers.append(tier)
    return tiers


def _collect_fee_section_text(document: dict[str, Any], windows: dict[str, str]) -> str:
    """申购赎回费率章节：兼容叙述体（正仁）与份额表（福禄）。"""
    chunks: list[str] = []
    markers = (
        "申购和赎回的费率",
        "申购费率",
        "赎回费率",
        "申购费率为",
        "赎回费率为",
        "短期赎回",
    )
    for block in document.get("blocks") or []:
        if block.get("type") != "paragraph":
            continue
        text = str(block.get("text") or "").strip()
        if text and any(m in text for m in markers):
            chunks.append(text)
    sub = (windows.get("subscription") or "").strip()
    if sub:
        chunks.append(sub)
    return "\n".join(chunks)


def _infer_subscription_billing(text: str) -> str | None:
    if re.search(
        r"1\s*\+\s*申购费率|/\s*（\s*1\s*\+\s*申购费率|申购金额\s*/\s*（\s*1\s*\+",
        text,
    ):
        return "价外法"
    if "价内法" in text:
        return "价内法"
    if "价外法" in text:
        return "价外法"
    return None


def _holding_period_redeem_tiers(text: str) -> list[dict[str, str]]:
    tiers: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()

    def _add(tier: dict[str, str]) -> None:
        key = (
            tier.get("计费基准", ""),
            tier.get("区间开始", ""),
            tier.get("区间结束", ""),
            tier.get("费率", ""),
        )
        if key in seen:
            return
        seen.add(key)
        tiers.append(tier)

    for m in _RE_REDEEM_HOLD_LT.finditer(text):
        _add(
            {
                "计费基准": "区间（P＜A）",
                "区间结束": m.group(1),
                "时间区间单位": "天",
                "费率": m.group(2),
            }
        )
    for m in _RE_REDEEM_HOLD_RANGE.finditer(text):
        _add(
            {
                "计费基准": "区间（A≤P＜B）",
                "区间开始": m.group(1),
                "区间结束": m.group(2),
                "时间区间单位": "天",
                "费率": m.group(3),
            }
        )
    for m in _RE_REDEEM_HOLD_GTE.finditer(text):
        _add(
            {
                "计费基准": "区间（P≥B）",
                "区间开始": m.group(1),
                "时间区间单位": "天",
                "费率": m.group(2),
            }
        )
    return tiers


def _extract_narrative_subscription_fees(
    fund_name: str,
    fee_text: str,
    *,
    fund_code: str | None,
) -> list[SubscriptionFeeRow]:
    """无份额分类表时，从申购赎回章节叙述抽取（如正仁）。"""
    rows: list[SubscriptionFeeRow] = []
    snippet = fee_text[:800]
    billing = _infer_subscription_billing(fee_text)

    if m := _RE_SUBSCRIBE_RATE.search(fee_text):
        rows.append(
            SubscriptionFeeRow(
                基金名称=fund_name,
                基金代码=fund_code,
                申赎费类型="认购费",
                费率=m.group(1),
                费率类型="百分比",
                计费方式=billing,
                snippet=snippet,
            )
        )
    if m := _RE_PURCHASE_RATE.search(fee_text):
        rows.append(
            SubscriptionFeeRow(
                基金名称=fund_name,
                基金代码=fund_code,
                申赎费类型="申购费",
                费率=m.group(1),
                费率类型="百分比",
                计费方式=billing,
                snippet=snippet,
            )
        )

    fake_doc = {
        "blocks": [
            {"type": "paragraph", "text": line}
            for line in fee_text.splitlines()
            if line.strip()
        ]
    }
    for tier in _holding_period_redeem_tiers(fee_text):
        rows.append(
            SubscriptionFeeRow(
                基金名称=fund_name,
                基金代码=fund_code,
                申赎费类型="赎回费",
                费率类型="百分比",
                snippet=snippet,
                **tier,
            )
        )
    for tier in _extract_redeem_tiers(fee_text, fake_doc):
        rows.append(
            SubscriptionFeeRow(
                基金名称=fund_name,
                基金代码=fund_code,
                申赎费类型="赎回费",
                费率类型="百分比",
                snippet=snippet,
                **tier,
            )
        )
    return rows


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

    rows: list[SubscriptionFeeRow] = []
    code_by_letter: dict[str, str | None] = {}
    for sc in share_classes:
        letter = _share_letter_from_row(sc)
        if letter:
            code_by_letter[letter] = sc.分级份额代码 or sc.基金代码

    fee_section = _collect_fee_section_text(document, windows)

    if table_rates:
        for letter in letters:
            rates = table_rates.get(letter, {})
            display_name = format_subscription_fund_name(fund_name, letter)
            fund_code = code_by_letter.get(letter)
            snip = fee_section[:500] if fee_section else None
            for fee_type in ("认购费", "申购费"):
                rate = rates.get(fee_type)
                if rate is None:
                    continue
                rows.append(
                    SubscriptionFeeRow(
                        基金名称=display_name,
                        基金代码=fund_code,
                        申赎费类型=fee_type,
                        费率=rate,
                        费率类型="百分比",
                        snippet=snip,
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
                        snippet=snip,
                    )
                )
    elif fund_name and fee_section.strip():
        parent_code: str | None = None
        for sc in share_classes:
            if sc.基金代码:
                parent_code = sc.基金代码
                break
        rows.extend(
            _extract_narrative_subscription_fees(
                fund_name, fee_section, fund_code=parent_code
            )
        )

    sub_text = windows.get("subscription", "") or ""
    tiers = _extract_redeem_tiers(sub_text, document)
    has_tier_redeem = any(
        r.申赎费类型 == "赎回费" and r.计费基准 for r in rows
    )
    if tiers and fund_name and (table_rates or not has_tier_redeem):
        parent_code: str | None = None
        for sc in share_classes:
            if sc.基金代码:
                parent_code = sc.基金代码
                break
        tier_snip = fee_section[:800] if fee_section else sub_text[:800]
        for tier in tiers:
            rows.append(
                SubscriptionFeeRow(
                    基金名称=fund_name,
                    基金代码=parent_code,
                    申赎费类型="赎回费",
                    费率类型="百分比",
                    snippet=tier_snip,
                    **tier,
                )
            )

    return rows
