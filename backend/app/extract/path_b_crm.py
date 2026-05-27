"""Map path_b JSON to CRM「业绩报酬提取设置」手录字段建议（含摘录）。"""

from __future__ import annotations

import re
from typing import Any

_CRM_METHOD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("基金整体资产高水位法", re.compile(r"整体.*?高水位|基金整体.*?高水位")),
    ("单个投资者高水位法", re.compile(r"单个投资者.*?高水位")),
    ("份额净值法", re.compile(r"份额净值")),
    ("高水位法", re.compile(r"高水位")),
]

_CRM_BENCHMARK_MAP = {
    "超额收益": "超额收益",
    "净值型": "净值型",
    "指数型": "指数型",
}

_TIMING_KEYWORDS: list[tuple[str, str]] = [
    ("固定时点", r"固定.*?开放|开放日|估值日|计提日|每年.*?月"),
    ("分红", r"分红|收益分配"),
    ("赎回", r"赎回"),
    ("基金清算", r"清算|合同终止|基金终止|解散"),
]

_HURDLE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("无门槛", re.compile(r"无门槛|不设门槛")),
    ("初始净值", re.compile(r"初始净值|初始份额净值|成立日.*?净值")),
    ("分段收费", re.compile(r"分段|分档|超额.*?部分")),
]


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


def _suggest_benchmark(raw: str | None, tiers: list[dict]) -> tuple[str | None, str | None]:
    text = raw or ""
    for t in tiers:
        text += " " + str(t.get("description") or "")
    if not text.strip():
        return None, None
    for key, label in _CRM_BENCHMARK_MAP.items():
        if key in text:
            return label, text[:300]
    if "中证" in text or "指数" in text:
        return "超额收益", text[:300]
    return None, text[:300] if text else None


def _suggest_hurdle(fees_context: str, tiers: list[dict]) -> tuple[str | None, str | None]:
    blob = fees_context + " ".join(str(t.get("description") or "") for t in tiers)
    if not blob.strip():
        return None, None
    if "正收益" in blob and "超额" in blob:
        snip = next(
            (str(t.get("description")) for t in tiers if t.get("description") and "正收益" in str(t["description"])),
            blob[:200],
        )
        return "有收益门槛（合同：正收益基础，CRM 请对照选「初始净值」或分段）", snip
    for label, pat in _HURDLE_PATTERNS:
        m = pat.search(blob)
        if m:
            return label, m.group(0)
    return None, None


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


def build_crm_handoff(path_b: dict[str, Any], *, fees_context: str = "") -> list[dict[str, str | None]]:
    """CRM 手录字段列表：crm_field, suggested_value, snippet, coverage."""
    perf = path_b.get("performance_fee") or {}
    open_day = path_b.get("open_day") or {}
    snippets = path_b.get("source_snippets") or {}
    tiers = perf.get("tiers") if isinstance(perf.get("tiers"), list) else []
    fees_ctx = fees_context or str(perf.get("summary") or "")

    items: list[dict[str, str | None]] = []

    def add(
        crm_field: str,
        value: str | None,
        snippet: str | None,
        *,
        coverage: str,
    ) -> None:
        items.append(
            {
                "crm_field": crm_field,
                "suggested_value": value,
                "snippet": snippet,
                "coverage": coverage,
            }
        )

    raw_method = perf.get("extraction_method")
    method, snip_m = _suggest_method(
        raw_method or _snip(snippets, "performance_fee.extraction_method")
    )
    add(
        "业绩报酬提取方式",
        method,
        snip_m or _snip(snippets, "performance_fee.extraction_method"),
        coverage="partial" if method else "missing",
    )

    bench, snip_b = _suggest_benchmark(
        perf.get("benchmark_type"),
        tiers,
    )
    add(
        "业绩基准类型",
        bench,
        snip_b or _snip(snippets, "performance_fee.benchmark_type"),
        coverage="partial" if bench else "missing",
    )

    if perf.get("hurdle_nav"):
        hurdle = str(perf["hurdle_nav"])
        snip_h = _snip(snippets, "performance_fee.hurdle_nav")
    else:
        hurdle, snip_h = _suggest_hurdle(fees_ctx, tiers)
    add(
        "门槛净值类型",
        hurdle,
        snip_h,
        coverage="partial" if hurdle else "missing",
    )

    if perf.get("extraction_timing"):
        timing = str(perf["extraction_timing"])
        snip_t = _snip(snippets, "performance_fee.extraction_timing")
    else:
        timing, snip_t = _suggest_timing(fees_ctx)
        if not timing and open_day.get("fixed_schedule"):
            timing = "固定时点"
            snip_t = str(open_day["fixed_schedule"])
    add(
        "提取时点",
        timing,
        snip_t,
        coverage="partial" if timing else "missing",
    )

    ratio, snip_r = _suggest_ratio(tiers)
    add(
        "提取比例",
        ratio,
        snip_r or _snip(snippets, "performance_fee.tiers[0].ratio_pct"),
        coverage="partial" if ratio else "missing",
    )

    schedule = open_day.get("fixed_schedule")
    add(
        "固定时点提取频率",
        schedule,
        _snip(snippets, "open_day.fixed_schedule"),
        coverage="partial" if schedule else "missing",
    )

    return items
