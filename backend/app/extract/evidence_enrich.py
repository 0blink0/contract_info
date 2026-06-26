"""Backfill contract excerpts (snippet / block_id) when extraction omitted evidence."""

from __future__ import annotations

import re
from typing import Any

from backend.app.extract.field_catalog import FIXED_PRODUCT_VALUES
from backend.app.extract.field_snippets import extract_section_body, resolve_field_snippet
from backend.app.extract.schemas import ExtractionResult, FieldValue
from backend.app.extract.section_windows import build_section_windows
from backend.app.extract.text_limits import excerpt_for_display

MIN_SNIPPET_LEN = 8

# Preferred section windows to search per field (first hit wins).
_FIELD_WINDOWS: dict[str, tuple[str, ...]] = {
    "产品类型（协会）": ("investment",),  # 必须从投资范围/限制章节取证，禁止从basic的「基金的类型」标签取
    "管理类型": ("basic", "cover_parties"),
    "份额结构": ("basic", "subscription"),
    "结构类型": ("basic",),
    "产品分类": ("basic", "investment"),
    "是否封闭": ("subscription", "basic"),
    "封闭期": ("subscription", "basic"),
    "封闭方式": ("subscription",),
    "冷静期回访": ("raising", "subscription"),
    "首次申购起点": ("subscription", "raising"),
    "追加起点": ("subscription", "raising"),
    "最低持有类型": ("subscription", "raising"),
    "最低持有数量": ("subscription", "raising"),
    "计费基准": ("fees", "subscription"),
    "计费频率": ("fees",),
    "基金类型": ("basic", "cover_parties"),
}

_DEFAULT_WINDOWS = (
    "basic",
    "subscription",
    "investment",
    "fees",
    "raising",
    "distribution",
    "risk",
    "cover_parties",
    "establish",
)

_LIST_TABLE_WINDOWS: dict[str, tuple[str, ...]] = {
    "lock_periods": ("subscription", "basic"),
    "share_classes": ("subscription", "basic"),
}

_SHARE_CLASS_IDENTITY_FIELDS = frozenset(
    {
        "基金全称",
        "基金代码",
        "分级份额名称",
        "分级份额简称",
        "分级份额代码",
        "代码类型",
        "分级类型",
        "实际成立日期",
        "投资起始日",
    }
)
_SHARE_CLASS_RISK_FIELDS = frozenset({"预警线", "止损线"})


def resolve_share_class_cell_snippet(
    field_key: str,
    value: str | None,
    row: dict[str, Any],
    windows: dict[str, str],
    document: dict[str, Any],
) -> str | None:
    """Per-column excerpt for 分级份额核对；预警/止损不得复用份额分类行摘录。"""
    val = _stringify(value)
    if field_key in _SHARE_CLASS_RISK_FIELDS:
        llm_snip = _stringify(row.get("预警止损原文"))
        if llm_snip:
            return excerpt_for_display(llm_snip)
        # 回退：从 investment 窗口里搜索含该值的句子
        inv_text = windows.get("investment") or ""
        if inv_text and val:
            around = _snippet_around_value(inv_text, val)
            if len(around.strip()) >= MIN_SNIPPET_LEN:
                return around
        return None

    if field_key in _SHARE_CLASS_IDENTITY_FIELDS:
        row_snip = _stringify(row.get("snippet") or row.get("_snippet"))
        if row_snip:
            return row_snip
        for wkey in ("basic", "subscription"):
            text = windows.get(wkey) or ""
            if not text or not val:
                continue
            around = _snippet_around_value(text, val)
            if len(around.strip()) >= MIN_SNIPPET_LEN:
                return around
    return None


def _stringify(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _has_usable_snippet(fv: FieldValue | dict[str, Any]) -> bool:
    if isinstance(fv, dict):
        snip = _stringify(fv.get("snippet") or fv.get("_snippet"))
    else:
        snip = _stringify(fv.snippet)
    return len(snip) >= MIN_SNIPPET_LEN


def document_plain_text(document: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in document.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "table":
            for row in block.get("rows") or []:
                if isinstance(row, list):
                    parts.append(" ".join(str(c) for c in row if c))
        else:
            text = block.get("text")
            if text:
                parts.append(str(text).strip())
    return "\n".join(p for p in parts if p)


def _norm(s: str) -> str:
    """Remove whitespace — collapses PDF-artifact spaces like 'A 类' → 'A类'."""
    return re.sub(r"\s+", "", s)


def find_block_id_for_text(document: dict[str, Any], needle: str) -> str | None:
    needle = needle.strip()
    if len(needle) < 2:
        return None
    probe = needle[: min(80, len(needle))]
    probe_norm = _norm(probe)
    for block in document.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        bid = block.get("id")
        if not bid:
            continue
        if block.get("type") == "table":
            rows = block.get("rows") or []
            joined = "\n".join(
                " ".join(str(c) for c in row) for row in rows if isinstance(row, list)
            )
            joined_norm = _norm(joined)
            if probe in joined or probe_norm in joined_norm:
                return str(bid)
            # Reverse: block content is a prefix of probe (probe spans multiple blocks)
            if len(joined_norm) >= 15 and joined_norm[:40] in probe_norm:
                return str(bid)
        else:
            text = str(block.get("text") or "")
            text_norm = _norm(text)
            if probe in text or probe_norm in text_norm:
                return str(bid)
            # Reverse: block text is a leading substring of probe (probe spans multiple blocks)
            if len(text_norm) >= 15 and text_norm[:40] in probe_norm:
                return str(bid)
    return None


def _snippet_around_value(text: str, value: str) -> str:
    val = value.strip()
    if not val or val not in text:
        return ""
    pos = text.find(val)
    start = max(0, pos - 80)
    end = min(len(text), pos + len(val) + 160)
    return excerpt_for_display(text[start:end].strip())


def resolve_snippet_for_field(
    field_name: str,
    value: str,
    windows: dict[str, str],
    document: dict[str, Any],
) -> tuple[str | None, str | None]:
    if not value:
        return None, None

    keys = _FIELD_WINDOWS.get(field_name, _DEFAULT_WINDOWS)
    for wkey in keys:
        text = windows.get(wkey) or ""
        if not text.strip():
            continue
        snip = resolve_field_snippet(field_name, text, value)
        if len(snip.strip()) >= MIN_SNIPPET_LEN:
            bid = find_block_id_for_text(document, snip) or find_block_id_for_text(
                document, value
            )
            return snip.strip(), bid

    full_text = document_plain_text(document)
    if full_text:
        snip = resolve_field_snippet(field_name, full_text, value)
        if len(snip.strip()) >= MIN_SNIPPET_LEN:
            bid = find_block_id_for_text(document, snip) or find_block_id_for_text(
                document, value
            )
            return snip.strip(), bid
        short = _snippet_around_value(full_text, value)
        if len(short) >= MIN_SNIPPET_LEN:
            bid = find_block_id_for_text(document, short) or find_block_id_for_text(
                document, value
            )
            return short, bid

    # Fixed catalog values: still attach nearby explanatory text if present.
    if field_name in FIXED_PRODUCT_VALUES and value in full_text:
        short = _snippet_around_value(full_text, value)
        if short:
            return short, find_block_id_for_text(document, value)

    return None, None


def enrich_field_value(
    fv: FieldValue | dict[str, Any] | None,
    field_name: str,
    windows: dict[str, str],
    document: dict[str, Any],
) -> FieldValue | dict[str, Any] | None:
    if fv is None:
        return None
    if isinstance(fv, dict):
        if _has_usable_snippet(fv):
            return fv
        value = _stringify(fv.get("value"))
        snip, bid = resolve_snippet_for_field(field_name, value, windows, document)
        if not snip:
            return fv
        updated = dict(fv)
        updated["snippet"] = snip
        if bid and not updated.get("block_id"):
            updated["block_id"] = bid
        return updated

    if _has_usable_snippet(fv):
        return fv
    value = _stringify(fv.value)
    snip, bid = resolve_snippet_for_field(field_name, value, windows, document)
    if not snip:
        return fv
    return fv.model_copy(
        update={
            "snippet": snip,
            "block_id": bid or fv.block_id,
        }
    )


def _row_primary_value(row: dict[str, Any]) -> str:
    skip = frozenset({"snippet", "_snippet", "摘录", "block_id", "section_id"})
    best = ""
    for key, val in row.items():
        if key in skip:
            continue
        text = _stringify(val)
        if len(text) > len(best):
            best = text
    return best



def enrich_list_row(
    row: dict[str, Any],
    table_key: str,
    windows: dict[str, str],
    document: dict[str, Any],
) -> dict[str, Any]:
    if row.get("snippet") or row.get("_snippet"):
        return row

    value = _row_primary_value(row)
    if not value:
        return row
    wkeys = _LIST_TABLE_WINDOWS.get(table_key, _DEFAULT_WINDOWS)
    snip, bid = resolve_snippet_for_field("", value, windows, document)
    if not snip:
        for wkey in wkeys:
            text = windows.get(wkey) or ""
            snip = resolve_field_snippet("", text, value)
            if len(snip.strip()) >= MIN_SNIPPET_LEN:
                bid = find_block_id_for_text(document, snip) or find_block_id_for_text(
                    document, value
                )
                break
            short = _snippet_around_value(text, value)
            if len(short) >= MIN_SNIPPET_LEN:
                snip = short
                bid = find_block_id_for_text(document, value)
                break
    if not snip:
        return row
    updated = dict(row)
    updated["snippet"] = snip
    if bid and not updated.get("block_id"):
        updated["block_id"] = bid
    return updated


def enrich_extraction_dict(
    extraction: dict[str, Any],
    document: dict[str, Any] | None,
) -> dict[str, Any]:
    """Mutate extraction_result dict in place; return same dict for chaining."""
    if not extraction:
        return extraction
    doc = document if isinstance(document, dict) else {}
    windows: dict[str, str] = {}
    if doc.get("blocks") is not None:
        windows, _warnings = build_section_windows(doc)

    pe = extraction.get("product_elements")
    if isinstance(pe, dict):
        for name, raw in list(pe.items()):
            pe[name] = enrich_field_value(raw, str(name), windows, doc)

    for table_key in ("lock_periods", "share_classes"):
        rows = extraction.get(table_key)
        if not isinstance(rows, list):
            continue
        extraction[table_key] = [
            enrich_list_row(r, table_key, windows, doc) if isinstance(r, dict) else r
            for r in rows
        ]

    # Backfill block_id for fee rows: LLM already provides 原文/snippet, just locate the block.
    for table_key in ("fee_rates", "subscription_fees"):
        rows = extraction.get(table_key)
        if not isinstance(rows, list):
            continue
        new_rows = []
        for r in rows:
            if not isinstance(r, dict) or r.get("block_id"):
                new_rows.append(r)
                continue
            anchor = r.get("原文") or r.get("snippet") or r.get("_snippet") or ""
            if anchor:
                bid = find_block_id_for_text(doc, anchor)
                if not bid:
                    # 原文 may span multiple blocks; try each sentence separately
                    for seg in re.split(r"[。；\n]", anchor):
                        seg = seg.strip()
                        if len(seg) >= 10:
                            bid = find_block_id_for_text(doc, seg)
                            if bid:
                                break
                if bid:
                    r = {**r, "block_id": bid}
            new_rows.append(r)
        extraction[table_key] = new_rows

    return extraction


def enrich_extraction_result(
    result: ExtractionResult,
    document: dict[str, Any],
) -> ExtractionResult:
    data = result.model_dump(by_alias=True)
    enrich_extraction_dict(data, document)
    return ExtractionResult.model_validate(data)
