"""Map path_b JSON to CRM「业绩报酬提取设置」手录字段建议（含摘录与诊断说明）。"""

from __future__ import annotations

import re
from typing import Any


_split_tokens = lambda s: set(t for t in re.split(r"[、，,\s；;/]+", s.strip()) if t)


def _kb_matches(suggested: str | None, kb_value: str) -> bool:
    """KB 值的所有 token 都被 suggested 覆盖才算一致（子集判断，非单纯交集）。"""
    if not suggested or not kb_value:
        return False
    return _split_tokens(kb_value).issubset(_split_tokens(suggested))


def _find_similar_passage(text: str, kb_snippets: list[str], min_score: float = 0.08) -> str | None:
    """用 KB 摘录的字符 bigram 在当前合同文本里定位最相似的段落。"""
    passages = [p.strip() for p in re.split(r"[。；\n]+", text) if len(p.strip()) > 4]
    if not passages:
        return None

    def bigrams(s: str) -> set[str]:
        return {s[i : i + 2] for i in range(len(s) - 1)}

    best_score = 0.0
    best_idx = -1
    for kb_snip in kb_snippets:
        kb_bi = bigrams(kb_snip)
        if not kb_bi:
            continue
        for idx, passage in enumerate(passages):
            p_bi = bigrams(passage)
            if not p_bi:
                continue
            score = len(kb_bi & p_bi) / len(kb_bi | p_bi)
            if score > best_score:
                best_score = score
                best_idx = idx

    if best_idx < 0 or best_score < min_score:
        return None

    start = max(0, best_idx - 1)
    end = min(len(passages), best_idx + 3)
    return "。".join(passages[start:end])


def _rag_note(crm_field: str, suggested: str | None, kb_index: dict[str, list[dict]]) -> str:
    """生成 KB 交叉核对诊断追加文本。crm_field 与 KB field_name 直接匹配。"""
    cases = kb_index.get(crm_field) or []
    if not cases:
        return ""
    kb_values = list(dict.fromkeys(
        c.get("field_value", "").strip() for c in cases if c.get("field_value", "").strip()
    ))
    if not kb_values:
        return ""
    kb_repr = "、".join(kb_values[:2])
    if any(_kb_matches(suggested, v) for v in kb_values):
        return f" · 知识库参考一致（{kb_repr}）"
    # 有部分重叠但 KB 包含更多 token → 提示缺失项
    s_tokens = _split_tokens(suggested or "")
    all_kb_tokens: set[str] = set()
    for v in kb_values:
        all_kb_tokens |= _split_tokens(v)
    missing = all_kb_tokens - s_tokens
    if missing and s_tokens:
        missing_str = "、".join(list(missing)[:3])
        return f" · 知识库含「{missing_str}」，建议核查"
    return f" · 知识库案例：{kb_repr}，建议核查"

_CRM_METHOD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("基金整体资产高水位法", re.compile(r"基金整体资产高水位|整体.*?高水位|基金整体.*?高水位")),
    ("单个投资者高水位法", re.compile(r"单个投资者.*?高水位|单笔高水位")),
    ("份额净值法", re.compile(r"份额净值")),
    ("高水位法", re.compile(r"高水位")),
]

_TIMING_KEYWORDS: list[tuple[str, str]] = [
    ("固定时点", r"固定.*?开放|开放日|估值日|计提日|每年.*?月|每季|每半年"),
    ("分红", r"分红|收益分配"),
    ("赎回", r"赎回"),
    ("基金清算", r"清算|合同终止|基金终止|解散"),
]

_HURDLE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("无门槛", re.compile(r"无门槛|不设门槛")),
    ("分段设置", re.compile(r"分段|分档|阶梯")),
    ("初始水位线", re.compile(r"初始净值|初始份额净值|成立日.*?净值|面值.*?1(?:\.0+)?元")),
]

_RE_INDEX_BENCHMARK = re.compile(
    r"中证\d{3}|沪深\d{3}|上证.*?指数|深证.*?指数|CSI\s*\d+|万得.*?指数|业绩比较基准",
    re.IGNORECASE,
)


def _snip(snippets: dict[str, str], *paths: str) -> str | None:
    for p in paths:
        t = snippets.get(p)
        if t and str(t).strip():
            return str(t).strip()
    return None


def _suggest_method(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    for label, pat in _CRM_METHOD_PATTERNS:
        if pat.search(raw):
            return label, raw
    return raw[:80] + ("…" if len(raw) > 80 else ""), raw


def _suggest_benchmark(
    raw_bench: str | None,
    raw_method: str | None,
    tiers: list[dict],
    fees_context: str,
) -> tuple[str | None, str | None, str]:
    """
    业绩基准类型判断：
    - 超额收益：与外部指数/基准比较
    - 净值型：高水位法（以基金自身净值为比较基准，不参照外部指数）
    返回 (值, 摘录, 诊断说明)
    """
    text = (raw_bench or "") + " " + (raw_method or "")
    for t in tiers:
        text += " " + str(t.get("description") or "")

    if raw_bench:
        if "超额收益" in raw_bench:
            return "超额收益", raw_bench[:200], "合同含超额收益描述"
        if "净值型" in raw_bench:
            return "净值型", raw_bench[:200], "合同直接描述净值型"

    # 含外部指数引用 → 超额收益
    m_idx = _RE_INDEX_BENCHMARK.search(fees_context + " " + text)
    if m_idx:
        return "超额收益", m_idx.group(0), f"合同引用外部基准（{m_idx.group(0)}）→ 超额收益"

    # 高水位法无外部指数 → 净值型
    if re.search(r"高水位", text):
        return "净值型", text[:100], "高水位法且无外部指数比较，建议填净值型"

    return None, None, "无法从合同自动判断，请人工确认"


def _suggest_hurdle(fees_context: str, tiers: list[dict]) -> tuple[str | None, str | None, str]:
    """返回 (值, 摘录, 诊断说明)。"""
    blob = fees_context + " ".join(str(t.get("description") or "") for t in tiers)
    if not blob.strip():
        return None, None, "无业绩报酬内容"

    if "正收益" in blob and "超额" in blob:
        snip = next(
            (str(t.get("description")) for t in tiers if t.get("description") and "正收益" in str(t["description"])),
            blob[:200],
        )
        return "初始水位线", snip, "合同描述'正收益基础'，对应CRM初始水位线（净值1.0）"

    for label, pat in _HURDLE_PATTERNS:
        m = pat.search(blob)
        if m:
            diag = {
                "无门槛": "合同明确无门槛，直接填写",
                "分段设置": "合同含分段/阶梯描述，需逐档录入",
                "初始水位线": "合同以初始净值/面值为水位线",
            }.get(label, "")
            return label, m.group(0), diag
    return None, None, "未检测到门槛信息，请人工确认"


def _suggest_timing(fees_context: str) -> tuple[str | None, str | None]:
    if not fees_context.strip():
        return None, None
    hits: list[str] = []
    snips: list[str] = []
    for label, pat in _TIMING_KEYWORDS:
        m = re.search(pat, fees_context)
        if m:
            hits.append(label)
            snips.append(m.group(0))
    if not hits:
        return None, None
    return "、".join(hits), "；".join(dict.fromkeys(snips))[:400]


def _suggest_ratio(tiers: list[dict]) -> tuple[str | None, str | None]:
    if not tiers:
        return None, None
    parts: list[str] = []
    snips: list[str] = []
    for t in tiers:
        letter = t.get("share_class") or "?"
        desc = str(t.get("description") or "").strip()
        ratio = t.get("ratio_pct")
        if ratio:
            parts.append(f"{letter}类: {ratio}%")
        elif desc:
            parts.append(f"{letter}类: {desc[:40]}")
        if desc:
            snips.append(f"{letter}: {desc}")
    if not parts:
        return None, None
    return "；".join(parts), "\n".join(snips[:4])


def build_crm_handoff(
    path_b: dict[str, Any],
    *,
    fees_context: str = "",
    rag_cases: list[dict[str, str]] | None = None,
) -> list[dict[str, str | None]]:
    """CRM 手录字段列表：crm_field, suggested_value, snippet, coverage, diagnostic。"""
    perf = path_b.get("performance_fee") or {}
    open_day = path_b.get("open_day") or {}
    snippets = path_b.get("source_snippets") or {}
    tiers: list[dict] = perf.get("tiers") if isinstance(perf.get("tiers"), list) else []
    fees_ctx = fees_context or str(perf.get("summary") or "")

    # Build KB lookup by field_name for O(1) cross-reference in each row
    kb_cases = rag_cases or (path_b.get("kb_cases") or [])
    kb_index: dict[str, list[dict]] = {}
    for c in kb_cases:
        fn = c.get("field_name", "").strip()
        if fn:
            kb_index.setdefault(fn, []).append(c)

    kb_extractions: dict[str, tuple[str, str]] = path_b.get("kb_field_extractions") or {}

    def _kb_llm(crm_field: str) -> tuple[str | None, str | None]:
        """返回 LLM 预提取的 (value, passage)；无则 (None, None)。"""
        entry = kb_extractions.get(crm_field)
        if entry:
            return entry[0] or None, entry[1] or None
        return None, None

    items: list[dict[str, str | None]] = []

    def add(
        crm_field: str,
        value: str | None,
        snippet: str | None,
        *,
        coverage: str,
        diagnostic: str = "",
    ) -> None:
        items.append(
            {
                "crm_field": crm_field,
                "suggested_value": value,
                "snippet": snippet,
                "coverage": coverage,
                "diagnostic": diagnostic,
            }
        )

    # 0. 是否计提业绩报酬（首行，决定下方字段是否需要填）
    has_pf = perf.get("has_performance_fee")
    has_pf_snip = _snip(snippets, "performance_fee.has_performance_fee") or _snip(
        snippets, "performance_fee.summary"
    )
    if has_pf:
        diag_pf = "LLM 从合同原文判断" if has_pf != "是" or not tiers else "合同含业绩报酬条款"
        coverage_pf = "full" if has_pf == "否" else "partial"
    else:
        diag_pf = "未能自动判断，请人工确认"
        coverage_pf = "missing"
    add(
        "是否计提业绩报酬",
        has_pf,
        has_pf_snip,
        coverage=coverage_pf,
        diagnostic=diag_pf,
    )

    # 1. 业绩报酬提取方式
    raw_method = perf.get("extraction_method")
    kb_m_val, kb_m_snip = _kb_llm("业绩报酬提取方式")
    if kb_m_val:
        method, snip_m = kb_m_val, kb_m_snip
        diag_m = "知识库案例定位，LLM 从相似段落提取"
    else:
        method, snip_m = _suggest_method(raw_method or _snip(snippets, "performance_fee.extraction_method"))
        diag_m = "合同明确描述，可直接填写" if method else "未检测到提取方式关键词，请查阅费用与税收章节"
    diag_m += _rag_note("业绩报酬提取方式", method, kb_index)
    add(
        "业绩报酬提取方式",
        method,
        snip_m or _snip(snippets, "performance_fee.extraction_method"),
        coverage="partial" if method else "missing",
        diagnostic=diag_m,
    )

    # 2. 业绩基准类型
    raw_bench = perf.get("benchmark_type")
    kb_b_val, kb_b_snip = _kb_llm("业绩基准类型")
    if kb_b_val:
        bench, snip_b, diag_b = kb_b_val, kb_b_snip, "知识库案例定位，LLM 从相似段落提取"
    else:
        bench, snip_b, diag_b = _suggest_benchmark(raw_bench, raw_method, tiers, fees_ctx)
    diag_b += _rag_note("业绩基准类型", bench, kb_index)
    add(
        "业绩基准类型",
        bench,
        snip_b or _snip(snippets, "performance_fee.benchmark_type"),
        coverage="partial" if bench else "missing",
        diagnostic=diag_b,
    )

    # 3. 门槛净值类型
    if perf.get("hurdle_nav"):
        hurdle = str(perf["hurdle_nav"])
        snip_h = _snip(snippets, "performance_fee.hurdle_nav")
        diag_h = "已从合同检测到门槛描述"
    else:
        kb_h_val, kb_h_snip = _kb_llm("门槛净值类型")
        if kb_h_val:
            hurdle, snip_h, diag_h = kb_h_val, kb_h_snip, "知识库案例定位，LLM 从相似段落提取"
        else:
            hurdle, snip_h, diag_h = _suggest_hurdle(fees_ctx, tiers)
    diag_h += _rag_note("门槛净值类型", hurdle, kb_index)
    add(
        "门槛净值类型",
        hurdle,
        snip_h,
        coverage="partial" if hurdle else "missing",
        diagnostic=diag_h,
    )

    # 4. 提取时点
    if perf.get("extraction_timing"):
        timing = str(perf["extraction_timing"])
        snip_t = _snip(snippets, "performance_fee.extraction_timing")
        diag_t = "合同明确描述提取时点"
    else:
        kb_t_val, kb_t_snip = _kb_llm("提取时点")
        if kb_t_val:
            timing, snip_t, diag_t = kb_t_val, kb_t_snip, "知识库案例定位，LLM 从相似段落提取"
        else:
            timing, snip_t = _suggest_timing(fees_ctx)
            diag_t = "从费用章节关键词推断" if timing else "请人工确认提取时点"
    diag_t += _rag_note("提取时点", timing, kb_index)
    add(
        "提取时点",
        timing,
        snip_t,
        coverage="partial" if timing else "missing",
        diagnostic=diag_t,
    )

    # 5. 提取比例（来自表格结构，不做段落定位）
    ratio, snip_r = _suggest_ratio(tiers)
    diag_r = "从基本情况表格提取，按份额类填写" if ratio else "未找到业绩报酬比例"
    diag_r += _rag_note("提取比例", ratio, kb_index)
    add(
        "提取比例",
        ratio,
        snip_r or _snip(snippets, "performance_fee.tiers[0].ratio_pct"),
        coverage="full" if ratio else "missing",
        diagnostic=diag_r,
    )

    # 6. 固定时点提取频率（仅当提取时点含"固定时点"时才有意义）
    if timing and "固定时点" in timing:
        schedule = open_day.get("fixed_schedule")
        diag_s = "来自合同开放日安排，与固定时点一致" if schedule else "未解析到开放日规则，请人工填写"
        add(
            "固定时点提取频率",
            schedule,
            _snip(snippets, "open_day.fixed_schedule"),
            coverage="partial" if schedule else "missing",
            diagnostic=diag_s,
        )

    return items
