from __future__ import annotations

import re

from backend.app.extract.schemas import FeeRateRow

_FEE_TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("管理费", re.compile(r"管理费")),
    ("托管费", re.compile(r"托管费")),
    ("投资顾问费", re.compile(r"投资顾问费|顾问费")),
    ("销售服务费", re.compile(r"销售服务费")),
]

_RATE_PCT = re.compile(
    r"(\d+(?:\.\d+)?)\s*[%％]\s*(?:/年|每年|年)?", re.IGNORECASE
)
_FREQ = re.compile(r"(按年|按月|按季|每日|每年|每月)")


def extract_fee_rates(fees_text: str, fund_name: str | None) -> list[FeeRateRow]:
    rows: list[FeeRateRow] = []
    seen_types: set[str] = set()
    name = fund_name or ""

    lines = fees_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        for fee_type, pattern in _FEE_TYPE_PATTERNS:
            if not pattern.search(line):
                continue
            if fee_type in seen_types:
                continue
            rate_m = _RATE_PCT.search(line)
            freq_m = _FREQ.search(line)
            if not rate_m and fee_type not in line:
                continue
            row = FeeRateRow(
                基金名称=name or None,
                运营费类型=fee_type,
                计费频率=freq_m.group(1) if freq_m else "按年",
                计费基准=None,
            )
            if rate_m:
                row.rate_annual_pct = rate_m.group(1)
            rows.append(row)
            seen_types.add(fee_type)

    # Table-style: tab-separated rows in window
    for line in lines:
        if "\t" not in line:
            continue
        cells = [c.strip() for c in line.split("\t")]
        joined = " ".join(cells)
        for fee_type, pattern in _FEE_TYPE_PATTERNS:
            if fee_type in seen_types or not pattern.search(joined):
                continue
            rate_m = _RATE_PCT.search(joined)
            if rate_m:
                rows.append(
                    FeeRateRow(
                        基金名称=name or None,
                        运营费类型=fee_type,
                        计费频率="按年",
                        rate_annual_pct=rate_m.group(1),
                    )
                )
                seen_types.add(fee_type)

    # Fallback: search whole text for type + rate pairs
    if len(rows) < 2:
        for fee_type, pattern in _FEE_TYPE_PATTERNS[:2]:
            if fee_type in seen_types:
                continue
            for m in re.finditer(
                rf"{pattern.pattern}[^。\n]{{0,120}}", fees_text, re.IGNORECASE
            ):
                chunk = m.group(0)
                rate_m = _RATE_PCT.search(chunk)
                if rate_m:
                    rows.append(
                        FeeRateRow(
                            基金名称=name or None,
                            运营费类型=fee_type,
                            计费频率="按年",
                            rate_annual_pct=rate_m.group(1),
                        )
                    )
                    seen_types.add(fee_type)
                    break

    return rows
