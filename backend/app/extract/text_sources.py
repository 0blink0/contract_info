"""Gather chapter text for LLM prompts (no field extraction)."""

from __future__ import annotations

import re
from typing import Any

from backend.app.extract.section_windows import gather_outline_chapter_text

_RAISING_BLOCK_MARKERS = (
    "认购费率为",
    "认购费率",
    "净认购金额",
    "认购份额",
    "价内法",
    "价外法",
)

_SUBSCRIPTION_BLOCK_MARKERS = (
    "申购费率为",
    "申购费率",
    "赎回费率为",
    "赎回费率",
    "短期赎回",
    "持有期低于",
    "持有期在",
    "价内法",
    "价外法",
    "净申购金额",
)

_COMBINED_RULE_MARKERS = _RAISING_BLOCK_MARKERS + _SUBSCRIPTION_BLOCK_MARKERS


def _append_paragraph_blocks(
    document: dict[str, Any], markers: tuple[str, ...], chunks: list[str]
) -> None:
    seen: set[str] = set(chunks)
    for block in document.get("blocks") or []:
        if block.get("type") != "paragraph":
            continue
        text = str(block.get("text") or "").strip()
        if not text or text in seen:
            continue
        if any(m in text for m in markers):
            chunks.append(text)
            seen.add(text)


def gather_full_document_text(document: dict[str, Any]) -> str:
    """Return all block text from the document for full-contract LLM extraction."""
    parts: list[str] = []
    for block in document.get("blocks") or []:
        if block.get("type") == "table":
            rows = block.get("rows") or []
            text = "\n".join("\t".join(str(c) for c in row) for row in rows)
        else:
            text = str(block.get("text") or "")
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts)


def gather_raising_fee_text(
    document: dict[str, Any],
    windows: dict[str, str],
) -> str:
    chunks: list[str] = []
    outline_text = gather_outline_chapter_text(document, "raising").strip()
    if outline_text:
        chunks.append(outline_text)
    else:
        part = (windows.get("raising") or "").strip()
        if part:
            chunks.append(part)
    _append_paragraph_blocks(document, _RAISING_BLOCK_MARKERS, chunks)
    return "\n".join(chunks)


def gather_subscription_chapter_text(
    document: dict[str, Any],
    windows: dict[str, str],
) -> str:
    chunks: list[str] = []
    outline_text = gather_outline_chapter_text(document, "subscription").strip()
    if outline_text:
        chunks.append(outline_text)
    else:
        part = (windows.get("subscription") or "").strip()
        if part:
            chunks.append(part)
    _append_paragraph_blocks(document, _SUBSCRIPTION_BLOCK_MARKERS, chunks)
    return "\n".join(chunks)


def gather_subscription_rules_text(
    document: dict[str, Any],
    windows: dict[str, str],
) -> str:
    chunks: list[str] = []
    raising = gather_raising_fee_text(document, windows)
    subscription = gather_subscription_chapter_text(document, windows)
    if raising:
        chunks.append(raising)
    if subscription:
        chunks.append(subscription)
    _append_paragraph_blocks(document, _COMBINED_RULE_MARKERS, chunks)
    return "\n".join(chunks)
