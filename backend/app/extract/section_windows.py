from __future__ import annotations

import re
from typing import Any

WINDOW_KEYS = (
    "cover_parties",
    "basic",
    "establish",
    "subscription",
    "investment",
    "raising",
    "distribution",
    "risk",
    "fees",
)

MAX_WINDOW_CHARS = 12000

_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "fees": re.compile(r"费用与税收|费用|税收|管理费|托管费|基金服务费|业绩报酬|计提"),
    "subscription": re.compile(
        r"申购|赎回|转让|开放日|封闭|份额锁定|申购赎回"
    ),
    "establish": re.compile(r"成立|备案|清算"),
    "investment": re.compile(
        r"投资目标|投资范围|投资策略|投资限制|风控|止损|预警|投资经理|基金的投资"
    ),
    "raising": re.compile(r"募集|销售|冷静期|回访|双录"),
    "distribution": re.compile(r"收益分配|分红|分配"),
    "risk": re.compile(r"风险揭示|风险等级|风险收益"),
    "basic": re.compile(
        r"基本情况|基金的基本|存续期|组织形式|私募证券投资基金$"
    ),
    "cover_parties": re.compile(
        r"基金管理人|托管人|当事人|前言|释义|合同|封面|私募基金管理人"
    ),
}


def _section_title_map(document: dict[str, Any]) -> dict[str, str]:
    return {
        item.get("anchor_id", ""): str(item.get("title", ""))
        for item in document.get("outline", [])
        if item.get("anchor_id")
    }


def _classify_section(title: str) -> str:
    for key, pattern in _SECTION_PATTERNS.items():
        if pattern.search(title):
            return key
    return "cover_parties"


def _block_text(block: dict[str, Any]) -> str:
    if block.get("type") == "table":
        rows = block.get("rows") or []
        lines = ["\t".join(str(c) for c in row) for row in rows]
        return "\n".join(lines)
    return str(block.get("text") or "")


def build_section_windows(document: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    title_map = _section_title_map(document)
    buckets: dict[str, list[str]] = {k: [] for k in WINDOW_KEYS}
    truncated: list[str] = []

    blocks = document.get("blocks") or []
    for idx, block in enumerate(blocks):
        section_id = block.get("section_id")
        title = title_map.get(section_id or "", "")
        window = _classify_section(title) if title else (
            "cover_parties" if idx < 80 else "basic"
        )
        text = _block_text(block).strip()
        if text:
            buckets[window].append(text)

    # Early blocks always contribute to cover
    for block in blocks[:40]:
        text = _block_text(block).strip()
        if text and "基金管理人" in text or "托管人" in text or "基金" in text:
            buckets["cover_parties"].append(text)

    result: dict[str, str] = {}
    for key in WINDOW_KEYS:
        joined = "\n".join(buckets[key])
        if len(joined) > MAX_WINDOW_CHARS:
            joined = joined[:MAX_WINDOW_CHARS]
            truncated.append(key)
        result[key] = joined
    return result, truncated
