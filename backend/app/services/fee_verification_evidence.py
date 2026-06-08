"""Fee-rate verification: share-classification tables + LLM-extracted narrative per 运营费类型."""

from __future__ import annotations

from typing import Any

from backend.app.services.parse_block_tables import (
    _normalize_rows,
    _table_flat,
    table_rows_from_block,
    table_rows_from_block_id,
)

_SHARE_TABLE_MARKERS = ("认购费率", "申购费率", "分类标准")
_FEE_TYPE_SHARE_ROW_LABELS: dict[str, tuple[str, ...]] = {
    "管理费": ("年管理费率", "管理费率"),
    "销售服务费": ("销售服务费率",),
    "基金服务费": ("基金服务费", "外包服务费", "运营服务费"),
    "投资顾问费": ("投资顾问费", "顾问费"),
    # 托管费通常不在份额分类表，走费用章节叙述
}

# Aliases so that document-specific terms (运营服务费 / 外包服务费) resolve to canonical key.
_FEE_TYPE_CANONICAL: dict[str, str] = {
    "运营服务费": "基金服务费",
    "外包服务费": "基金服务费",
    "运营外包服务费": "基金服务费",
}
_SUBSCRIPTION_TABLE_MARKERS = ("认购费率", "申购费率", "赎回费率", "申赎费率")


def _is_share_classification_table(rows: list[list[str]]) -> bool:
    flat = _table_flat(rows)
    hits = sum(1 for m in _SHARE_TABLE_MARKERS if m in flat)
    return hits >= 2


def _is_subscription_rate_table(rows: list[list[str]]) -> bool:
    flat = _table_flat(rows)
    return sum(1 for m in _SUBSCRIPTION_TABLE_MARKERS if m in flat) >= 2 and not _is_share_classification_table(
        rows
    )



def find_share_table_for_fee_type(
    parse_json: dict | None,
    fee_type: str,
) -> list[list[str]] | None:
    canonical = _FEE_TYPE_CANONICAL.get(fee_type, fee_type)
    row_labels = _FEE_TYPE_SHARE_ROW_LABELS.get(canonical, ())
    if not row_labels or not parse_json:
        return None
    for block in parse_json.get("blocks") or []:
        if not isinstance(block, dict) or block.get("type") != "table":
            continue
        rows = table_rows_from_block(block)
        if not rows or not _is_share_classification_table(rows):
            continue
        flat = _table_flat(rows)
        if any(label in flat for label in row_labels):
            return rows
    return None


def find_fees_chapter_table_for_fee_type(
    parse_json: dict | None,
    fee_type: str,
) -> list[list[str]] | None:
    if not parse_json or not fee_type:
        return None
    canonical = _FEE_TYPE_CANONICAL.get(fee_type, fee_type)
    best: list[list[str]] | None = None
    best_score = -1
    for block in parse_json.get("blocks") or []:
        if not isinstance(block, dict) or block.get("type") != "table":
            continue
        rows = table_rows_from_block(block)
        if not rows:
            continue
        if _is_share_classification_table(rows) or _is_subscription_rate_table(rows):
            continue
        flat = _table_flat(rows)
        if fee_type not in flat and canonical not in flat and not any(
            label in flat for label in _FEE_TYPE_SHARE_ROW_LABELS.get(canonical, ())
        ):
            continue
        score = 10 + flat.count(fee_type) + flat.count(canonical)
        if score > best_score:
            best_score = score
            best = rows
    return best


def resolve_fee_row_verification_evidence(
    row: dict[str, Any],
    parse_json: dict | None,
) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    """
    Return (narrative excerpt, capture_source, excerpt_tables with captions).
    Tables: share-classification (when row applies) + fees-chapter tables; narrative in excerpt.
    """
    fee_type = str(row.get("运营费类型") or "").strip()
    tables: list[dict[str, Any]] = []
    seen_flat: set[str] = set()

    def _add_table(rows: list[list[str]], caption: str) -> None:
        flat = _table_flat(rows)
        if not flat or flat in seen_flat:
            return
        seen_flat.add(flat)
        tables.append({"rows": rows, "caption": caption})

    block_id = row.get("block_id")
    from_id = table_rows_from_block_id(parse_json, str(block_id) if block_id else None)
    canonical_fee_type = _FEE_TYPE_CANONICAL.get(fee_type, fee_type)
    if from_id:
        if _is_share_classification_table(from_id) and canonical_fee_type in _FEE_TYPE_SHARE_ROW_LABELS:
            _add_table(from_id, "份额分类表")
        elif not _is_subscription_rate_table(from_id):
            _add_table(from_id, "费用章节表格")

    share = find_share_table_for_fee_type(parse_json, fee_type)
    if share:
        _add_table(share, "份额分类表")

    fees_table = find_fees_chapter_table_for_fee_type(parse_json, fee_type)
    if fees_table:
        _add_table(fees_table, "费用与税收 · 相关表格")

    row_snip = str(row.get("snippet") or row.get("_snippet") or "").strip()
    narrative: str | None = row_snip if row_snip else None
    excerpt: str | None = None
    if narrative:
        excerpt = f"【费用与税收 · {fee_type}】\n{narrative}"

    if tables and excerpt:
        source = "table+narrative"
    elif tables:
        source = "table"
    elif excerpt:
        source = "narrative"
    else:
        source = None

    return excerpt, source, tables
