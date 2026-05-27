from __future__ import annotations

import asyncio
from typing import Any

from backend.app.llm.client import LlmClient
from backend.app.validate.deterministic import deterministic_validation_items
from backend.app.validate.evidence import collect_validation_candidates
from backend.app.validate.policy import apply_validation_policy
from backend.app.validate.prompts import build_validation_messages
from backend.app.validate.schemas import (
    ValidationBatchResponse,
    ValidationItem,
    ValidationResult,
)

DEFAULT_BATCH_SIZE = 10


def _chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def run_llm_validation(
    extraction_result: dict,
    path_b_json: dict | None,
    parse_json: dict,
    *,
    llm_client: LlmClient | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> ValidationResult:
    client = llm_client or LlmClient()

    def _finish(
        items: list[ValidationItem],
        *,
        skipped: bool,
        model: str | None = None,
    ) -> ValidationResult:
        merged = apply_validation_policy(items, extraction_result)
        result = ValidationResult(
            model=model,
            skipped=skipped,
            items=merged,
        )
        result.compute_summary()
        return result

    if not client.available:
        return _finish([], skipped=True)

    candidates = collect_validation_candidates(
        extraction_result, path_b_json, parse_json
    )
    if not candidates:
        return _finish([], skipped=False, model=client.model_name)

    all_items: list[ValidationItem] = []
    for batch in _chunk(candidates, batch_size):
        messages = build_validation_messages(batch)
        parsed = await client.chat_json(messages, ValidationBatchResponse)
        by_field = {c.field: c for c in batch}
        for row in parsed.items:
            if not row.field:
                continue
            cand = by_field.get(row.field)
            all_items.append(
                ValidationItem(
                    field=row.field,
                    status=row.status,
                    value=cand.value if cand else None,
                    reason=row.reason or "（模型未返回原因）",
                    suggestion=row.suggestion,
                )
            )

    overrides = deterministic_validation_items(extraction_result)
    by_field = {item.field: item for item in all_items}
    for field, item in overrides.items():
        by_field[field] = item
    return _finish(list(by_field.values()), skipped=False, model=client.model_name)


def run_llm_validation_sync(
    extraction_result: dict,
    path_b_json: dict | None,
    parse_json: dict,
    *,
    llm_client: LlmClient | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> ValidationResult:
    return asyncio.run(
        run_llm_validation(
            extraction_result,
            path_b_json,
            parse_json,
            llm_client=llm_client,
            batch_size=batch_size,
        )
    )
