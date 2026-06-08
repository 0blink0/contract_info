from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.extract.text_limits import text_for_llm_prompt
from backend.app.extract.schemas import ExtractionWarning, FeeRateRow, SubscriptionFeeRow
from backend.app.llm.client import LlmClient


class _FeeRateRowsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rows: list[FeeRateRow] = Field(default_factory=list)


class _SubFeeRowsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rows: list[SubscriptionFeeRow] = Field(default_factory=list)


_FEE_RATE_SYSTEM = (
    "你是私募基金合同运营费率抽取助手。从合同片段提取运营费率子表，输出 JSON，禁止 markdown 代码块。\n\n"
    '输出格式示例：\n{"rows": [\n'
    '  {"运营费类型": "管理费", "费率（%/年）": "1", "计费频率": "按日", "计费基准": "前一日资产净值"},\n'
    '  {"运营费类型": "托管费", "费率（%/年）": "0.025", "计费频率": "按日", "计费基准": "前一日资产净值"}\n'
    "]}\n\n"
    "字段说明：\n"
    "· 运营费类型：管理费 / 托管费 / 运营服务费 / 基金服务费 / 外包服务费 / 销售服务费 / 投资顾问费（保留合同原文用词）\n"
    "· 费率（%/年）：纯数字字符串；年费率 1% 填 \"1\"，0.025% 填 \"0.025\"；"
    "合同明确本基金不收取该费用时填 \"0\"\n"
    "· 计费频率：按日 / 按月 / 按年\n"
    "· 计费基准：前一日资产净值 / 资产净值 / 初始委托本金（按合同原文）\n\n"
    "侧袋账户单独免收管理费不影响主基金，不计入结果；"
    "每种费用类型只输出一行；若某费用仅对特定份额类别收取、或各类费率不同，"
    "在基金名称字段加类别后缀并分行（如「基金全称B」）；"
    "对全体份额完全相同的费用只写一行，基金名称留空；"
    "合同中没有的费用类型不输出该行"
)

_SUB_FEE_SYSTEM = (
    "你是私募基金合同申赎费率抽取助手。从合同片段提取申赎费率子表，输出 JSON，禁止 markdown 代码块。\n\n"
    '输出格式示例：\n{"rows": [\n'
    '  {"申赎费类型": "认购费", "费率": "1", "时间区间单位": "", "区间开始": "", "区间结束": "", "计费基准": "不分段"},\n'
    '  {"申赎费类型": "申购费", "费率": "0.5", "时间区间单位": "", "区间开始": "", "区间结束": "", "计费基准": "不分段"},\n'
    '  {"申赎费类型": "赎回费", "费率": "1.5", "时间区间单位": "天", "区间开始": "", "区间结束": "180", "计费基准": "区间 (P<180)"},\n'
    '  {"申赎费类型": "赎回费", "费率": "1", "时间区间单位": "天", "区间开始": "180", "区间结束": "365", "计费基准": "区间 (180<=P<365)"},\n'
    '  {"申赎费类型": "赎回费", "费率": "0", "时间区间单位": "天", "区间开始": "365", "区间结束": "", "计费基准": "区间 (P>=365)"}\n'
    "]}\n\n"
    "字段说明：\n"
    "· 申赎费类型：认购费 / 申购费 / 赎回费\n"
    "· 费率：纯数字字符串，1.5% 填 \"1.5\"；不收取填 \"0\"\n"
    "· 时间区间单位：天 或 月（有持有期分段时填，否则留空）\n"
    "· 区间开始：持有期分段起始数值，纯数字（无分段或无下界时留空）\n"
    "· 区间结束：持有期分段结束数值，纯数字（无分段或无上界时留空）\n"
    "· 计费基准：无持有期分段时填「不分段」；"
    "有分段时按持有天数 P 的区间填写，格式如「区间 (P<180)」「区间 (180<=P<365)」「区间 (P>=365)」\n\n"
    "赎回费有持有期分段时每个区间单独一行；"
    "有 A/B 类份额且各类费率不同、或某费用仅对特定类别收取时，"
    "在基金名称字段加类别后缀并分行输出（如「基金全称A」「基金全称B」）；"
    "对全体份额完全相同的费用只写一行，基金名称留空；"
    "合同中没有的费用类型不输出该行"
)


def _build_messages(
    system: str, fund_name: str | None, text: str
) -> list[dict[str, str]]:
    user = (
        f"【基金全称】{fund_name or '（未知）'}\n\n"
        f"【合同片段】\n{text_for_llm_prompt(text)}\n\n"
        "请仅输出 JSON。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def extract_fee_rates_llm(
    client: LlmClient | None,
    fees_text: str,
    *,
    fund_name: str | None,
) -> tuple[list[FeeRateRow], list[ExtractionWarning]]:
    """LLM 从费用章节提取运营费率行（管理费/托管费/服务费等）。"""
    if not client or not client.available or not fees_text.strip():
        return [], []
    messages = _build_messages(_FEE_RATE_SYSTEM, fund_name, fees_text)
    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, _FeeRateRowsResponse)
            rows = [r for r in parsed.rows if r.rate_annual_pct is not None]
            for r in rows:
                if fund_name and not r.基金名称:
                    r.基金名称 = fund_name
            return rows, []
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break
    return [], [
        ExtractionWarning(
            field="fee_rates:llm",
            code="llm_fee_rates_failed",
            message=last_err or "unknown",
            suggestion="已回退到规则层提取",
        )
    ]


async def extract_subscription_fees_llm(
    client: LlmClient | None,
    sub_text: str,
    *,
    fund_name: str | None,
) -> tuple[list[SubscriptionFeeRow], list[ExtractionWarning]]:
    """LLM 从申赎章节提取认购/申购/赎回费率行（含持有期分段）。"""
    if not client or not client.available or not sub_text.strip():
        return [], []
    messages = _build_messages(_SUB_FEE_SYSTEM, fund_name, sub_text)
    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, _SubFeeRowsResponse)
            rows = [r for r in parsed.rows if r.费率 is not None]
            for r in rows:
                if fund_name and not r.基金名称:
                    r.基金名称 = fund_name
            return rows, []
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break
    return [], [
        ExtractionWarning(
            field="subscription_fees:llm",
            code="llm_sub_fees_failed",
            message=last_err or "unknown",
            suggestion="已回退到规则层提取",
        )
    ]
