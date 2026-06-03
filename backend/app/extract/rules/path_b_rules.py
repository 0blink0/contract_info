from __future__ import annotations

import re
from typing import Any

from backend.app.extract.path_b_assemble import build_path_b_document
from backend.app.extract.rules.product_rules import _RE_OPEN_SCHEDULE
from backend.app.extract.schemas import ExtractionWarning, FieldValue, PerformanceFeeTier

_SHARE_COL = re.compile(r"([A-D])\s*类(?:份额)?", re.IGNORECASE)
_RATE_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")

# Matches "业绩报酬" appearing as a SECTION HEADING.
# Branch 1: mandatory numeric/Chinese prefix (e.g. "5、业绩报酬", "（五）基金管理人的业绩报酬").
#   No negative lookahead — allows full heading titles like "5、业绩报酬提取条款".
# Branch 2: exact full phrase "基金管理人的业绩报酬" at line start (no prefix required).
_PERF_FEE_HEADING_PAT = re.compile(
    r"(?:^|\n)[ \t]*"
    r"(?:"
    r"(?:\d+[、．.]|[一二三四五六七八九十]+[、．.]|（[一二三四五六七八九十]+）)"
    r"[ \t]*(?:(?:基金|本基金)(?:管理人的?|的)?)?业绩报酬"
    r"|基金管理人的业绩报酬"
    r")",
    re.MULTILINE,
)

_CHINESE_NUM_SEQ = "一二三四五六七八九十"

# Specific performance-fee content markers for fallback (more reliable than bare "业绩报酬").
_PERF_FEE_CONTENT_MARKERS = (
    "计提业绩报酬",
    "业绩报酬的计提",
    "业绩报酬计提比例",
    "业绩报酬提取",
    "业绩报酬比例",
)

# 提取方式
_RE_PERF_METHOD_SPECIFIC = re.compile(
    r"(基金整体资产高水位|基金整体高水位|整体高水位"
    r"|单个投资者高水位|单笔高水位"
    r"|份额净值法"
    r"|超额收益法)",
    re.IGNORECASE,
)
_RE_PERF_METHOD_GENERIC = re.compile(
    r"(高水位|超额收益|单个投资者|整体高水位|份额净值)[^。\n]{0,80}(计提|提取|业绩报酬)",
)

# 基准类型：含外部指数比较 → 超额收益
_RE_BENCHMARK_INDEX = re.compile(
    r"(中证\d{3}|沪深\d{3}|上证.*?指数|深证.*?指数|[A-Z]{2,}[0-9]{3}|CSI\s*\d+|万得.*?指数)"
    r"|基金整体.*?高于.*?业绩基准"
    r"|超额收益",
    re.IGNORECASE | re.DOTALL,
)

# 开放日/固定频率
_RE_OPEN_BUSINESS = re.compile(
    r"(申购|赎回)[^。\n]{0,120}(开放日|申请日|确认)",
)
_RE_TEMP_OPEN = re.compile(r"临时开放[^。\n]{0,400}")

_TIMING_CHECKS: list[tuple[str, re.Pattern[str]]] = [
    # "固定时点" only when the contract explicitly states performance fee is
    # collected at a recurring fixed interval — not merely because a fixed
    # open-day schedule exists elsewhere.
    ("固定时点", re.compile(
        r"(?:按|于|在).*?(?:开放日|估值日|计提日).*?(?:计提|提取|收取)"
        r"|(?:每年|每季|每半年|每月).*?(?:计提|提取)业绩报酬"
        r"|固定.*?开放.*?计提"
    )),
    ("分红", re.compile(r"分红|收益分配")),
    ("赎回", re.compile(r"赎回")),
    ("基金清算", re.compile(r"清算|合同终止|基金终止|解散")),
]

# 门槛净值
_RE_HURDLE_TIERED = re.compile(
    r"分段|分档|分级.*?门槛|超额.*?阶梯|阶梯.*?收费|"
    r"第[一二三四五]档|(?:\d+\s*%.*?){2,}.*?(区间|档位)"
    r"|(?:低于|高于)[^。\n]{0,20}\d+[^。\n]{0,20}(?:低于|高于)",
)
_RE_HURDLE_INITIAL_NAV = re.compile(
    r"初始净值|初始份额净值|成立日.*?净值|首次.*?净值|发行价|面值.*?1(?:\.0+)?元"
    r"|水位线.*?1(?:\.0+)?",
)
_RE_NO_HURDLE = re.compile(r"无门槛|不设门槛|无需.*?超过.*?净值|无绩效.*?门槛")

# 管理人放弃提取
_RE_MANAGER_WAIVER = re.compile(
    r"管理人.*?(?:放弃|自愿放弃|不计提|豁免).*?业绩报酬"
    r"|(?:放弃|不计提|豁免).*?业绩报酬.*?管理人"
    r"|基金.*?亏损.*?不.*?计提业绩报酬"
    r"|管理人.*?不.*?计提",
    re.DOTALL,
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


def _fv(value: str, *, snippet: str, confidence: str = "medium") -> FieldValue:
    return FieldValue(
        value=value,
        confidence=confidence,  # type: ignore[arg-type]
        source="rule",
        snippet=snippet,
    )


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


def _extract_extraction_method(fees_text: str) -> FieldValue | None:
    """识别业绩报酬提取方式（优先具体名称，兜底泛化）。"""
    m = _RE_PERF_METHOD_SPECIFIC.search(fees_text)
    if m:
        raw = m.group(0).strip()
        # 规范化到 CRM 枚举值
        if "基金整体" in raw or "整体高水位" in raw:
            value = "基金整体资产高水位法"
        elif "单个投资者" in raw or "单笔高水位" in raw:
            value = "单个投资者高水位法"
        elif "份额净值" in raw:
            value = "份额净值法"
        elif "超额收益" in raw:
            value = "超额收益法"
        else:
            value = raw
        # 取上下文摘录
        pos = fees_text.find(m.group(0))
        snip = fees_text[max(0, pos - 30): pos + 150].strip()
        return _fv(value, snippet=snip, confidence="high")
    m = _RE_PERF_METHOD_GENERIC.search(fees_text)
    if m:
        return _fv(m.group(0).strip()[:200], snippet=m.group(0).strip())
    return None


def _extract_benchmark_type(fees_text: str, tiers: list[PerformanceFeeTier]) -> FieldValue | None:
    """
    判断业绩基准类型：
    - 净值型：高水位法，不与外部指数比较
    - 超额收益：与外部指数/基准比较
    """
    tier_text = " ".join(t.description or "" for t in tiers)
    all_text = fees_text + " " + tier_text

    if _RE_BENCHMARK_INDEX.search(all_text):
        m = _RE_BENCHMARK_INDEX.search(all_text)
        return _fv("超额收益", snippet=m.group(0) if m else "超额收益", confidence="medium")

    # 高水位法 → 净值型
    if re.search(r"高水位", all_text):
        m = re.search(r".{0,30}高水位.{0,60}", all_text)
        return _fv("净值型", snippet=m.group(0).strip() if m else "高水位法→净值型", confidence="medium")

    return None


def _extract_hurdle_nav(fees_text: str, tiers: list[PerformanceFeeTier]) -> FieldValue | None:
    """识别门槛净值类型：无门槛 / 初始水位线 / 分段设置。"""
    tier_text = " ".join(t.description or "" for t in tiers)
    all_text = fees_text + " " + tier_text

    # 分段设置优先（有多档或阶梯描述）
    m = _RE_HURDLE_TIERED.search(all_text)
    if m:
        return _fv("分段设置", snippet=m.group(0)[:200], confidence="medium")

    # 正收益基础（来自档位说明）
    for t in tiers:
        desc = t.description or ""
        if "正收益" in desc:
            return _fv(
                "初始水位线（正收益基础）",
                snippet=desc[:200],
                confidence="medium",
            )

    # 明确无门槛
    m = _RE_NO_HURDLE.search(all_text)
    if m:
        return _fv("无门槛", snippet=m.group(0), confidence="high")

    # 初始净值 / 面值
    m = _RE_HURDLE_INITIAL_NAV.search(all_text)
    if m:
        return _fv("初始水位线", snippet=m.group(0), confidence="medium")

    return None


def _extract_manager_waiver(fees_text: str) -> FieldValue | None:
    """管理人是否有放弃提取业绩报酬的条款。"""
    m = _RE_MANAGER_WAIVER.search(fees_text)
    if m:
        pos = fees_text.find(m.group(0))
        snip = fees_text[max(0, pos - 20): pos + 150].strip()
        return _fv("是", snippet=snip, confidence="medium")
    return None


def _extract_extraction_timing(
    fees_text: str, *, has_fixed_schedule: bool  # noqa: ARG001
) -> FieldValue | None:
    hits: list[str] = []
    snips: list[str] = []
    for label, pat in _TIMING_CHECKS:
        m = pat.search(fees_text)
        if m and label not in hits:
            hits.append(label)
            snips.append(m.group(0))
    if not hits:
        return None
    return _fv("、".join(hits), snippet="；".join(snips)[:400] or "、".join(hits))


def _performance_summary_from_fees(fees_text: str) -> FieldValue | None:
    if "业绩报酬" not in fees_text:
        return None
    idx = fees_text.find("业绩报酬")
    chunk = fees_text[idx: idx + 500].strip()
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
    m_temp = _RE_TEMP_OPEN.search(temp_text)
    if m_temp:
        fields["temporary_open"] = _fv(m_temp.group(0).strip(), snippet=m_temp.group(0))

    return fields


def _perf_fee_next_sibling_pos(heading_match: re.Match[str], tail: str) -> int:
    """Return the position within *tail* where the next sibling section starts, or len(tail)."""
    heading_str = heading_match.group(0)

    # Digit prefix: "5、" → next sibling starts at 6、, 7、, …
    digit_m = re.search(r"(\d+)[、．.]", heading_str)
    if digit_m:
        n = int(digit_m.group(1))
        # Build alternation for numbers n+1 … n+20 to avoid matching sub-items
        alternatives = "|".join(str(n + i) for i in range(1, 21))
        sibling_pat = re.compile(r"\n[ \t]*(?:" + alternatives + r")[、．.]", re.MULTILINE)
        sm = sibling_pat.search(tail, 1)
        if sm:
            return sm.start()

    # Parenthesised Chinese numeral: "（五）" → next is "（六）"
    paren_m = re.search(r"（([" + _CHINESE_NUM_SEQ + r"]+)）", heading_str)
    if paren_m:
        cn = paren_m.group(1)
        idx = _CHINESE_NUM_SEQ.find(cn)
        if 0 <= idx < len(_CHINESE_NUM_SEQ) - 1:
            next_cn = _CHINESE_NUM_SEQ[idx + 1]
            sm = re.search(r"\n[ \t]*（" + next_cn + r"）", tail[1:], re.MULTILINE)
            if sm:
                return sm.start() + 1

    # Chinese numeral + 、: "五、" → next is "六、"
    cn_m = re.search(r"([" + _CHINESE_NUM_SEQ + r"]+)[、．.]", heading_str)
    if cn_m:
        cn = cn_m.group(1)
        idx = _CHINESE_NUM_SEQ.find(cn)
        if 0 <= idx < len(_CHINESE_NUM_SEQ) - 1:
            next_cn = _CHINESE_NUM_SEQ[idx + 1]
            sm = re.search(r"\n[ \t]*" + next_cn + r"[、．.]", tail[1:], re.MULTILINE)
            if sm:
                return sm.start() + 1

    return len(tail)


def _perf_fee_raw_section(fees_text: str) -> str:
    """Return only the performance-fee subsection of the fees chapter.

    Primary: finds ALL section headings (e.g. '5、业绩报酬', '基金管理人的业绩报酬') and
    returns the most substantive one — the heading match that yields the longest
    body text.  Contracts often have a brief fee-enumeration line ("4、业绩报酬：
    基金的证券、期货交易费用…") earlier in the fees chapter; the actual detailed clause
    with tier tables comes later.  Picking the longest match skips the brief line.
    Fallback 1: window around specific content markers like '计提业绩报酬'.
    Fallback 2: window around the first bare '业绩报酬' occurrence.
    Last resort: full fees_text.
    """
    best: str | None = None
    for m in _PERF_FEE_HEADING_PAT.finditer(fees_text):
        tail = fees_text[m.start():]
        end = _perf_fee_next_sibling_pos(m, tail)
        chunk = tail[:end].strip()
        if best is None or len(chunk) > len(best):
            best = chunk
    if best and len(best) >= 30:
        return best
    for marker in _PERF_FEE_CONTENT_MARKERS:
        idx = fees_text.find(marker)
        if idx >= 0:
            return fees_text[max(0, idx - 200):idx + 2000].strip()
    idx = fees_text.find("业绩报酬")
    if idx >= 0:
        return fees_text[max(0, idx - 100):idx + 2000].strip()
    return fees_text


def extract_path_b_rules(
    document: dict[str, Any],
    windows: dict[str, str],
    *,
    fund_name: str | None,
    product_elements: dict[str, Any],
    llm_perf_raw_section: str | None = None,
    llm_perf_flag: str | None = None,
    llm_open_day_raw_section: str | None = None,
    rag_cases: list[dict[str, str]] | None = None,
    kb_field_extractions: dict[str, tuple[str, str]] | None = None,
) -> tuple[dict[str, Any], list[ExtractionWarning]]:
    del fund_name
    warnings: list[ExtractionWarning] = []
    fees_text = windows.get("fees", "") or ""

    perf_fields: dict[str, FieldValue | None] = {}
    tiers = _parse_performance_tiers_from_table(document)

    # When LLM confirms no performance fee, record the original text as summary
    # and skip further parsing — no warning needed since the answer is definitive.
    if llm_perf_flag == "否":
        raw_text = llm_perf_raw_section or ""
        perf_fields["has_performance_fee"] = _fv("否", snippet=raw_text)
        perf_fields["summary"] = _fv(raw_text, snippet=raw_text) if raw_text else None
    elif not tiers:
        summary = _performance_summary_from_fees(fees_text)
        if summary:
            perf_fields["summary"] = summary
        elif not llm_perf_raw_section:
            # Only warn when we have neither rules-based nor LLM-sourced content.
            warnings.append(
                ExtractionWarning(
                    field="path_b.performance_fee",
                    code="path_b_incomplete",
                    message="未从合同解析到业绩报酬结构化内容",
                    suggestion="请人工查阅费用与税收章节",
                )
            )
    else:
        perf_fields["has_performance_fee"] = _fv(
            llm_perf_flag if llm_perf_flag else "是", snippet=""
        )

        method = _extract_extraction_method(fees_text)
        if method:
            perf_fields["extraction_method"] = method

        bench = _extract_benchmark_type(fees_text, tiers)
        if bench:
            perf_fields["benchmark_type"] = bench

        hurdle = _extract_hurdle_nav(fees_text, tiers)
        if hurdle:
            perf_fields["hurdle_nav"] = hurdle

        waiver = _extract_manager_waiver(fees_text)
        if waiver:
            perf_fields["manager_waiver"] = waiver

    open_fields = _extract_open_day_fields(document, windows, product_elements)
    has_schedule = bool(_field_text(open_fields.get("fixed_schedule")))
    timing = _extract_extraction_timing(fees_text, has_fixed_schedule=has_schedule)
    if timing and tiers:
        perf_fields["extraction_timing"] = timing

    if not _field_text(open_fields.get("fixed_schedule")):
        warnings.append(
            ExtractionWarning(
                field="path_b.open_day.fixed_schedule",
                code="path_b_incomplete",
                message="未解析到固定开放日规则",
            )
        )

    sub_text = windows.get("subscription", "") or ""
    raw_sections: dict[str, str] = {}
    if fees_text.strip():
        # Prefer LLM-located verbatim text; fall back to regex heuristic.
        raw_sections["performance_fee"] = (
            llm_perf_raw_section if llm_perf_raw_section
            else _perf_fee_raw_section(fees_text)
        )
    if sub_text.strip():
        # Prefer LLM-located open-day clauses; fall back to full subscription chapter.
        raw_sections["open_day"] = (
            llm_open_day_raw_section if llm_open_day_raw_section
            else sub_text
        )

    path_b = build_path_b_document(
        performance_fields=perf_fields,
        open_day_fields=open_fields,
        tiers=tiers,
        raw_sections=raw_sections,
        rag_cases=rag_cases,
        kb_field_extractions=kb_field_extractions,
    )
    return path_b, warnings
