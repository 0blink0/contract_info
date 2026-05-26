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
_FREQ = re.compile(r"(按年|按月|按季|每日|每年|每月|每季)")
_BASE = re.compile(
    r"(按初始委托本金|前一日资产净值|固定金额|资产净值|初始委托本金)"
)
_FIXED_AMT = re.compile(r"固定金额[：:\s]*(\d+(?:\.\d+)?)")
_PAY_FREQ = re.compile(r"支付[^。\n]{0,8}(按年|按月|按季|每年|每月)")
_DAYS_YEAR = re.compile(r"(365|360)\s*天")
_CALC_METHOD = re.compile(r"(系统计算|手工录入)")
_FEE_DATE = re.compile(
    r"(计费起始|计费截止|费率生效)[日期：:\s]*(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})"
)
_CAP_FLOOR = re.compile(r"(保底|封顶)[：:\s]*(\d+(?:\.\d+)?)")


def _parse_line_fields(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    freq_m = _FREQ.search(line)
    if freq_m:
        out["计费频率"] = freq_m.group(1)
    base_m = _BASE.search(line)
    if base_m:
        out["计费基准"] = base_m.group(1)
    fixed_m = _FIXED_AMT.search(line)
    if fixed_m:
        out["固定金额"] = fixed_m.group(1)
    pay_m = _PAY_FREQ.search(line)
    if pay_m:
        out["支付频率"] = pay_m.group(1)
    days_m = _DAYS_YEAR.search(line)
    if days_m:
        out["年计提天数"] = days_m.group(1)
    calc_m = _CALC_METHOD.search(line)
    if calc_m:
        out["费用计算方式"] = calc_m.group(1)
    for m in _FEE_DATE.finditer(line):
        label = m.group(1)
        date_str = f"{m.group(2)}/{int(m.group(3))}/{int(m.group(4))}"
        if "起始" in label:
            out["计费起始日期"] = date_str
        elif "截止" in label:
            out["计费截止日期"] = date_str
        else:
            out["费率生效日期"] = date_str
    for m in _CAP_FLOOR.finditer(line):
        out[m.group(1)] = m.group(2)
    return out


def _row_from_line(
    line: str,
    fee_type: str,
    fund_name: str,
    *,
    seen: set[str],
) -> FeeRateRow | None:
    if fee_type in seen:
        return None
    pattern = next(p for t, p in _FEE_TYPE_PATTERNS if t == fee_type)
    if not pattern.search(line):
        return None
    rate_m = _RATE_PCT.search(line)
    if not rate_m and fee_type not in line:
        return None
    extra = _parse_line_fields(line)
    row = FeeRateRow(
        基金名称=fund_name or None,
        运营费类型=fee_type,
        计费频率=extra.get("计费频率", "按年"),
        计费基准=extra.get("计费基准"),
    )
    if rate_m:
        row.rate_annual_pct = rate_m.group(1)
    for key in (
        "固定金额",
        "年计提天数",
        "费用计算方式",
        "支付频率",
        "计费起始日期",
        "计费截止日期",
        "费率生效日期",
        "保底",
        "封顶",
    ):
        if key in extra:
            setattr(row, key, extra[key])
    return row


def extract_fee_rates(fees_text: str, fund_name: str | None) -> list[FeeRateRow]:
    rows: list[FeeRateRow] = []
    seen_types: set[str] = set()
    name = fund_name or ""

    lines = fees_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        for fee_type, _pattern in _FEE_TYPE_PATTERNS:
            row = _row_from_line(line, fee_type, name, seen=seen_types)
            if row:
                rows.append(row)
                seen_types.add(fee_type)

    for line in lines:
        if "\t" not in line:
            continue
        cells = [c.strip() for c in line.split("\t")]
        joined = " ".join(cells)
        for fee_type, pattern in _FEE_TYPE_PATTERNS:
            if fee_type in seen_types or not pattern.search(joined):
                continue
            row = _row_from_line(joined, fee_type, name, seen=seen_types)
            if row:
                rows.append(row)
                seen_types.add(fee_type)

    if len(rows) < 2:
        for fee_type, pattern in _FEE_TYPE_PATTERNS[:2]:
            if fee_type in seen_types:
                continue
            for m in re.finditer(
                rf"{pattern.pattern}[^。\n]{{0,160}}", fees_text, re.IGNORECASE
            ):
                chunk = m.group(0)
                row = _row_from_line(chunk, fee_type, name, seen=seen_types)
                if row:
                    rows.append(row)
                    seen_types.add(fee_type)
                    break

    return rows


def enrich_fee_rates_from_product(
    fee_rates: list[FeeRateRow],
    product_elements: dict,
) -> list[FeeRateRow]:
    """Copy product-level fee hints onto fee rows when missing."""
    base_fv = product_elements.get("计费基准")
    freq_fv = product_elements.get("计费频率")
    code_fv = product_elements.get("基金代码")
    base = (
        str(base_fv.value).strip()
        if base_fv and getattr(base_fv, "value", None)
        else None
    )
    freq = (
        str(freq_fv.value).strip()
        if freq_fv and getattr(freq_fv, "value", None)
        else None
    )
    code = (
        str(code_fv.value).strip()
        if code_fv and getattr(code_fv, "value", None)
        else None
    )
    for row in fee_rates:
        if not row.计费基准 and base:
            row.计费基准 = base
        if not row.计费频率 and freq:
            row.计费频率 = freq
        if not row.基金代码 and code:
            row.基金代码 = code
    return fee_rates
