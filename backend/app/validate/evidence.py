from __future__ import annotations

from typing import Any

from backend.app.validate.schemas import ValidationCandidate

MIN_SNIPPET_LEN = 20
PARTY_FIELDS = frozenset({"管理人", "托管人", "投资顾问", "外包机构"})
ROW_SNIPPET_KEYS = ("snippet", "_snippet", "摘录")


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _block_text(block_id: str | None, parse_json: dict) -> str | None:
    if not block_id:
        return None
    blocks = parse_json.get("blocks") or []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("id") != block_id:
            continue
        text = (block.get("text") or "").strip()
        if text:
            return text
        rows = block.get("rows")
        if isinstance(rows, list):
            parts: list[str] = []
            for row in rows:
                if isinstance(row, list):
                    parts.append(" ".join(str(c) for c in row if c))
            joined = " ".join(parts).strip()
            if joined:
                return joined
    return None


def resolve_evidence_text(
    snippet: str | None,
    block_id: str | None,
    parse_json: dict,
) -> str | None:
    snip = (snippet or "").strip()
    if len(snip) >= MIN_SNIPPET_LEN:
        return snip
    from_block = _block_text(block_id, parse_json)
    if from_block:
        return from_block
    if snip:
        return snip
    return None


def _nested_value(obj: dict | None, dotted: str) -> str | None:
    if not obj or not dotted:
        return None
    cur: Any = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return _stringify(cur)


def _row_snippet(row: dict) -> str | None:
    for key in ROW_SNIPPET_KEYS:
        text = _stringify(row.get(key))
        if text:
            return text
    return None


def _add_candidate(
    out: list[ValidationCandidate],
    seen: set[str],
    *,
    field: str,
    value: str | None,
    evidence_text: str | None,
    party: bool = False,
) -> None:
    if not value or not evidence_text:
        return
    if field in seen:
        return
    seen.add(field)
    out.append(
        ValidationCandidate(
            field=field,
            value=value,
            evidence_text=evidence_text,
            party=party or field in PARTY_FIELDS,
        )
    )


def _collect_product_elements(
    extraction_result: dict,
    parse_json: dict,
    out: list[ValidationCandidate],
    seen: set[str],
) -> None:
    elements = extraction_result.get("product_elements") or {}
    if not isinstance(elements, dict):
        return
    for name, raw in elements.items():
        if not isinstance(raw, dict):
            continue
        value = _stringify(raw.get("value"))
        snippet = raw.get("snippet")
        block_id = raw.get("block_id")
        if not value:
            continue
        if not snippet and not block_id:
            continue
        evidence = resolve_evidence_text(snippet, block_id, parse_json)
        _add_candidate(
            out,
            seen,
            field=name,
            value=value,
            evidence_text=evidence,
            party=name in PARTY_FIELDS,
        )


def _collect_table_rows(
    extraction_result: dict,
    key: str,
    prefix: str,
    parse_json: dict,
    out: list[ValidationCandidate],
    seen: set[str],
) -> None:
    rows = extraction_result.get(key) or []
    if not isinstance(rows, list):
        return
    value_columns = (
        "运营费类型",
        "费率",
        "rate_annual_pct",
        "费率（%/年）",
        "申赎费类型",
        "计费方式",
    )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        snippet = _row_snippet(row)
        block_id = row.get("block_id")
        if not snippet and not block_id:
            continue
        evidence = resolve_evidence_text(snippet, block_id, parse_json)
        if not evidence:
            continue
        for col in value_columns:
            value = _stringify(row.get(col))
            if not value:
                continue
            field = f"{prefix}[{idx}].{col}"
            _add_candidate(
                out,
                seen,
                field=field,
                value=value,
                evidence_text=evidence,
            )


def _collect_path_b(
    path_b_json: dict | None,
    out: list[ValidationCandidate],
    seen: set[str],
) -> None:
    if not path_b_json or not isinstance(path_b_json, dict):
        return
    snippets = path_b_json.get("source_snippets") or {}
    if not isinstance(snippets, dict):
        return
    for path, evidence in snippets.items():
        if not isinstance(path, str):
            continue
        evidence_text = _stringify(evidence)
        if not evidence_text:
            continue
        value = _nested_value(path_b_json, path)
        field = f"path_b.{path}"
        _add_candidate(
            out,
            seen,
            field=field,
            value=value or evidence_text[:80],
            evidence_text=evidence_text,
        )


def collect_validation_candidates(
    extraction_result: dict,
    path_b_json: dict | None,
    parse_json: dict,
) -> list[ValidationCandidate]:
    out: list[ValidationCandidate] = []
    seen: set[str] = set()
    parse_json = parse_json or {}
    _collect_product_elements(extraction_result, parse_json, out, seen)
    _collect_table_rows(
        extraction_result, "fee_rates", "fee_rates", parse_json, out, seen
    )
    _collect_table_rows(
        extraction_result,
        "subscription_fees",
        "subscription_fees",
        parse_json,
        out,
        seen,
    )
    _collect_path_b(path_b_json, out, seen)
    return out
