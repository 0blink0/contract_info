"""Gather chapter text for LLM prompts (no field extraction)."""

from __future__ import annotations

from typing import Any

from backend.app.extract.section_windows import gather_outline_chapter_text

_FEE_SOURCE_MARKERS = (
    "基金管理费",
    "管理费率",
    "收取管理费",
    "基金的托管费",
    "托管费",
    "运营服务费",
    "基金服务费",
    "不收取管理费",
    "年费率",
    "外包服务费",
    "销售服务费率",
    "投资顾问费",
)

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


def gather_fee_source_text(
    fees_text: str,
    document: dict[str, Any] | None = None,
) -> str:
    parts: list[str] = []
    seen: set[str] = set()

    def _add(t: str) -> None:
        s = t.strip()
        if s and s not in seen:
            parts.append(s)
            seen.add(s)

    if document:
        outline_fees = gather_outline_chapter_text(document, "fees").strip()
        if outline_fees:
            _add(outline_fees)

    _add(fees_text)

    if document:
        for block in document.get("blocks") or []:
            if block.get("type") not in ("paragraph", "table"):
                continue
            if block.get("type") == "table":
                rows = block.get("rows") or []
                text = "\n".join("\t".join(str(c) for c in row) for row in rows)
            else:
                text = str(block.get("text") or "")
            if text.strip() and any(m in text for m in _FEE_SOURCE_MARKERS):
                _add(text)

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
