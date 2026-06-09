"""Dedicated LLM call to extract the full performance-fee section verbatim.

Separate from fees_combined to avoid token competition: fees_combined outputs
30+ JSON fields, which forces the model to truncate the raw-text field.
This call outputs a single field, giving the model its full token budget for
the raw text.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.extract.text_limits import text_for_llm_prompt
from backend.app.llm.client import LlmClient

_SYSTEM = (
    "你是私募基金合同原文提取助手。\n"
    "在用户提供的基金合同全文中，找到「业绩报酬」章节，"
    "将该章节的全部文字**一字不改、完整**复制——包括计提条件、计算公式、"
    "各参数定义（PFi,j / HWMi,j / HWM0 / Ri,j / Fi,j 等）以及支付约定，"
    "不得省略、总结或改写任何句子。\n"
    "输出单个 JSON 对象，只含一个字段「业绩报酬原文」，值为完整原文字符串。\n"
    "若合同明确不设业绩报酬，值填「本基金不计提业绩报酬」。\n"
    "若合同中完全没有业绩报酬章节，值填空字符串。"
)


class _PerfFeeSectionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    业绩报酬原文: str | None = None


async def extract_perf_fee_section_llm(
    client: LlmClient | None,
    full_text: str,
) -> str | None:
    """Return the verbatim performance-fee section, or None on failure."""
    if not client or not client.available:
        return None
    text = full_text.strip()
    if not text:
        return None

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": text_for_llm_prompt(text)},
    ]
    try:
        parsed = await client.chat_json(messages, _PerfFeeSectionResponse)
        return (parsed.业绩报酬原文 or "").strip() or None
    except Exception:  # noqa: BLE001
        return None
