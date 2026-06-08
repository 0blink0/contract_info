"""LLM-based extraction of the open-day raw clause from the subscription chapter.

The LLM locates verbatim text of open-day / trading-day rules so that human
reviewers see only the relevant clauses, not the full subscription chapter.
Rules-based extraction (passing the full sub_text) is kept as a fallback.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.config import get_settings
from backend.app.extract.schemas import ExtractionWarning
from backend.app.extract.text_limits import text_for_llm_prompt
from backend.app.llm.client import LlmClient


class OpenDayRawResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    原文摘录: str | None = None


async def extract_open_day_section_llm(
    client: LlmClient | None,
    subscription_text: str,
) -> tuple[str | None, list[ExtractionWarning]]:
    """Return (raw_section_text, warnings).

    raw_section_text: verbatim open-day clause(s) copied from the contract.
    Returns (None, []) when the client is unavailable; caller falls back to
    passing the full subscription chapter text.
    """
    if not client or not client.available or not subscription_text.strip():
        return None, []

    system = (
        "你是私募基金合同要素抽取助手。"
        "在申购赎回章节中找出开放日/交易日时间安排相关的原文，一字不改地引用。\n"
        "仅引用说明何时开放（如每月第X个交易日、封闭期内特殊安排、申购赎回时间窗口等）的段落，"
        "不引用确认流程、款项划付、费用计算、锁定期、人数限制等无关内容。"
        "章节无相关内容则留空字符串。\n"
        "禁止改写、总结或翻译原文。只输出 JSON，禁止 markdown 代码块。"
    )
    user = (
        "【申购赎回章节】\n"
        f"{text_for_llm_prompt(subscription_text)}\n\n"
        '请输出 JSON：{"原文摘录":""}'
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, OpenDayRawResponse)
            raw = (parsed.原文摘录 or "").strip() or None
            return raw, []
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break
    return None, [
        ExtractionWarning(
            field="open_day.raw_section",
            code="llm_open_day_failed",
            message=last_err or "unknown",
            suggestion="规则层原文摘录保留；可人工查阅申购赎回章节",
        )
    ]
