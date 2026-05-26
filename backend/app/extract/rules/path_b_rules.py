from __future__ import annotations

import re
from typing import Any

from backend.app.extract.path_b_assemble import build_path_b_document
from backend.app.extract.rules.product_rules import _RE_OPEN_SCHEDULE
from backend.app.extract.schemas import ExtractionWarning, FieldValue, PerformanceFeeTier

_SHARE_COL = re.compile(r"([A-D])\s*类(?:份额)?", re.IGNORECASE)
_RATE_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_RE_PERF_METHOD = re.compile(
    r"(高水位|超额收益|单个投资者|整体高水位|份额净值)[^。\n]{0,80}(计提|提取|业绩报酬)",
)
_RE_OPEN_BUSINESS = re.compile(
    r"(申购|赎回)[^。\n]{0,120}(开放日|申请日|确认)",
)
_RE_TEMP_OPEN = re.compile(r"临时开放[^。\n]{0,400}")


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


def _fv(value: str, *, snippet: str) -> FieldValue:
    return FieldValue(value=value, confidence="medium", source="rule", snippet=snippet)


def _paragraph_text(document: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in document.get("blocks") or []:
        if block.get("type") == "paragraph":
            parts.append(str(block.get("text") or ""))
    return "\n".join(parts)


def _parse_performance_tiers_from_table(document: dict[str, Any]) -> list[PerformanceFeeTier]:
    tiers: list[PerformanceFeeTier] = []
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
        for row in rows[1:]:
            if not row:
                continue
            label = str(row[0] or "").strip()
            if "业绩报酬" not in label:
                continue
            for col_idx, letter in col_letters.items():
                if col_idx >= len(row):
                    continue
                cell = str(row[col_idx] or "").strip()
                if not cell or cell in ("【0%】", "0%"):
                    continue
                ratio = None
                m = _RATE_PCT.search(cell)
                if m:
                    ratio = m.group(1)
                tiers.append(
                    PerformanceFeeTier(
                        share_class=letter,
                        description=cell,
                        ratio_pct=ratio,
                    )
                )
        if tiers:
            return tiers
    return tiers


def _performance_summary_from_fees(fees_text: str) -> FieldValue | None:
    if "业绩报酬" not in fees_text:
        return None
    idx = fees_text.find("业绩报酬")
    chunk = fees_text[idx : idx + 500].strip()
    if len(chunk) < 20:
        return None
    return _fv(chunk[:500], snippet=chunk[:500])


def _extract_open_day_fields(
    document: dict[str, Any],
    windows: dict[str, str],
    product_elements: dict[str, Any],
) -> dict[str, FieldValue | None]:
    fields: dict[str, FieldValue | None] = {}
    schedule_fv = product_elements.get("开放日规则")
    schedule_text = _field_text(schedule_fv)
    sub_text = windows.get("subscription", "") or ""
    full_text = _paragraph_text(document)

    if schedule_text:
        fields["fixed_schedule"] = (
            schedule_fv
            if isinstance(schedule_fv, FieldValue)
            else _fv(schedule_text, snippet=schedule_text)
        )
    else:
        m = _RE_OPEN_SCHEDULE.search(sub_text) or _RE_OPEN_SCHEDULE.search(full_text)
        if m:
            fields["fixed_schedule"] = _fv(m.group(0).strip(), snippet=m.group(0))

    m_bus = _RE_OPEN_BUSINESS.search(sub_text)
    if m_bus:
        fields["open_business"] = _fv(m_bus.group(0).strip(), snippet=m_bus.group(0))

    temp_text = sub_text + "\n" + full_text
    if "临时开放" not in temp_text:
        for block in document.get("blocks") or []:
            if block.get("type") == "paragraph":
                chunk = str(block.get("text") or "")
                if "临时开放" in chunk:
                    temp_text += "\n" + chunk
    m_temp = _RE_TEMP_OPEN.search(temp_text)
    if m_temp:
        fields["temporary_open"] = _fv(m_temp.group(0).strip(), snippet=m_temp.group(0))

    return fields


def extract_path_b_rules(
    document: dict[str, Any],
    windows: dict[str, str],
    *,
    fund_name: str | None,
    product_elements: dict[str, Any],
) -> tuple[dict[str, Any], list[ExtractionWarning]]:
    del fund_name
    warnings: list[ExtractionWarning] = []
    fees_text = windows.get("fees", "") or ""

    perf_fields: dict[str, FieldValue | None] = {}
    tiers = _parse_performance_tiers_from_table(document)
    if not tiers:
        summary = _performance_summary_from_fees(fees_text)
        if summary:
            perf_fields["summary"] = summary
        else:
            warnings.append(
                ExtractionWarning(
                    field="path_b.performance_fee",
                    code="path_b_incomplete",
                    message="未从合同解析到业绩报酬结构化内容",
                    suggestion="请人工查阅费用与税收章节",
                )
            )
    else:
        m_method = _RE_PERF_METHOD.search(fees_text)
        if m_method:
            perf_fields["extraction_method"] = _fv(
                m_method.group(0).strip()[:200],
                snippet=m_method.group(0).strip(),
            )
        if "超额" in fees_text or any("超额" in (t.description or "") for t in tiers):
            perf_fields["benchmark_type"] = _fv(
                "超额收益",
                snippet=next(
                    (
                        t.description
                        for t in tiers
                        if t.description and "超额" in t.description
                    ),
                    "超额收益",
                ),
            )

    open_fields = _extract_open_day_fields(document, windows, product_elements)
    if not _field_text(open_fields.get("fixed_schedule")):
        warnings.append(
            ExtractionWarning(
                field="path_b.open_day.fixed_schedule",
                code="path_b_incomplete",
                message="未解析到固定开放日规则",
            )
        )

    path_b = build_path_b_document(
        performance_fields=perf_fields,
        open_day_fields=open_fields,
        tiers=tiers,
    )
    return path_b, warnings
