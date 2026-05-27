from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, create_model

from backend.app.config import get_settings
from backend.app.extract.field_catalog import CHAPTER_FIELDS
from backend.app.extract.field_snippets import resolve_field_snippet
from backend.app.extract.llm.chapter_prompts import build_messages
from backend.app.extract.schemas import ExtractionWarning, FieldValue
from backend.app.llm.client import LlmClient


def _response_model_for_window(window_key: str) -> type[BaseModel]:
    fields = CHAPTER_FIELDS.get(window_key, [])
    if not fields:
        return create_model(f"Empty{window_key}", __config__=ConfigDict(extra="ignore"))
    annotations = {name: (str | None, None) for name in fields}
    return create_model(
        f"Chapter_{window_key}",
        __config__=ConfigDict(extra="ignore"),
        **annotations,
    )


async def extract_chapter_fields(
    client: LlmClient | None,
    window_key: str,
    text: str,
) -> tuple[dict[str, FieldValue], list[ExtractionWarning]]:
    if not client or not client.available or not text.strip():
        return {}, []

    model_cls = _response_model_for_window(window_key)
    if not CHAPTER_FIELDS.get(window_key):
        return {}, []

    messages = build_messages(window_key, text)
    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, model_cls)
            out: dict[str, FieldValue] = {}
            for key, val in parsed.model_dump().items():
                if val is None or str(val).strip() == "":
                    continue
                value = str(val).strip()
                out[key] = FieldValue(
                    value=value,
                    confidence="medium",
                    source="llm",
                    snippet=resolve_field_snippet(key, text, value),
                )
            return out, []
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break
    warning = ExtractionWarning(
        field=f"chapter:{window_key}",
        code="llm_chapter_failed",
        message=last_err or "unknown",
        suggestion="规则层结果保留；可人工补录",
    )
    return {}, [warning]
