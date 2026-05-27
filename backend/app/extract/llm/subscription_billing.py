"""LLM inference of 申购/认购 计费方式 (价内法 / 价外法) from 募集 + 申赎章节."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.extract.schemas import ExtractionWarning
from backend.app.extract.text_limits import text_for_llm_prompt
from backend.app.llm.client import LlmClient

_ALLOWED = frozenset({"价内法", "价外法"})


class SubscriptionBillingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    认购费计费方式: str | None = None
    申购费计费方式: str | None = None


def _normalize_method(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip().replace(" ", "")
    if "价内" in text:
        return "价内法"
    if "价外" in text:
        return "价外法"
    if text in _ALLOWED:
        return text
    return None


def billing_map_from_response(parsed: SubscriptionBillingResponse) -> dict[str, str]:
    out: dict[str, str] = {}
    sub = _normalize_method(parsed.认购费计费方式)
    pur = _normalize_method(parsed.申购费计费方式)
    if sub:
        out["认购费"] = sub
    if pur:
        out["申购费"] = pur
    return out


async def extract_subscription_billing_llm(
    client: LlmClient | None,
    text: str,
) -> tuple[dict[str, str], list[ExtractionWarning]]:
    if not client or not client.available or not text.strip():
        return {}, []

    system = (
        "你是私募基金合同申赎费用计费方式判断助手。"
        "根据合同片段判断认购费、申购费各自采用「价内法」还是「价外法」。"
        "价内法常见表述：申购（认）费用 = 缴款金额 × 费率 / (1+费率)，费用从缴款额中内扣。"
        "价外法常见表述：申购份额 = 申购金额 / (1+申购费率) / 价格，或净申购金额 = 申购金额/(1+费率)。"
        "认购费公式若在募集章、申购费在申赎章，需分别判断，二者可能不同。"
        "合同未写明计算依据或无法判断时对应字段留空。只输出 JSON，禁止 markdown。"
    )
    user = (
        "【合同片段（含募集章认购、申赎章申购赎回）】\n"
        f"{text_for_llm_prompt(text)}\n\n"
        '请输出 JSON：{"认购费计费方式":"","申购费计费方式":""}，'
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
