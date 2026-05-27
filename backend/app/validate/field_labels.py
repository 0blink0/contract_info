from __future__ import annotations

import re

_PATH_B: dict[str, str] = {
    "performance_fee.extraction_method": "业绩报酬·计提方式",
    "performance_fee.benchmark_type": "业绩报酬·基准类型",
    "performance_fee.hurdle_nav": "业绩报酬·门槛净值",
    "performance_fee.extraction_timing": "业绩报酬·提取时点",
    "performance_fee.summary": "业绩报酬·摘要",
    "open_day.fixed_schedule": "开放日·固定安排",
    "open_day.open_business": "开放日·开放业务",
    "open_day.temporary_open": "开放日·临时开放",
    "open_day.ad_hoc_rules": "开放日·特殊规则",
}

_TIER_FIELD: dict[str, str] = {
    "ratio_pct": "计提比例",
    "description": "档位说明",
    "benchmark": "比较基准",
    "threshold": "计提门槛",
}

_RE_PATH_B_TIER = re.compile(
    r"^performance_fee\.tiers\[(\d+)\]\.(\w+)$"
)


def label_for_path_b_snippet(path: str, path_b: dict | None = None) -> str:
    """Chinese label for path_b source_snippets keys (no path_b. prefix)."""
    text = (path or "").strip()
    if not text:
        return text
    if text in _PATH_B:
        return _PATH_B[text]
    m = _RE_PATH_B_TIER.match(text)
    if m:
        tier_idx = int(m.group(1))
        sub = _TIER_FIELD.get(m.group(2), m.group(2))
        share: str | None = None
        if path_b:
            tiers = (path_b.get("performance_fee") or {}).get("tiers") or []
            if tier_idx < len(tiers) and isinstance(tiers[tier_idx], dict):
                raw = tiers[tier_idx].get("share_class")
                if raw:
                    share = str(raw).upper()
        if share:
            return f"业绩报酬·{share}类·{sub}"
        return f"业绩报酬·第{tier_idx + 1}档·{sub}"
    parts = text.split(".")
    if len(parts) >= 2:
        module = "业绩报酬" if parts[0] == "performance_fee" else "开放日"
        return f"{module}·{parts[-1]}"
    return text


def label_for_validation_field(
    field: str,
    extraction_result: dict | None = None,
) -> str:
    """Human-readable label for validation UI (product fields already Chinese)."""
    text = (field or "").strip()
    if not text:
        return text
    if text.startswith("path_b."):
        path_b = None
        if extraction_result:
            path_b = extraction_result.get("path_b_json") or extraction_result.get("path_b")
        return label_for_path_b_snippet(text[len("path_b.") :], path_b)
    if text.startswith("fee_rates["):
        m = re.match(r"^fee_rates\[(\d+)\]\.(.+)$", text)
        if m:
            return f"费率表·第{int(m.group(1)) + 1}行·{m.group(2)}"
    if text.startswith("subscription_fees["):
        m = re.match(r"^subscription_fees\[(\d+)\]\.(.+)$", text)
        if m:
            idx = int(m.group(1))
            col = m.group(2)
            fee_label = "申赎费"
            if extraction_result:
                rows = extraction_result.get("subscription_fees") or []
                if idx < len(rows) and isinstance(rows[idx], dict):
                    fee_label = str(rows[idx].get("申赎费类型") or fee_label)
            return f"{fee_label}·第{idx + 1}行·{col}"
    return text
