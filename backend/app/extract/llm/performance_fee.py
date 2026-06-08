"""LLM-based extraction of the performance-fee raw clause from the fees chapter.

The LLM locates the exact verbatim text of the performance-fee subsection so that
human reviewers always see the correct original wording regardless of contract format.
Rules-based extraction (_perf_fee_raw_section) is kept as a fallback.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.config import get_settings
from backend.app.extract.llm.chapter_prompts import build_rag_history_block
from backend.app.extract.schemas import ExtractionWarning
from backend.app.extract.text_limits import text_for_llm_prompt
from backend.app.llm.client import LlmClient


class PerformanceFeeRawResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    原文摘录: str | None = None
    是否计提业绩报酬: str | None = None  # "是" / "否" / "条件性不计提"


async def extract_performance_fee_section_llm(
    client: LlmClient | None,
    fees_text: str,
    rag_cases: list[dict[str, str]] | None = None,
) -> tuple[str | None, str | None, list[ExtractionWarning]]:
    """Return (raw_section_text, has_perf_fee_flag, warnings).

    raw_section_text: verbatim performance-fee clause copied from the contract.
    has_perf_fee_flag: "是" / "否" / "条件性不计提" / None if indeterminate.
    Falls back to (None, None, []) when the client is unavailable.
    """
    if not client or not client.available or not fees_text.strip():
        return None, None, []

    system = (
        "你是私募基金合同要素抽取助手。"
        "在费用与税收章节中找出「业绩报酬」相关的完整条款原文，一字不改地引用。\n"
        "根据内容判断是否计提：合同明确否定计提→「否」；存在完整业绩报酬条款→「是」；"
        "仅在特定条件下不计提（如侧袋账户、亏损期间）→「条件性不计提」；章节无相关内容→两字段均留空。\n"
        "禁止改写、总结或翻译原文。只输出 JSON，禁止 markdown 代码块。"
    )
    rag_block = build_rag_history_block(rag_cases)
    rag_part = f"{rag_block}\n\n" if rag_block else ""

    user = (
        "【费用与税收章节】\n"
        f"{text_for_llm_prompt(fees_text)}\n\n"
        f"{rag_part}"
        '请输出 JSON：{"原文摘录":"","是否计提业绩报酬":""}'
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, PerformanceFeeRawResponse)
            raw = (parsed.原文摘录 or "").strip() or None
            flag = (parsed.是否计提业绩报酬 or "").strip() or None
            return raw, flag, []
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break
    return None, None, [
        ExtractionWarning(
            field="performance_fee.raw_section",
            code="llm_performance_fee_failed",
            message=last_err or "unknown",
            suggestion="规则层原文摘录保留；可人工查阅费用与税收章节",
        )
    ]
