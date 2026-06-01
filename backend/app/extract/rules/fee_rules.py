from __future__ import annotations

import re
from typing import Any

from backend.app.extract.field_catalog import SKIP_FEE_FIELDS
from backend.app.extract.rules.subscription_rules import format_subscription_fund_name
from backend.app.extract.schemas import FeeRateRow

_SHARE_COL = re.compile(r"^([A-D])\s*类", re.IGNORECASE)
_SHARE_TABLE_FEE_ROWS: dict[str, str] = {
    "年管理费率": "管理费",
    "销售服务费率": "销售服务费",
}

_FEE_TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("管理费", re.compile(r"管理费")),
    ("托管费", re.compile(r"托管费")),
    ("投资顾问费", re.compile(r"投资顾问费|顾问费")),
    ("销售服务费", re.compile(r"销售服务费")),
    ("基金服务费", re.compile(r"基金服务费|运营服务费|运营外包服务费")),
]

_RATE_PCT = re.compile(
    r"(\d+(?:\.\d+)?)\s*[%％]\s*(?:/年|每年|年)?", re.IGNORECASE
)
_RE_TYPED_RATE = re.compile(
    r"(年托管费率|基金服务费|外包服务费|年管理费率|销售服务费率)"
    r"[^。\n]{0,30}?(\d+(?:\.\d+)?)\s*[%％]",
    re.IGNORECASE,
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
_FEE_SOURCE_MARKERS = (
    "基金管理费",
    "基金的托管费",
    "托管费",
    "运营服务费",
    "基金服务费",
    "不收取管理费",
    "年费率",
    "外包服务费",
)
_FEE_TYPE_ORDER = ("管理费", "托管费", "基金服务费", "销售服务费", "投资顾问费")


def gather_fee_source_text(
    fees_text: str,
    document: dict[str, Any] | None = None,
) -> str:
    """费用章节全文：窗口 + 正文中含费率说明的段落（避免窗口分类遗漏）。"""
    parts: list[str] = []
    if fees_text.strip():
        parts.append(fees_text.strip())
    if document:
        for block in document.get("blocks") or []:
            if block.get("type") not in ("paragraph", "table"):
                continue
            if block.get("type") == "table":
                rows = block.get("rows") or []
                text = "\n".join("\t".join(str(c) for c in row) for row in rows)
            else:
                text = str(block.get("text") or "")
            if text.strip() and any(m in text for m in _FEE_SOURCE_MARKERS):
                parts.append(text.strip())
    return "\n\n".join(parts)


def _rates_from_narrative_fees(text: str) -> dict[str, str]:
    """按合同费用小节叙述抽取（正仁：管理费/托管费/运营服务费）。"""
    rates: dict[str, str] = {}
    if not text.strip():
        return rates
    if re.search(r"不收取管理费|管理费.*不收取|本基金不收取管理费", text):
        rates["管理费"] = "0"
    m = re.search(
        r"(?:基金)?托管费[^。\n]{0,160}?年费率\s*为?\s*(\d+(?:\.\d+)?)\s*[%％]",
        text,
    )
    if m:
        rates["托管费"] = m.group(1)
    for pattern, key in (
        (
            r"运营服务费[^。\n]{0,160}?年费率\s*为?\s*(\d+(?:\.\d+)?)\s*[%％]",
            "基金服务费",
        ),
        (
            r"基金服务费[^。\n]{0,160}?年费率\s*为?\s*(\d+(?:\.\d+)?)\s*[%％]",
            "基金服务费",
        ),
        (
            r"外包服务费[^。\n]{0,5000}?年费率\s*为?\s*(\d+(?:\.\d+)?)\s*[%％]",
            "基金服务费",
        ),
    ):
        m = re.search(pattern, text)
        if m:
            rates[key] = m.group(1)
    return rates


def _rows_from_explicit_rates(
    fund_name: str | None,
    rates: dict[str, str],
) -> list[FeeRateRow]:
    rows: list[FeeRateRow] = []
    for fee_type in _FEE_TYPE_ORDER:
        if fee_type not in rates:
            continue
        row = FeeRateRow(
            基金名称=fund_name or None,
            运营费类型=fee_type,
            计费频率="按年",
        )
        _apply_rate(row, rates[fee_type])
        rows.append(row)
    return rows


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
        if "起始" in label and "计费起始日期" not in SKIP_FEE_FIELDS:
            out["计费起始日期"] = date_str
        elif "截止" in label and "计费截止日期" not in SKIP_FEE_FIELDS:
            out["计费截止日期"] = date_str
        elif "费率生效日期" not in SKIP_FEE_FIELDS:
            out["费率生效日期"] = date_str
    for m in _CAP_FLOOR.finditer(line):
        out[m.group(1)] = m.group(2)
    return out


def _apply_rate(row: FeeRateRow, rate: str | None) -> None:
    if rate:
        row.rate_annual_pct = rate


def _row_from_line(
    line: str,
    fee_type: str,
    fund_name: str,
    *,
    seen: set[str],
    default_rate: str | None = None,
) -> FeeRateRow | None:
    if fee_type in seen:
        return None
    pattern = next(p for t, p in _FEE_TYPE_PATTERNS if t == fee_type)
    if not pattern.search(line):
        return None
    rate_m = _RATE_PCT.search(line)
    if not rate_m and fee_type not in line and not default_rate:
        return None
    extra = _parse_line_fields(line)
    row = FeeRateRow(
        基金名称=fund_name or None,
        运营费类型=fee_type,
        计费频率=extra.get("计费频率", "按年"),
        计费基准=extra.get("计费基准"),
    )
    if rate_m:
        _apply_rate(row, rate_m.group(1))
    elif default_rate:
        _apply_rate(row, default_rate)
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


def _rates_from_fee_chapter(fees_text: str) -> dict[str, str]:
    rates: dict[str, str] = {}
    for m in _RE_TYPED_RATE.finditer(fees_text):
        label, pct = m.group(1), m.group(2)
        if "托管" in label:
            rates["托管费"] = pct
        elif "基金服务" in label or "运营服务" in label or "外包服务" in label:
            rates["基金服务费"] = pct
        elif "管理" in label:
            rates["管理费"] = pct
        elif "销售服务" in label:
            rates["销售服务费"] = pct
    m = re.search(r"年托管费率为\s*(\d+(?:\.\d+)?)\s*[%％]", fees_text)
    if m:
        rates["托管费"] = m.group(1)
    m = re.search(
        r"基金服务费[\s\S]{0,5000}?年费率为\s*(\d+(?:\.\d+)?)\s*[%％]", fees_text
    )
    if m:
        rates["基金服务费"] = m.group(1)
    m = re.search(
        r"外包服务费[\s\S]{0,400}?年费率为\s*(\d+(?:\.\d+)?)\s*[%％]", fees_text
    )
    if m:
        rates["基金服务费"] = m.group(1)
    m = re.search(r"年费率为\s*(\d+(?:\.\d+)?)\s*[%％]", fees_text)
    if m and "基金服务费" not in rates:
        # only if line is under 基金服务费 section
        idx = fees_text.find("3、基金服务费")
        if idx >= 0 and m.start() > idx:
            rates["基金服务费"] = m.group(1)
    return rates


def _rates_from_document_text(document: dict[str, Any]) -> dict[str, str]:
    """Fallback when fee chapter window truncates 外包服务费 / 基金服务费 blocks."""
    parts: list[str] = []
    for block in document.get("blocks") or []:
        if block.get("type") == "paragraph":
            parts.append(str(block.get("text") or ""))
        elif block.get("type") == "table":
            rows = block.get("rows") or []
            parts.append(
                "\n".join("\t".join(str(c) for c in row) for row in rows)
            )
    text = "\n".join(parts)
    rates: dict[str, str] = {}
    m = re.search(
        r"外包服务费[\s\S]{0,5000}?年费率为\s*(\d+(?:\.\d+)?)\s*[%％]", text
    )
    if m:
        rates["基金服务费"] = m.group(1)
    m = re.search(
        r"3、基金服务费[\s\S]{0,5000}?年费率为\s*(\d+(?:\.\d+)?)\s*[%％]", text
    )
    if m:
        rates["基金服务费"] = m.group(1)
    return rates


def _fee_rows_from_share_classification_table(
    document: dict[str, Any],
    fund_name: str | None,
) -> list[FeeRateRow]:
    """One operating-fee row per share class when 份额分类表 lists rates by A–D."""
    rows: list[FeeRateRow] = []
    name = fund_name or ""
    for block in document.get("blocks") or []:
        if block.get("type") != "table":
            continue
        table_rows = block.get("rows") or []
        if len(table_rows) < 2:
            continue
        header = [str(c or "").strip() for c in table_rows[0]]
        col_letters: dict[int, str] = {}
        for idx, cell in enumerate(header):
            if idx == 0:
                continue
            m = _SHARE_COL.search(cell)
            if m:
                col_letters[idx] = m.group(1).upper()
        if len(col_letters) < 2:
            continue
        parsed_any = False
        table_block_id = str(block.get("id") or "") or None
        for tr in table_rows[1:]:
            if not tr:
                continue
            label = str(tr[0] or "").strip()
            fee_type: str | None = None
            for key, ft in _SHARE_TABLE_FEE_ROWS.items():
                if key in label:
                    fee_type = ft
                    break
            if not fee_type:
                continue
            for col_idx, letter in col_letters.items():
                if col_idx >= len(tr):
                    continue
                pct = _RATE_PCT.search(str(tr[col_idx] or ""))
                if not pct:
                    continue
                row = FeeRateRow(
                    基金名称=format_subscription_fund_name(name, letter) or name,
                    运营费类型=fee_type,
                    计费频率="按年",
                    block_id=table_block_id,
                )
                _apply_rate(row, pct.group(1))
                rows.append(row)
                parsed_any = True
        if parsed_any:
            break
    return rows


def _rates_from_share_table(document: dict[str, Any]) -> dict[str, str]:
    rates: dict[str, str] = {}
    for block in document.get("blocks") or []:
        if block.get("type") != "table":
            continue
        rows = block.get("rows") or []
        if len(rows) < 3:
            continue
        flat = "\n".join("\t".join(str(c) for c in row) for row in rows)
        if "年管理费率" not in flat and "申购费率" not in flat:
            continue
        for row in rows:
            cells = [str(c).strip() for c in row]
            if not cells:
                continue
            label = cells[0].replace("【", "").replace("】", "")
            if "年管理费率" in label:
                for cell in cells[1:]:
                    pct = re.search(r"(\d+(?:\.\d+)?)\s*[%％]", cell)
                    if pct:
                        rates["管理费"] = pct.group(1)
                        break
            if "销售服务费率" in label:
                for cell in cells[1:]:
                    pct = re.search(r"(\d+(?:\.\d+)?)\s*[%％]", cell)
                    if pct:
                        rates["销售服务费"] = pct.group(1)
                        break
    return rates


def extract_fee_rates(
    fees_text: str,
    fund_name: str | None,
    document: dict[str, Any] | None = None,
) -> list[FeeRateRow]:
    rows: list[FeeRateRow] = []
    seen_types: set[str] = set()
    name = fund_name or ""

    per_class_rows = (
        _fee_rows_from_share_classification_table(document, fund_name)
        if document
        else []
    )
    per_class_types = {r.运营费类型 for r in per_class_rows if r.运营费类型}

    source = gather_fee_source_text(fees_text, document)
    narrative_rates = _rates_from_narrative_fees(source)
    chapter_rates = _rates_from_fee_chapter(source)
    if document:
        chapter_rates = {
            **_rates_from_document_text(document),
            **_rates_from_share_table(document),
            **chapter_rates,
            **narrative_rates,
        }
    else:
        chapter_rates = {**chapter_rates, **narrative_rates}

    if narrative_rates and not per_class_rows:
        explicit_rows = _rows_from_explicit_rates(name, chapter_rates)
        if explicit_rows:
            return explicit_rows

    lines = source.splitlines()
    if "外包服务费" in fees_text and "基金服务费" not in seen_types:
        m = re.search(
            r"外包服务费[\s\S]{0,5000}?年费率为\s*(\d+(?:\.\d+)?)\s*[%％]", fees_text
        )
        if m:
            chapter_rates.setdefault("基金服务费", m.group(1))

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "外包服务费" in line and "基金服务费" not in seen_types:
            pct = re.search(r"(\d+(?:\.\d+)?)\s*[%％]", line)
            row = FeeRateRow(
                基金名称=name or None,
                运营费类型="基金服务费",
                计费频率="按年",
            )
            if pct:
                _apply_rate(row, pct.group(1))
            elif chapter_rates.get("基金服务费"):
                _apply_rate(row, chapter_rates["基金服务费"])
            if row.rate_annual_pct:
                rows.append(row)
                seen_types.add("基金服务费")
        for fee_type, _pattern in _FEE_TYPE_PATTERNS:
            if fee_type in per_class_types:
                continue
            row = _row_from_line(
                line,
                fee_type,
                name,
                seen=seen_types,
                default_rate=chapter_rates.get(fee_type),
            )
            if row:
                rows.append(row)
                seen_types.add(fee_type)

    for line in lines:
        if "\t" not in line:
            continue
        cells = [c.strip() for c in line.split("\t")]
        joined = " ".join(cells)
        for fee_type, pattern in _FEE_TYPE_PATTERNS:
            if fee_type in seen_types or fee_type in per_class_types:
                continue
            if not pattern.search(joined):
                continue
            row = _row_from_line(
                joined,
                fee_type,
                name,
                seen=seen_types,
                default_rate=chapter_rates.get(fee_type),
            )
            if row:
                rows.append(row)
                seen_types.add(fee_type)

    if len(rows) < 2:
        for fee_type, pattern in _FEE_TYPE_PATTERNS[:2]:
            if fee_type in seen_types or fee_type in per_class_types:
                continue
            for m in re.finditer(
                rf"{pattern.pattern}[^。\n]{{0,160}}", fees_text, re.IGNORECASE
            ):
                chunk = m.group(0)
                row = _row_from_line(
                    chunk,
                    fee_type,
                    name,
                    seen=seen_types,
                    default_rate=chapter_rates.get(fee_type),
                )
                if row:
                    rows.append(row)
                    seen_types.add(fee_type)
                    break

    for fee_type, rate in chapter_rates.items():
        if fee_type in per_class_types:
            continue
        if fee_type in seen_types:
            for row in rows:
                if row.运营费类型 == fee_type and not row.rate_annual_pct:
                    _apply_rate(row, rate)
            continue
        row = FeeRateRow(
            基金名称=name or None,
            运营费类型=fee_type,
            计费频率="按年",
        )
        _apply_rate(row, rate)
        rows.append(row)
        seen_types.add(fee_type)

    return per_class_rows + rows


def enrich_fee_rates_from_fees_chapter(
    fee_rates: list[FeeRateRow],
    fees_text: str,
) -> list[FeeRateRow]:
    """Align billing frequency/basis with 费用章节 (daily accrual + prior-day NAV)."""
    if not fees_text.strip():
        return fee_rates
    daily_accrual = "每日计提" in fees_text or "每日应计提" in fees_text
    prev_nav = bool(
        re.search(r"前一自然日.{0,24}资产净值", fees_text)
        or re.search(r"前一自然日的?基金资产净值", fees_text)
    )
    use_actual_days = "当年天数" in fees_text or "÷N" in fees_text
    freq = "按日" if daily_accrual else None
    basis = "前一日资产净值" if prev_nav else None
    vague_basis = frozenset(
        {"基金资产净值", "资产净值", "前一自然日基金资产净值", None, ""}
    )
    for row in fee_rates:
        # Zero-rate means "not charged" — don't apply billing attributes from
        # other fee subsections (e.g. 托管费 daily-accrual text should not
        # bleed onto 管理费=0 rows).
        if row.rate_annual_pct == "0":
            continue
        if freq and (not row.计费频率 or row.计费频率 in ("按年", "每年")):
            row.计费频率 = freq
        if basis and (not row.计费基准 or row.计费基准 in vague_basis):
            row.计费基准 = basis
        if daily_accrual and not row.费用计算方式:
            row.费用计算方式 = "系统计算"
        if use_actual_days and not row.年计提天数:
            row.年计提天数 = "实际天数"
    return fee_rates


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
        if "基金代码" not in SKIP_FEE_FIELDS and not row.基金代码 and code:
            row.基金代码 = code
    return fee_rates
