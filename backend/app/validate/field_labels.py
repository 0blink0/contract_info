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


def label_for_validation_field(field: str) -> str:
    """Human-readable label for validation UI (product fields already Chinese)."""
    text = (field or "").strip()
    if not text:
        return text
    if text.startswith("path_b."):
        path = text[len("path_b.") :]
        if path in _PATH_B:
            return _PATH_B[path]
        m = _RE_PATH_B_TIER.match(path)
        if m:
            tier_no = int(m.group(1)) + 1
            sub = _TIER_FIELD.get(m.group(2), m.group(2))
            return f"业绩报酬·第{tier_no}档·{sub}"
        parts = path.split(".")
        if len(parts) >= 2:
            module = "业绩报酬" if parts[0] == "performance_fee" else "开放日"
            return f"{module}·{parts[-1]}"
        return path
    if text.startswith("fee_rates["):
        m = re.match(r"^fee_rates\[(\d+)\]\.(.+)$", text)
        if m:
            return f"费率表·第{int(m.group(1)) + 1}行·{m.group(2)}"
    if text.startswith("subscription_fees["):
        m = re.match(r"^subscription_fees\[(\d+)\]\.(.+)$", text)
        if m:
            return f"申购费·第{int(m.group(1)) + 1}行·{m.group(2)}"
    return text
