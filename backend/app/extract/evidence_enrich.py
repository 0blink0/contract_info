"""Backfill contract excerpts (snippet / block_id) when extraction omitted evidence."""

from __future__ import annotations

import re
from typing import Any

from backend.app.extract.field_catalog import FIXED_PRODUCT_VALUES
from backend.app.extract.field_snippets import resolve_field_snippet
from backend.app.extract.schemas import ExtractionResult, FieldValue
from backend.app.extract.section_windows import build_section_windows
from backend.app.extract.text_limits import excerpt_for_display

MIN_SNIPPET_LEN = 8

# Preferred section windows to search per field (first hit wins).
_FIELD_WINDOWS: dict[str, tuple[str, ...]] = {
    "运作方式": ("basic", "subscription", "investment"),
    "产品存续期": ("basic", "establish"),
    "管理类型": ("basic", "cover_parties"),
    "份额结构": ("basic", "subscription"),
    "结构类型": ("basic",),
    "产品分类": ("basic", "investment"),
    "默认分红方式": ("distribution", "subscription"),
    "是否封闭": ("subscription", "basic"),
    "封闭期": ("subscription", "basic"),
    "封闭方式": ("subscription",),
    "是否支持基金转换": ("subscription",),
    "基金转换方式": ("subscription",),
    "基金转换限制": ("subscription",),
    "是否支持金额赎回": ("subscription",),
    "金额赎回方式": ("subscription",),
    "冷静期回访": ("raising", "subscription"),
    "首次申购起点": ("subscription", "raising"),
    "追加起点": ("subscription", "raising"),
    "最低持有类型": ("subscription", "raising"),
    "最低持有数量": ("subscription", "raising"),
    "交易确认规则": ("subscription",),
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
    "fee_rates": ("fees", "subscription", "basic"),
    "lock_periods": ("subscription", "basic"),
    "share_classes": ("subscription", "basic"),
    "subscription_fees": ("subscription", "fees", "raising"),
}


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


def find_block_id_for_text(document: dict[str, Any], needle: str) -> str | None:
    needle = needle.strip()
    if len(needle) < 2:
        return None
    probe = needle[: min(80, len(needle))]
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
            if probe in joined:
                return str(bid)
        else:
            text = str(block.get("text") or "")
            if probe in text:
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


_FEE_TYPE_SECTION_LABELS: dict[str, list[str]] = {
    "管理费": ["基金的管理费", "管理费"],
    "托管费": ["基金的托管费", "托管费"],
    "基金服务费": ["基金的运营服务费", "运营服务费", "基金服务费", "外包服务费"],
    "销售服务费": ["基金的销售服务费", "销售服务费"],
    "投资顾问费": ["基金的投资顾问费", "投资顾问费"],
}


def _fee_rate_snippet(
    row: dict[str, Any],
    fees_window: str,
    document: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Find the specific fee-type subsection in the (二) 费用计提 section."""
    fee_type = _stringify(row.get("运营费类型") or "")
    if not fee_type or not fees_window:
        return None, None

    # Narrow search to the 计提 subsection (二) when present
    idx = fees_window.find("（二）")
    search_area = fees_window[idx:] if idx >= 0 else fees_window

    labels = _FEE_TYPE_SECTION_LABELS.get(fee_type, [fee_type])
    for label in labels:
        pos = search_area.find(label)
        if pos < 0:
            continue
        tail = search_area[pos:]
        stop = re.search(r"\n\d+[、.]|\n（[二三四五六七八九十]）", tail[len(label) :])
        end = len(label) + (stop.start() if stop else min(400, len(tail) - len(label)))
        chunk = tail[:end].strip()
        if len(chunk) < 8:
            continue
        snip = excerpt_for_display(chunk)
        bid = find_block_id_for_text(document, chunk[:60])
        return snip, bid

    return None, None


def enrich_list_row(
    row: dict[str, Any],
    table_key: str,
    windows: dict[str, str],
    document: dict[str, Any],
) -> dict[str, Any]:
    if row.get("snippet") or row.get("_snippet"):
        return row

    # Fee-rate rows: locate the specific fee-type subsection rather than
    # searching by primary value (which is often the fund name and matches
    # the chapter preamble instead of the per-fee paragraph).
    if table_key == "fee_rates":
        fees_text = windows.get("fees") or ""
        snip, bid = _fee_rate_snippet(row, fees_text, document)
        if snip:
            updated = dict(row)
            updated["snippet"] = snip
            if bid and not updated.get("block_id"):
                updated["block_id"] = bid
            return updated

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

    for table_key in ("fee_rates", "lock_periods", "share_classes", "subscription_fees"):
        rows = extraction.get(table_key)
        if not isinstance(rows, list):
            continue
        extraction[table_key] = [
            enrich_list_row(r, table_key, windows, doc) if isinstance(r, dict) else r
            for r in rows
        ]
    return extraction


def enrich_extraction_result(
    result: ExtractionResult,
    document: dict[str, Any],
) -> ExtractionResult:
    data = result.model_dump(by_alias=True)
    enrich_extraction_dict(data, document)
    return ExtractionResult.model_validate(data)
