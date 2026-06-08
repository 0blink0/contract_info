"""LLM-based CRM field extraction guided by KB few-shot cases and passage matching."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict

from backend.app.extract.path_b_crm import _find_similar_passage
from backend.app.llm.client import LlmClient

logger = logging.getLogger(__name__)

_CRM_FIELDS = ["提取时点", "业绩报酬提取方式", "业绩基准类型", "门槛净值类型"]


class _FieldValue(BaseModel):
    model_config = ConfigDict(extra="ignore")
    字段值: str = ""


async def _extract_one_field(
    client: LlmClient,
    field_name: str,
    passage: str,
    kb_cases: list[dict[str, str]],
) -> str | None:
    few_shot_lines: list[str] = []
    for i, c in enumerate(kb_cases[:3], 1):
        snip = (c.get("snippet") or "").strip()[:300]
        val = (c.get("field_value") or "").strip()
        if snip and val:
            few_shot_lines.append(f"{i}. 原文：{snip}\n   {field_name}：{val}")
    if not few_shot_lines:
        return None

    system = (
        f"你是私募基金合同要素提取助手，参考历史案例从合同段落中提取「{field_name}」字段的值。"
        "严格依据原文，不推断、不补充原文未提及的内容。"
        "只输出 JSON，禁止 markdown 代码块。"
    )
    user = (
        f"【历史案例参考】\n" + "\n".join(few_shot_lines) + "\n\n"
        f"【当前合同段落】\n{passage}\n\n"
        f'请输出 JSON：{{"字段值": ""}}'
    )
    try:
        result = await client.chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            _FieldValue,
        )
        value = (result.字段值 or "").strip()
        return value or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("KB field LLM extraction failed for %s: %s", field_name, exc)
        return None


async def extract_crm_fields_with_kb(
    client: LlmClient,
    fees_text: str,
    rag_cases: list[dict[str, str]],
) -> dict[str, tuple[str, str]]:
    """For each CRM field with KB cases, locate similar passage and extract value via LLM.

    Returns: {field_name: (llm_value, passage_snippet)}
    If no KB cases or no similar passage found for a field, that field is absent from result.
    """
    if not client.available or not rag_cases or not fees_text.strip():
        return {}

    kb_index: dict[str, list[dict[str, str]]] = {}
    for c in rag_cases:
        fn = (c.get("field_name") or "").strip()
        if fn:
            kb_index.setdefault(fn, []).append(c)

    tasks: list[Any] = []
    meta: list[tuple[str, str]] = []  # (field_name, passage)

    for field_name in _CRM_FIELDS:
        cases = kb_index.get(field_name) or []
        if not cases:
            continue
        snippets = [c.get("snippet", "").strip() for c in cases if c.get("snippet", "").strip()]
        if not snippets:
            continue
        passage = _find_similar_passage(fees_text, snippets)
        if not passage:
            continue
        tasks.append(_extract_one_field(client, field_name, passage, cases))
        meta.append((field_name, passage))

    if not tasks:
        return {}

    values = await asyncio.gather(*tasks, return_exceptions=True)
    result: dict[str, tuple[str, str]] = {}
    for (field_name, passage), value in zip(meta, values):
        if isinstance(value, str) and value:
            result[field_name] = (value, passage)
            logger.info("KB field LLM: %s → %s", field_name, value)

    return result
