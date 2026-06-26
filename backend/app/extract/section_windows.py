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

_INVESTOR_COMMITMENT = re.compile(
    r"合格投资者|投资者承诺|适当性管理办法|风险承受能力|"
    r"私募基金投资者承诺|本人/本单位承诺",
)

_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "fees": re.compile(r"费用与税收|费用|税收|管理费|托管费|基金服务费|外包服务费|业绩报酬|计提"),
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


def section_title_map(document: dict[str, Any]) -> dict[str, str]:
    return {
        item.get("anchor_id", ""): str(item.get("title", ""))
        for item in document.get("outline", [])
        if item.get("anchor_id")
    }



_RISK_DISCLOSURE_SUB = re.compile(r"引起的风险|可能.*?风险|带来.*?风险")


def _classify_section(title: str) -> str:
    t = title.strip()
    if _INVESTOR_COMMITMENT.search(t):
        return "risk"
    if t in ("基金的投资",) or re.match(r"^基金的投资\s*\d*$", t):
        return "investment"
    # Numbered risk-disclosure sub-items like "17、业绩报酬安排可能引起的风险" contain
    # fee-related keywords ("业绩报酬") but belong to the risk chapter, not fees.
    # Check this BEFORE the main pattern loop so "fees" doesn't steal them.
    if _RISK_DISCLOSURE_SUB.search(t):
        return "risk"
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
        tail = source[pos:]
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


def _normalize_outline_title(title: str) -> str:
    """Strip Word TOC page tabs; keep actual heading text."""
    return re.sub(r"\t\d+\s*$", "", (title or "").strip())


# Common prefix for numbered main chapters — supports 章/部分/篇 so patterns work
# across contracts that differ only in structural word (e.g. "第七部分" vs "第七章").
_CHAPTER_NUM_PREFIX = r"^(?:第[零一二三四五六七八九十百]+(?:章|部分|篇)[：:\s]*)?"

# Main chapter headings from parsed outline (wording varies by contract).
_MAIN_CHAPTER_PATTERNS: dict[str, re.Pattern[str]] = {
    "raising": re.compile(
        _CHAPTER_NUM_PREFIX + r"(?:私募)?基金的募集\s*$"
    ),
    "subscription": re.compile(
        _CHAPTER_NUM_PREFIX + r"(?:私募)?基金的申购[、,]\s*赎回"
    ),
}

# Next major part after 申赎章（目录表述不一，用常见后继章名截断）
_CHAPTER_BOUNDARY = re.compile(
    _CHAPTER_NUM_PREFIX
    + r"(?:当事人及权利义务|基金的财产|基金的投资|费用与税收|基金的收益|"
    r"风险揭示|基金的成立|基金合同的效力)"
)


def _main_chapter_window(title: str) -> str | None:
    norm = _normalize_outline_title(title)
    for key, pattern in _MAIN_CHAPTER_PATTERNS.items():
        if pattern.search(norm):
            return key
    return None


def _is_plausible_chapter_heading(norm: str, window_key: str) -> bool:
    """Ignore mis-detected outline rows (long sentences tagged as level-1)."""
    if not norm or len(norm) > 72:
        return False
    if pat := _MAIN_CHAPTER_PATTERNS.get(window_key):
        if pat.search(norm):
            return True
    if len(norm) > 48:
        return False
    if window_key == "raising":
        return bool(re.search(r"(?:私募)?基金的募集\s*$", norm))
    if window_key == "subscription":
        return bool(re.search(r"(?:私募)?基金的申购.*赎回", norm))
    return False


def _chapter_start_rank(norm: str, window_key: str) -> tuple[int, int, int]:
    """Prefer exact main-chapter titles; among TOC/body duplicates prefer later body copy."""
    exact = 0
    if window_key == "raising" and re.search(r"^(?:私募)?基金的募集\s*$", norm):
        exact = 3
    elif window_key == "subscription" and re.search(
        r"^(?:私募)?基金的申购[、,]\s*赎回", norm
    ):
        exact = 3
    elif _MAIN_CHAPTER_PATTERNS[window_key].search(norm):
        exact = 2
    return (exact, -len(norm), 0)


def find_outline_chapter_span(
    outline: list[dict[str, Any]],
    window_key: str,
) -> tuple[str, str | None] | None:
    """
    Locate (start_anchor, end_anchor_exclusive) for a main chapter from doc outline.
    Picks the best main heading; when TOC and body repeat, later body copy wins via index.
    """
    if window_key not in _MAIN_CHAPTER_PATTERNS:
        return None
    candidates: list[int] = []
    for i, item in enumerate(outline):
        norm = _normalize_outline_title(str(item.get("title") or ""))
        if _is_plausible_chapter_heading(norm, window_key):
            candidates.append(i)
    if not candidates:
        return None
    start_idx = max(
        candidates,
        key=lambda i: (
            _chapter_start_rank(
                _normalize_outline_title(str(outline[i].get("title") or "")),
                window_key,
            ),
            i,
        ),
    )
    end_idx = len(outline)
    for j in range(start_idx + 1, len(outline)):
        norm = _normalize_outline_title(str(outline[j].get("title") or ""))
        other = _main_chapter_window(norm)
        if other and other != window_key:
            end_idx = j
            break
        if _CHAPTER_BOUNDARY.search(norm):
            end_idx = j
            break
    start_aid = str(outline[start_idx].get("anchor_id") or "")
    if not start_aid:
        return None
    end_aid: str | None = None
    if end_idx < len(outline):
        end_aid = str(outline[end_idx].get("anchor_id") or "") or None
    return start_aid, end_aid


def gather_outline_chapter_text(
    document: dict[str, Any],
    window_key: str,
) -> str:
    """All block text under a main outline chapter (by actual 目录), not hardcoded 五、… titles."""
    outline = document.get("outline") or []
    if not outline:
        return ""
    span = find_outline_chapter_span(outline, window_key)
    if not span:
        return ""
    start_aid, end_aid = span
    anchor_order = [str(o.get("anchor_id") or "") for o in outline if o.get("anchor_id")]
    if start_aid not in anchor_order:
        return ""
    start_pos = anchor_order.index(start_aid)
    end_pos = anchor_order.index(end_aid) if end_aid and end_aid in anchor_order else len(
        anchor_order
    )
    allowed = set(anchor_order[start_pos:end_pos])
    lines: list[str] = []
    for block in document.get("blocks") or []:
        sid = block.get("section_id")
        if sid not in allowed:
            continue
        text = _block_text(block).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def build_section_windows(document: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Build full chapter windows for LLM prompts; no head truncation."""
    title_map = section_title_map(document)
    buckets: dict[str, list[str]] = {k: [] for k in WINDOW_KEYS}

    blocks = document.get("blocks") or []
    last_section_id: str | None = None
    for idx, block in enumerate(blocks):
        section_id = block.get("section_id")
        title = title_map.get(section_id or "", "")
        window = _classify_section(title) if title else (
            "cover_parties" if idx < 80 else "basic"
        )
        # Inject the section title as a heading line when entering a new section.
        # Word headings are often stored only in the outline (not as body blocks), so
        # without this the fees window lacks the "4、基金管理人的业绩报酬" line and
        # _perf_fee_raw_section's heading-pattern match falls back to the wrong section.
        if section_id and section_id != last_section_id and title.strip():
            buckets[window].append(title.strip())
            last_section_id = section_id
        text = _block_text(block).strip()
        if text:
            buckets[window].append(text)

    for block in blocks[:40]:
        text = _block_text(block).strip()
        if text and "基金管理人" in text or "托管人" in text or "基金" in text:
            buckets["cover_parties"].append(text)

    result: dict[str, str] = {
        key: "\n".join(buckets[key]) for key in WINDOW_KEYS
    }

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
        result["investment"] = investment_slice

    return result, []
