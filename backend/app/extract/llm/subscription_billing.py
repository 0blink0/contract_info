"""LLM inference of 申购/认购 计费方式 (价内法 / 价外法) from 募集 + 申赎章节."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.config import get_settings
from backend.app.extract.schemas import ExtractionWarning
from backend.app.extract.text_limits import text_for_llm_prompt
from backend.app.llm.client import LlmClient


class SubscriptionBillingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    认购费计费方式: str | None = None
    申购费计费方式: str | None = None
    赎回费计费方式: str | None = None


def billing_map_from_response(parsed: SubscriptionBillingResponse) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, val in [
        ("认购费", parsed.认购费计费方式),
        ("申购费", parsed.申购费计费方式),
        ("赎回费", parsed.赎回费计费方式),
    ]:
        v = (val or "").strip()
        if v:
            out[key] = v
    return out


async def extract_subscription_billing_llm(
    client: LlmClient | None,
    text: str,
) -> tuple[dict[str, str], list[ExtractionWarning]]:
    if not client or not client.available or not text.strip():
        return {}, []

    system = (
        "你是私募基金合同申赎费用计费方式判断助手。"
        "根据合同片段判断认购费、申购费、赎回费各自采用「价内法」还是「价外法」。\n"
        "价外法（主流）：净认/申购金额 = 金额 ÷ (1+费率)；费用 = 金额×费率÷(1+费率)；"
        "份额 = (金额−费用) ÷ 净值。\n"
        "价内法：净认/申购金额 = 金额×(1−费率)；费用 = 金额×费率（不除以1+费率）；"
        "赎回金额直接扣减费用。\n"
        "认购费公式在募集章、申购费公式在申赎章，需分别判断，二者可能不同。"
        "合同未写明计算依据或无法判断时对应字段留空字符串。"
        "只输出 JSON，禁止 markdown。"
    )
    user = (
        "【合同片段（含募集章认购、申赎章申购赎回）】\n"
        f"{text_for_llm_prompt(text)}\n\n"
        '请输出 JSON：{"认购费计费方式":"","申购费计费方式":"","赎回费计费方式":""}，'
        "取值仅限「价内法」「价外法」或空字符串。"
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, SubscriptionBillingResponse)
            return billing_map_from_response(parsed), []
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break
    return {}, [
        ExtractionWarning(
            field="subscription_billing",
            code="llm_subscription_billing_failed",
            message=last_err or "unknown",
            suggestion="保留规则层计费方式推断结果",
        )
    ]
