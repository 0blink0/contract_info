"""Map product fields to chapter windows for group-level 原文 excerpts."""

from __future__ import annotations

from backend.app.extract.field_catalog import CHAPTER_FIELDS
from backend.app.extract.text_limits import excerpt_for_display

# field name -> window_key (first chapter wins)
FIELD_TO_WINDOW: dict[str, str] = {}
for _window, _fields in CHAPTER_FIELDS.items():
    for _name in _fields:
        FIELD_TO_WINDOW.setdefault(_name, _window)


def normalize_chapter_snippets(raw: object) -> dict[str, str]:
    """Accept 章节摘录 dict from LLM; keys may be window_key or Chinese labels."""
    if not isinstance(raw, dict):
        return {}
    label_to_key = {
        "当事人与合同前言章节": "cover_parties",
        "基金基本情况章节": "basic",
        "申购赎回章节": "subscription",
        "投资范围与策略章节": "investment",
        "募集与销售章节": "raising",
        "收益分配章节": "distribution",
        "风险揭示章节": "risk",
        "费用与税收章节": "fees",
    }
    out: dict[str, str] = {}
    for key, val in raw.items():
        if val is None:
            continue
        text = str(val).strip()
        if not text:
            continue
        win = label_to_key.get(str(key).strip(), str(key).strip())
        out[win] = excerpt_for_display(text)
    return out


def snippet_for_field(field_name: str, chapter_snippets: dict[str, str]) -> str | None:
    win = FIELD_TO_WINDOW.get(field_name)
    if win and chapter_snippets.get(win):
        return chapter_snippets[win]
    return None


def apply_row_group_snippet(rows: list, group_snippet: str | None) -> None:
    """Attach one group 原文 to every row (export/validation use per-row snippet)."""
    snip = (group_snippet or "").strip()
    if not snip:
        return
    snip = excerpt_for_display(snip)
    for row in rows:
        if getattr(row, "snippet", None) in (None, ""):
            row.snippet = snip
