"""Resolve contract table blocks from parse_json for verification display."""

from __future__ import annotations

from typing import Any

_SKIP_ROW_KEYS = frozenset({"snippet", "_snippet", "摘录", "block_id", "source", "section_id"})

_SECTION_TABLE_HINTS: dict[str, tuple[str, ...]] = {
    "fee-rates": (
        "年管理费率",
        "管理费率",
        "托管费",
        "运营费",
        "份额分类",
        "基金服务费",
        "销售服务费",
        "费率",
    ),
    "subscription-fee-rates": ("申购", "赎回", "认购", "申赎", "费率"),
    "share-classes": ("份额", "分级", "基金代码", "基金简称", "A类", "B类"),
    "lock-periods": ("锁定", "封闭期", "份额锁定"),
    "product-elements": ("份额分类", "费率", "申购", "赎回"),
}


def _normalize_rows(rows: list[Any]) -> list[list[str]]:
    out: list[list[str]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        cells = [str(c or "").strip() for c in row]
        if any(cells):
            out.append(cells)
    return out


def block_by_id(parse_json: dict | None, block_id: str | None) -> dict[str, Any] | None:
    if not block_id or not parse_json:
        return None
    for block in parse_json.get("blocks") or []:
        if isinstance(block, dict) and block.get("id") == block_id:
            return block
    return None


def table_rows_from_block(block: dict[str, Any] | None) -> list[list[str]] | None:
    if not block or block.get("type") != "table":
        return None
    rows = _normalize_rows(block.get("rows") or [])
    return rows if len(rows) >= 1 else None


def table_rows_from_block_id(
    parse_json: dict | None,
    block_id: str | None,
) -> list[list[str]] | None:
    return table_rows_from_block(block_by_id(parse_json, block_id))


def _table_flat(rows: list[list[str]]) -> str:
    return "\n".join("\t".join(c for c in row if c) for row in rows)


def _score_table(
    rows: list[list[str]],
    needles: list[str],
    hints: tuple[str, ...],
) -> int:
    flat = _table_flat(rows)
    if not flat.strip():
        return -1
    score = 0
    matched_needles = 0
    for needle in needles:
        n = needle.strip()
        if len(n) < 2:
            continue
        if n in flat or any(n in cell for row in rows for cell in row):
            score += 12
            matched_needles += 1
    if needles and matched_needles == 0:
        return -1
    for hint in hints:
        if hint in flat:
            score += 4
    # Prefer compact tables when multiple match
    score -= min(len(rows), 40)
    return score


def find_best_table_for_value(
    parse_json: dict | None,
    value: str | None,
    *,
    hints: tuple[str, ...] = (),
    min_needle_len: int = 2,
) -> list[list[str]] | None:
    needle = (value or "").strip()
    if len(needle) < min_needle_len:
        return None
    return find_best_table_for_needles(parse_json, [needle], hints=hints)


def find_best_table_for_needles(
    parse_json: dict | None,
    needles: list[str],
    *,
    hints: tuple[str, ...] = (),
) -> list[list[str]] | None:
    if not parse_json:
        return None
    cleaned = [n.strip() for n in needles if n and len(n.strip()) >= 2]
    if not cleaned:
        return None
    best: list[list[str]] | None = None
    best_score = -1
    for block in parse_json.get("blocks") or []:
        if not isinstance(block, dict) or block.get("type") != "table":
            continue
        rows = table_rows_from_block(block)
        if not rows:
            continue
        score = _score_table(rows, cleaned, hints)
        if score > best_score:
            best_score = score
            best = rows
    return best


def row_needle_values(row: dict[str, Any]) -> list[str]:
    vals: list[str] = []
    for key, val in row.items():
        if key in _SKIP_ROW_KEYS:
            continue
        text = str(val or "").strip()
        if len(text) >= 2:
            vals.append(text)
    vals.sort(key=len, reverse=True)
    return vals


def resolve_excerpt_table(
    raw: dict[str, Any] | None,
    parse_json: dict | None,
    *,
    section: str | None = None,
    value: str | None = None,
) -> dict[str, list[list[str]]] | None:
    """Return {rows: ...} when evidence comes from a contract table block."""
    hints = _SECTION_TABLE_HINTS.get(section or "", ())
    if raw and isinstance(raw, dict):
        block_id = raw.get("block_id")
        from_id = table_rows_from_block_id(parse_json, str(block_id) if block_id else None)
        if from_id:
            return {"rows": from_id}
        needles = row_needle_values(raw)
        if value and value.strip():
            needles = [value.strip(), *needles]
        found = find_best_table_for_needles(parse_json, needles, hints=hints)
        if found:
            return {"rows": found}
    if value:
        found = find_best_table_for_value(parse_json, value, hints=hints)
        if found:
            return {"rows": found}
    return None
