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

_INVESTOR_COMMITMENT = re.compile(
    r"合格投资者|投资者承诺|适当性管理办法|风险承受能力|"
    r"私募基金投资者承诺|本人/本单位承诺",
)

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
    t = title.strip()
    if _INVESTOR_COMMITMENT.search(t):
        return "risk"
    if t in ("基金的投资",) or re.match(r"^基金的投资\s*\d*$", t):
        return "investment"
    for key, pattern in _SECTION_PATTERNS.items():
        if pattern.search(t):
            return key
    return "cover_parties"


_INVESTMENT_CHAPTER_START = re.compile(
    r"^基金的投资\s*$|"
    r"^十[一二三四五六七八九]?、\s*(?:私募)?基金的投资\s*$|"
    r"^二、\s*基金的投资\s*$",
)


def _is_outline_toc_line(text: str) -> bool:
    t = text.strip()
    return len(t) < 120 and bool(re.search(r"\t\d{1,4}\s*$", t))
_INVESTMENT_CHAPTER_END = re.compile(
    r"^七、\s*基金的申购|^八、\s*基金|"
    r"^十二、\s*(?:私募)?基金的财产|"
    r"基金的申购、赎回与转让|基金的申购、赎回",
)


def _rebuild_investment_window(
    blocks: list[dict[str, Any]],
    title_map: dict[str, str],
) -> str:
    """Full 基金的投资 chapter from start marker through 申购赎回前（含后半段业绩基准/经理等）。"""
    lines: list[str] = []
    active = False
    for block in blocks:
        text = _block_text(block).strip()
        if not text:
            continue
        title = title_map.get(block.get("section_id") or "", "").strip()
        head = f"{title}\n{text}" if title else text
        if not active:
            if _is_outline_toc_line(text):
                continue
            if (
                title in ("基金的投资",)
                or _INVESTMENT_CHAPTER_START.search(text[:160])
                or _INVESTMENT_CHAPTER_START.search(head[:200])
            ):
                active = True
            else:
                continue
        if active and _INVESTMENT_CHAPTER_END.search(text[:80]):
            break
        if _INVESTOR_COMMITMENT.search(text[:400]):
            continue
        lines.append(text)
    return "\n".join(lines)


def _append_missing_sections(target: str, source: str, markers: tuple[str, ...]) -> str:
    if not source.strip():
        return target
    parts = [target] if target.strip() else []
    for marker in markers:
        if marker in target:
            continue
        if marker not in source:
            continue
        pos = source.find(marker)
        tail = source[pos : pos + 2500]
        next_m = _INVESTMENT_CHAPTER_END.search(tail[80:])
        chunk = tail[: next_m.start() + 80] if next_m else tail
        if chunk.strip():
            parts.append(chunk.strip())
    return "\n\n".join(parts)


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

    investment_slice = _rebuild_investment_window(blocks, title_map)
    risk_text = result.get("risk", "")
    investment_slice = _append_missing_sections(
        investment_slice,
        risk_text,
        (
            "（十）风险收益特征",
            "（十一）",
            "基金的预警与止损",
            "（八）业绩比较基准",
            "业绩比较基准",
            "（十二）投资经理",
        ),
    )
    if len(investment_slice) > 200:
        if len(investment_slice) > MAX_WINDOW_CHARS:
            investment_slice = investment_slice[:MAX_WINDOW_CHARS]
            truncated.append("investment")
        result["investment"] = investment_slice

    return result, truncated
