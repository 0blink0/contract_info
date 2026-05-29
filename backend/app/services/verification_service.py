"""Build per-table verification rows from extraction (and optional validation overlay)."""

from __future__ import annotations

from typing import Any

from backend.app.api.schemas import PreviewSection
from backend.app.export.column_map import (
    template_header_for_fee_key,
    template_header_for_subscription_key,
)
from backend.app.services.preview_service import PREVIEW_STATUSES, SNIPPET_DISPLAY, build_job_preview
from backend.app.validate.evidence import resolve_evidence_text
from backend.app.validate.field_labels import label_for_validation_field

PAGE_UNAVAILABLE_NOTE = "页码暂未解析"

_SKIP_PREVIEW_KEYS = frozenset({"snippet", "_snippet", "摘录", "block_id"})


def _page_for_block(block_id: str | None, parse_json: dict | None) -> int | None:
    if not block_id or not parse_json:
        return None
    blocks = parse_json.get("blocks") or []
    for block in blocks:
        if not isinstance(block, dict) or block.get("id") != block_id:
            continue
        for key in ("page", "page_index", "page_no"):
            raw = block.get(key)
            if raw is not None:
                try:
                    return int(raw)
                except (TypeError, ValueError):
                    continue
    return None


def _snippet_and_block(raw: dict) -> tuple[str | None, str | None]:
    snippet = raw.get("snippet") or raw.get("_snippet") or raw.get("摘录")
    block_id = raw.get("block_id")
    if snippet is None and isinstance(raw.get("value"), dict):
        nested = raw["value"]
        snippet = nested.get("snippet")
        block_id = block_id or nested.get("block_id")
    return (
        str(snippet).strip() if snippet else None,
        str(block_id).strip() if block_id else None,
    )


def _overlay_validation(
    rows: list[dict[str, Any]],
    validation_result: dict | None,
) -> None:
    if not validation_result or not isinstance(validation_result, dict):
        return
    by_field = {
        str(item.get("field") or ""): item
        for item in (validation_result.get("items") or [])
        if isinstance(item, dict)
    }
    for row in rows:
        item = by_field.get(row.get("field") or "")
        if not item:
            continue
        row["validation_status"] = item.get("status")
        row["validation_reason"] = item.get("reason")


def _row_template(
    *,
    field: str,
    field_label: str,
    value: str | None,
    excerpt: str | None,
    page_no: int | None = None,
) -> dict[str, Any]:
    return {
        "field": field,
        "field_label": field_label,
        "value": value,
        "page_no": page_no,
        "page_no_note": None if page_no is not None else PAGE_UNAVAILABLE_NOTE,
        "excerpt": excerpt,
    }


def _verification_rows_from_preview(
    preview: dict[str, Any],
    table_key: PreviewSection,
) -> list[dict[str, Any]]:
    """When extraction JSON is empty but exported xlsx preview exists, still show核对行."""
    rows: list[dict[str, Any]] = []

    if table_key == "product-elements":
        for item in preview.get("product_rows") or []:
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "").strip()
            if not field:
                continue
            val = item.get("value")
            value = str(val).strip() if val is not None else None
            rows.append(
                _row_template(
                    field=field,
                    field_label=field,
                    value=value or None,
                    excerpt=None,
                )
            )
        return rows

    columns_key, rows_key = {
        "fee-rates": ("fee_columns", "fee_rows"),
        "lock-periods": ("lock_columns", "lock_rows"),
        "share-classes": ("share_columns", "share_rows"),
        "subscription-fee-rates": ("subscription_columns", "subscription_rows"),
    }[table_key]
    columns = list(preview.get(columns_key) or [])
    data_rows = preview.get(rows_key) or []
    for i, row in enumerate(data_rows):
        if not isinstance(row, dict):
            continue
        excerpt_raw = row.get(SNIPPET_DISPLAY)
        excerpt = str(excerpt_raw).strip() if excerpt_raw else None
        for col, val in row.items():
            if col in _SKIP_PREVIEW_KEYS or col == SNIPPET_DISPLAY:
                continue
            if col not in columns and columns:
                continue
            text = str(val).strip() if val is not None else None
            rows.append(
                _row_template(
                    field=f"{rows_key}[{i}].{col}",
                    field_label=str(col),
                    value=text or None,
                    excerpt=excerpt,
                )
            )
    return rows


def build_verification_rows(record, table_key: PreviewSection) -> list[dict[str, Any]]:
    extraction = record.extraction_result or {}
    parse_json = record.parse_json or {}
    rows: list[dict[str, Any]] = []

    if table_key == "product-elements":
        elements = extraction.get("product_elements") or {}
        if isinstance(elements, dict):
            for field_name, raw in elements.items():
                if not isinstance(raw, dict):
                    val = str(raw).strip() if raw is not None else ""
                    snippet, block_id = None, None
                else:
                    val = str(raw.get("value") or "").strip()
                    snippet, block_id = _snippet_and_block(raw)
                excerpt = resolve_evidence_text(snippet, block_id, parse_json)
                page_no = _page_for_block(block_id, parse_json)
                rows.append(
                    {
                        "field": field_name,
                        "field_label": field_name,
                        "value": val or None,
                        "page_no": page_no,
                        "page_no_note": None if page_no is not None else PAGE_UNAVAILABLE_NOTE,
                        "excerpt": excerpt,
                    }
                )
    elif table_key == "fee-rates":
        fee_list = extraction.get("fee_rates") or []
        for i, row in enumerate(fee_list):
            if not isinstance(row, dict):
                continue
            snippet, block_id = _snippet_and_block(row)
            excerpt = resolve_evidence_text(snippet, block_id, parse_json)
            page_no = _page_for_block(block_id, parse_json)
            for key, val in row.items():
                if key in ("snippet", "_snippet", "摘录", "block_id"):
                    continue
                label = template_header_for_fee_key(key)
                field_path = f"fee_rates[{i}].{key}"
                rows.append(
                    {
                        "field": field_path,
                        "field_label": label,
                        "value": str(val).strip() if val is not None else None,
                        "page_no": page_no,
                        "page_no_note": None if page_no is not None else PAGE_UNAVAILABLE_NOTE,
                        "excerpt": excerpt,
                    }
                )
    elif table_key == "lock-periods":
        lock_list = extraction.get("lock_periods") or []
        for i, row in enumerate(lock_list):
            if not isinstance(row, dict):
                continue
            snippet, block_id = _snippet_and_block(row)
            excerpt = resolve_evidence_text(snippet, block_id, parse_json)
            page_no = _page_for_block(block_id, parse_json)
            for key, val in row.items():
                if key in ("snippet", "_snippet", "摘录", "block_id"):
                    continue
                field_path = f"lock_periods[{i}].{key}"
                rows.append(
                    {
                        "field": field_path,
                        "field_label": str(key),
                        "value": str(val).strip() if val is not None else None,
                        "page_no": page_no,
                        "page_no_note": None if page_no is not None else PAGE_UNAVAILABLE_NOTE,
                        "excerpt": excerpt,
                    }
                )
    elif table_key == "share-classes":
        share_list = extraction.get("share_classes") or []
        for i, row in enumerate(share_list):
            if not isinstance(row, dict):
                continue
            snippet, block_id = _snippet_and_block(row)
            excerpt = resolve_evidence_text(snippet, block_id, parse_json)
            page_no = _page_for_block(block_id, parse_json)
            for key, val in row.items():
                if key in ("snippet", "_snippet", "摘录", "block_id"):
                    continue
                field_path = f"share_classes[{i}].{key}"
                rows.append(
                    {
                        "field": field_path,
                        "field_label": str(key),
                        "value": str(val).strip() if val is not None else None,
                        "page_no": page_no,
                        "page_no_note": None if page_no is not None else PAGE_UNAVAILABLE_NOTE,
                        "excerpt": excerpt,
                    }
                )
    elif table_key == "subscription-fee-rates":
        sub_list = extraction.get("subscription_fees") or []
        for i, row in enumerate(sub_list):
            if not isinstance(row, dict):
                continue
            snippet, block_id = _snippet_and_block(row)
            excerpt = resolve_evidence_text(snippet, block_id, parse_json)
            page_no = _page_for_block(block_id, parse_json)
            for key, val in row.items():
                if key in ("snippet", "_snippet", "摘录", "block_id"):
                    continue
                label = template_header_for_subscription_key(key)
                field_path = f"subscription_fees[{i}].{key}"
                rows.append(
                    {
                        "field": field_path,
                        "field_label": label,
                        "value": str(val).strip() if val is not None else None,
                        "page_no": page_no,
                        "page_no_note": None if page_no is not None else PAGE_UNAVAILABLE_NOTE,
                        "excerpt": excerpt,
                    }
                )

    if not rows and getattr(record, "status", None) in PREVIEW_STATUSES:
        try:
            preview = build_job_preview(record)
        except ValueError:
            preview = None
        if preview:
            rows = _verification_rows_from_preview(preview, table_key)

    _overlay_validation(rows, getattr(record, "validation_result", None))
    for row in rows:
        if not row.get("field_label"):
            row["field_label"] = label_for_validation_field(
                str(row.get("field") or ""),
                extraction,
            )
    return rows


def page_no_available(rows: list[dict[str, Any]]) -> bool:
    return any(r.get("page_no") is not None for r in rows)
