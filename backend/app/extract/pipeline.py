from __future__ import annotations

import asyncio
from typing import Any, cast

from backend.app.extract.llm.chapter_extract import extract_chapter_fields
from backend.app.extract.merge import merge_extraction
from backend.app.extract.rules import extract_fee_rates, extract_product_rules
from backend.app.extract.schemas import (
    ExtractionMeta,
    ExtractionResult,
    ExtractionWarning,
)
from backend.app.extract.section_windows import build_section_windows
from backend.app.extract.validate import validate_enums
from backend.app.llm.client import LlmClient

_LLM_WINDOWS = ("basic", "establish", "subscription", "investment", "fees")


async def extract_document(
    document: dict[str, Any],
    *,
    llm_client: LlmClient | None = None,
) -> tuple[ExtractionResult, list[ExtractionWarning]]:
    windows, truncated = build_section_windows(document)
    product_rules = extract_product_rules(document, windows)

    fund_fv = product_rules.get("基金全称")
    fund_name = str(fund_fv.value) if fund_fv and fund_fv.value else None
    fee_rates = extract_fee_rates(windows.get("fees", ""), fund_name)

    llm_fields: dict[str, Any] = {}
    warnings: list[ExtractionWarning] = []
    chapters_called: list[str] = []

    client = cast(Any, llm_client if llm_client is not None else LlmClient())
    if getattr(client, "available", False):
        for key in _LLM_WINDOWS:
            text = windows.get(key, "")
            if not text.strip():
                continue
            fields, w = await extract_chapter_fields(client, key, text)
            llm_fields.update(fields)
            warnings.extend(w)
            if fields:
                chapters_called.append(key)

    meta = ExtractionMeta(
        model=client.model_name if client.available else None,
        chapters_called=chapters_called,
        truncated_windows=truncated,
    )
    result = merge_extraction(product_rules, llm_fields, fee_rates, meta=meta)
    warnings.extend(validate_enums(result))
    return result, warnings


def extract_document_sync(
    document: dict[str, Any],
    *,
    llm_client: LlmClient | None = None,
) -> tuple[ExtractionResult, list[ExtractionWarning]]:
    return asyncio.run(extract_document(document, llm_client=llm_client))
