"""Combined LLM extraction for all fee-related fields.

Replaces individual calls to:
  extract_fee_rates_llm, extract_subscription_fees_llm,
  extract_subscription_billing_llm, extract_performance_fee_section_llm,
  extract_crm_fields_with_kb, extract_chapter_fields("fees")
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.extract.schemas import (
    ExtractionWarning,
    FeeRateRow,
    SubscriptionFeeRow,
)
from backend.app.extract.llm.snippet_groups import apply_row_group_snippet
from backend.app.extract.field_catalog import CRM_PERFORMANCE_FEE_FIELDS
from backend.app.extract.text_limits import excerpt_for_display, text_for_llm_prompt
from backend.app.llm.client import LlmClient
_CHAPTER_FEE_FIELDS = ("计费频率", "计费基准", "年计提天数", "费用计算方式")


class _FeesCombinedResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    运营费率原文: str | None = None
    申赎费率原文: str | None = None
    费用元数据原文: str | None = None
    业绩报酬CRM原文: str | None = None
    运营费率: list[FeeRateRow] = Field(default_factory=list)
    申赎费率: list[SubscriptionFeeRow] = Field(default_factory=list)
    认购费计费方式: str | None = None
    申购费计费方式: str | None = None
    赎回费计费方式: str | None = None
    业绩报酬原文: str | None = None
    是否计提业绩报酬: str | None = None
    计费频率: str | None = None
    计费基准: str | None = None
    年计提天数: str | None = None
    费用计算方式: str | None = None
    提取时点: str | None = None
    业绩报酬提取方式: str | None = None
    业绩基准类型: str | None = None
    门槛净值类型: str | None = None
    提取比例: str | None = None


_FEES_SYSTEM = (
    "你是私募基金合同费用要素抽取助手。从合同费用章节和申赎章节中提取所有费用相关字段，"
    "输出单个 JSON 对象，禁止 markdown 代码块。\n"
    "重要：只要合同提供了对应章节文字，「运营费率」和「申赎费率」数组就不得为空，"
    "必须输出所有能从文本中确认的行；宁可多输出一行也不可遗漏。\n\n"
    "【原文摘录规则】同一合同段落推导出多行/多字段时，只在对应分组键下输出一次「…原文」，"
    "不要在每个字段或每行重复粘贴；例外：「运营费率」和「申赎费率」数组每行均须填自己的「原文」，"
    "详见各字段说明。\n\n"
    "输出格式示例（仅示意结构）：\n"
    '{"运营费率原文":"（可选）各费用类型共用的通用约定段落，如统一的计提/支付规则；每行已有自己的「原文」时可不填",'
    '"运营费率":['
    '{"运营费类型":"管理费","基金名称":"示例基金A","费率（%/年）":"1","计费频率":"按日","支付频率":"按季",'
    '"原文":"A类份额年管理费率为【1%】，每日计提，按季支付。"},'
    '{"运营费类型":"管理费","基金名称":"示例基金B","费率（%/年）":"1","计费频率":"按日","支付频率":"按季",'
    '"原文":"B类份额年管理费率为【1%】，每日计提，按季支付。"},'
    '{"运营费类型":"管理费","基金名称":"示例基金C","费率（%/年）":"1","计费频率":"按日","支付频率":"按季",'
    '"原文":"C类份额年管理费率为【1%】，每日计提，按季支付。"},'
    '{"运营费类型":"管理费","基金名称":"示例基金D","费率（%/年）":"0","计费频率":"按日","支付频率":"按季",'
    '"原文":"D类份额不收取管理费，年管理费率为【0%】。"},'
    '{"运营费类型":"托管费","费率（%/年）":"0.025","计费频率":"按日","支付频率":"按季",'
    '"原文":"本基金托管费按年0.025%的费率收取，每日计提，按季支付。"}],'
    '"费用元数据原文":"管理费、托管费均按前一日资产净值，每日计提，由系统自动计算。",'
    '"计费频率":"按日","计费基准":"前一日资产净值","年计提天数":"365","费用计算方式":"系统计算",'
    '"申赎费率原文":"（可选）各申赎费类型共用的通用约定段落，如统一的份额确认基准；每行已有自己的「原文」时可不填",'
    '"申赎费率":['
    '{"申赎费类型":"认购费","基金名称":"示例基金A","费率":"0.5","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段",'
    '"原文":"A类份额认购费率为【0.5%】，净认购金额=认购金额÷(1+认购费率)。"},'
    '{"申赎费类型":"认购费","基金名称":"示例基金B","费率":"0","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段",'
    '"原文":"B类份额认购费率为【0%】，免收认购费。"},'
    '{"申赎费类型":"认购费","基金名称":"示例基金C","费率":"0","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段",'
    '"原文":"C类份额认购费率为【0%】，免收认购费。"},'
    '{"申赎费类型":"认购费","基金名称":"示例基金D","费率":"0","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段",'
    '"原文":"D类份额认购费率为【0%】，免收认购费。"},'
    '{"申赎费类型":"申购费","费率":"0.5","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段",'
    '"原文":"净申购金额=申购金额÷(1+申购费率)，申购费率为0.5%。"},'
    '{"申赎费类型":"赎回费","费率":"1","费率类型":"百分比","计费方式":"价内法",'
    '"时间区间单位":"天","区间开始":"","区间结束":"180","计费基准":"区间 (P<180)",'
    '"原文":"赎回费用=赎回份额×赎回价格×赎回费率，持有期限小于180天的赎回费率为1%。"}],'
    '"认购费计费方式":"价外法","申购费计费方式":"价外法","赎回费计费方式":"价内法",'
    '"业绩报酬原文":"…完整业绩报酬条款…","是否计提业绩报酬":"是",'
    '"业绩报酬CRM原文":"…含提取时点/高水位等表述的段落…",'
    '"提取时点":"","业绩报酬提取方式":"","业绩基准类型":"","门槛净值类型":"","提取比例":""}\n\n'
    "字段说明：\n"
    "【运营费率原文】（可选）各费用类型共用的通用约定段落；每行已有自己的「原文」时可不填\n"
    "【运营费率】管理费/托管费/运营服务费/基金服务费/外包服务费/销售服务费/投资顾问费（保留合同原文用词）；"
    "费率（%/年）纯数字，不含%符号（1%填\"1\"，0.5%填\"0.5\"，0%填\"0\"）；免收填\"0\"；侧袋账户单独免收不计入；\n"
    "  每行必填「原文」：一字不改地摘录合同中该费用类型对应的原文（须含费率数字及计提/支付约定）；\n"
    "  ─ 有份额分级时，分行判断规则：\n"
    "  · 合同用横向表格（类别为列）或逐类文字描述了某费项 → 该费项每个类别各输出一行，费率相同也须分行，基金名称填「基金全称＋类别字母」\n"
    "  · 合同只描述了部分类别（如「仅对A/C收取管理费」），其余已知类别（见【本基金份额类别】）视为不收取，各输出一行（费率填0）\n"
    "  · 合同对某费项仅有统一描述（无表格、无逐类文字）→ 只写一行，基金名称留空\n"
    "  · 严禁以「费率相同」为由合并已按类别展示的费项；严禁用无类别字母的基金全称行代表若干类别\n\n"
    "  示例1【有份额分级·横向表格】\n"
    "  合同原文（表格）：\n"
    "  |        | A类份额 | B类份额 | C类份额 |\n"
    "  | 年管理费率 | 0.5%  | 0%    | 1%    |\n"
    "  | 销售服务费率| 0%   | 0.4%  | 0.6%  |\n"
    "  另有统一文字：「本基金托管费按0.05%年费率，每日计提，按季支付。」\n"
    "  已知类别为A/B/C，正确输出（管理费3行+销售服务费3行+托管费1行）：\n"
    '  {"运营费类型":"管理费","基金名称":"示例基金A","费率（%/年）":"0.5","计费频率":"按日","支付频率":"按季","原文":"（表格所在章节计提/支付约定文字）"}\n'
    '  {"运营费类型":"管理费","基金名称":"示例基金B","费率（%/年）":"0","计费频率":"按日","支付频率":"按季","原文":"（同上）"}\n'
    '  {"运营费类型":"管理费","基金名称":"示例基金C","费率（%/年）":"1","计费频率":"按日","支付频率":"按季","原文":"（同上）"}\n'
    '  {"运营费类型":"销售服务费","基金名称":"示例基金A","费率（%/年）":"0","计费频率":"按日","支付频率":"按季","原文":"（同上）"}\n'
    '  {"运营费类型":"销售服务费","基金名称":"示例基金B","费率（%/年）":"0.4","计费频率":"按日","支付频率":"按季","原文":"（同上）"}\n'
    '  {"运营费类型":"销售服务费","基金名称":"示例基金C","费率（%/年）":"0.6","计费频率":"按日","支付频率":"按季","原文":"（同上）"}\n'
    '  {"运营费类型":"托管费","基金名称":"示例基金","费率（%/年）":"0.05","计费频率":"按日","支付频率":"按季","原文":"本基金托管费按0.05%年费率，每日计提，按季支付。"}\n\n'
    "  示例2【有份额分级·文字逐类描述】\n"
    "  合同原文：「本基金仅对A类份额和C类份额收取管理费。本基金的A类份额的年管理费率为【0.5】%，"
    "HA=EA×A类份额年管理费率÷365。本基金的C类份额的年管理费率为【1】%，HC=EC×C类份额年管理费率÷365。"
    "本基金A类份额和C类份额的管理费自基金成立日起，每日计提，按季支付。」\n"
    "  已知类别为A/B/C，正确输出（A/C有费率，B未提及补0，共3行）：\n"
    '  {"运营费类型":"管理费","基金名称":"示例基金A","费率（%/年）":"0.5","计费频率":"按日","支付频率":"按季","原文":"本基金仅对A类份额和C类份额收取管理费。本基金的A类份额的年管理费率为【0.5】%...按季支付。"}\n'
    '  {"运营费类型":"管理费","基金名称":"示例基金C","费率（%/年）":"1","计费频率":"按日","支付频率":"按季","原文":"本基金的C类份额的年管理费率为【1】%...按季支付。"}\n'
    '  {"运营费类型":"管理费","基金名称":"示例基金B","费率（%/年）":"0","计费频率":"按日","支付频率":"按季","原文":"本基金仅对A类份额和C类份额收取管理费。"}\n\n'
    "【申赎费率原文】（可选）各申赎费类型共用的通用约定段落；每行已有自己的「原文」时可不填\n"
    "【申赎费率】数组，每行字段：申赎费类型、基金名称（分级时填）、费率、费率类型、计费方式、计费基准、"
    "时间区间单位、区间开始、区间结束、原文。\n"
    "  每行必填「原文」：一字不改地摘录合同中该申赎费类型对应的原文（须含费率数字及计费方式公式/依据）；\n"
    "  ─ 有份额分级时，分行判断规则同运营费率（合同按类别展示则分行，统一描述则一行，仅部分类别有费率则其余补0）\n\n"
    "  示例3【有份额分级·申赎费率横向表格】\n"
    "  合同原文（表格）：\n"
    "  |       | A类份额 | B类份额 | C类份额 |\n"
    "  | 认购费率 | 0.5%  | 0%    | 0%    |\n"
    "  | 申购费率 | 0.5%  | 0%    | 0%    |\n"
    "  另有统一文字：「赎回费=赎回份额×赎回价格×赎回费率，持有期限小于180天费率1%，180天及以上免收。」\n"
    "  已知类别为A/B/C，正确输出（认购3行+申购3行+赎回不分级2行）：\n"
    '  {"申赎费类型":"认购费","基金名称":"示例基金A","费率":"0.5","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段","原文":"（认购费约定段落）"}\n'
    '  {"申赎费类型":"认购费","基金名称":"示例基金B","费率":"0","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段","原文":"（同上）"}\n'
    '  {"申赎费类型":"认购费","基金名称":"示例基金C","费率":"0","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段","原文":"（同上）"}\n'
    '  {"申赎费类型":"申购费","基金名称":"示例基金A","费率":"0.5","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段","原文":"（申购费约定段落）"}\n'
    '  {"申赎费类型":"申购费","基金名称":"示例基金B","费率":"0","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段","原文":"（同上）"}\n'
    '  {"申赎费类型":"申购费","基金名称":"示例基金C","费率":"0","费率类型":"百分比","计费方式":"价外法","计费基准":"不分段","原文":"（同上）"}\n'
    '  {"申赎费类型":"赎回费","基金名称":"","费率":"1","费率类型":"百分比","计费方式":"价内法","计费基准":"区间 (P<180)","时间区间单位":"天","区间开始":"","区间结束":"180","原文":"赎回费=赎回份额×赎回价格×赎回费率，持有期限小于180天费率1%..."}\n'
    '  {"申赎费类型":"赎回费","基金名称":"","费率":"0","费率类型":"百分比","计费方式":"价内法","计费基准":"区间 (P>=180)","时间区间单位":"天","区间开始":"180","区间结束":"","原文":"持有180天及以上免收赎回费。"}\n\n'
    "  · 申赎费类型：认购费/申购费/赎回费；费率纯数字（0.5%填\"0.5\"，免收填\"0\"）\n"
    "  · 费率类型：申赎费一律填「百分比」（按金额比例计收）\n"
    "  · 计费方式：价外法 或 价内法（见下规则；每行必填，勿留空）\n"
    "  · 计费基准：无分段→「不分段」；赎回持有期分段→「区间 (P<X)」「区间 (A<=P<B)」「区间 (P>=A)」\n"
    "  · 时间区间单位/区间开始/区间结束：赎回费分段时填「天」及边界天数\n\n"
    "【价外法 / 价内法判定规则】\n"
    "价外法（净额法，费用另算在金额外）：\n"
    "  · 净认购金额=认购金额÷(1+认购费率) 或 认购费用=认购金额×认购费率÷(1+认购费率)\n"
    "  · 净申购金额=申购金额÷(1+申购费率) 或 申购份额=申购金额÷(1+申购费率)÷申购价格\n"
    "  · 净申购金额=申购金额－申购费用 且 费用公式含 ÷(1+费率)\n"
    "价内法（费用从赎回/确认金额中扣）：\n"
    "  · 赎回费用=赎回份额×赎回价格×赎回费率（或赎回份数×价格×费率）\n"
    "  · 赎回金额公式中直接减去赎回费用\n"
    "  · 认购/申购：净认购/净申购金额=认购/申购金额×(1－费率) 则为价内法\n"
    "合同未写计算公式、仅写费率数字时：认购/申购默认价外法，赎回默认价内法（与行业惯例一致则填）。\n\n"
    "【示例·石云福禄1000指数增强一号类合同】\n"
    "认购费：「净认购金额=认购金额×认购费率/(1+认购费率)」「净认购金额=认购金额/(1+认购费率)」"
    "→ 价外法；费率如0.5%填0.5。\n"
    "申购费：「净申购份额=申购金额×申购费率/(1+申购费率)」或净申购金额=申购金额/(1+申购费率)"
    "→ 价外法。\n"
    "赎回费：「赎回费用=赎回份额×赎回价格×赎回费率」、持有期分段（如t<180天1%、180–360天0.2%）"
    "→ 价内法；每段一行。\n\n"
    "顶层「认购/申购/赎回费计费方式」可与各行计费方式一致，作汇总；以申赎费率[]各行「计费方式」为准。\n"
    "【业绩报酬原文】在费用章节中一字不改引用完整业绩报酬条款原文；"
    "明确否定→是否计提填「否」；有完整条款→「是」；"
    "仅特定条件（侧袋/亏损等）不计提→「条件性不计提」；章节无相关内容→两字段均留空\n"
    "【业绩报酬CRM原文】提取时点/业绩报酬提取方式/业绩基准类型/门槛净值类型/提取比例"
    "若来自同一段，只在此写一次原文；各 CRM 字段填值即可\n"
    "【费用元数据原文】计费频率、计费基准、年计提天数、费用计算方式若来自同一段，只写此处一次\n"
    "【费用元数据】计费频率（按日/按月/按年）、计费基准、年计提天数（实际天数/365/360）、"
    "费用计算方式（系统计算/管理人计算）；无明确说明则留空"
)


async def extract_fees_combined_llm(
    client: LlmClient | None,
    fees_text: str,
    sub_fees_text: str,
    *,
    fund_name: str | None,
    share_class_labels: list[str] | None = None,
    rag_cases: list[dict[str, str]] | None = None,
) -> tuple[
    list[FeeRateRow],
    list[SubscriptionFeeRow],
    dict[str, str],
    str | None,
    str | None,
    dict[str, str],
    dict[str, str],
    str | None,
    str | None,
    list[ExtractionWarning],
]:
    """Combined extraction of all fee-related fields.

    Returns:
        (fee_rates, sub_fees, billing_map, perf_raw, perf_flag,
         crm_fields, chapter_fee_fields, warnings)
    """
    if not client or not client.available:
        return [], [], {}, None, None, {}, {}, None, None, []

    fees_clean = fees_text.strip()
    sub_clean = sub_fees_text.strip()
    if not fees_clean and not sub_clean:
        return [], [], {}, None, None, {}, {}, None, None, []

    sections: list[str] = []
    if fees_clean:
        sections.append(f"【合同原文】\n{text_for_llm_prompt(fees_clean)}")
    if sub_clean:
        sections.append(f"【申购赎回补充原文】\n{text_for_llm_prompt(sub_clean)}")

    few_shot = ""
    if rag_cases:
        from backend.app.extract.llm.chapter_prompts import build_rag_history_block
        block = build_rag_history_block(rag_cases)
        if block:
            few_shot = f"\n\n{block}"

    class_hint = ""
    if share_class_labels:
        labels_str = "、".join(share_class_labels)
        class_hint = (
            f"\n\n【本基金份额类别】本基金已确认存在以下份额类别：{labels_str}。\n"
            "请按上述示例1/2/3的规则处理运营费率和申赎费率中的分级情形：\n"
            f"· 合同按类别展示（横向表格或逐类文字）→ {labels_str} 每个类别各输出一行（费率相同也须分行）\n"
            f"· 合同只提到部分类别有费率 → {labels_str} 中其余类别费率填0，也须各输出一行\n"
            "· 合同统一描述（无表格无逐类文字）→ 只写一行，基金名称留空"
        )

    user = (
        "\n\n".join(sections)
        + class_hint
        + few_shot
        + f"\n\n【基金全称】{fund_name or '（未知）'}\n\n请仅输出 JSON 对象。"
    )

    messages = [
        {"role": "system", "content": _FEES_SYSTEM},
        {"role": "user", "content": user},
    ]

    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, _FeesCombinedResponse)

            op_snip = excerpt_for_display(parsed.运营费率原文 or "")
            sub_snip = excerpt_for_display(parsed.申赎费率原文 or "")
            meta_snip = excerpt_for_display(parsed.费用元数据原文 or "")

            fee_rates = [r for r in parsed.运营费率 if r.rate_annual_pct is not None]
            sub_fees_raw = [r for r in parsed.申赎费率 if r.费率 is not None]

            # Semantic retry: fee text exists but LLM returned nothing → treat as failure
            if fees_clean and not fee_rates and attempt < settings.llm_max_retries:
                last_err = "LLM returned empty 运营费率 despite fee content"
                continue
            if sub_clean and not sub_fees_raw and attempt < settings.llm_max_retries:
                last_err = "LLM returned empty 申赎费率 despite subscription content"
                continue

            # If fund_name unavailable, infer base name from class-specific rows
            effective_fund = fund_name
            if not effective_fund:
                for r in fee_rates:
                    name = (r.基金名称 or "").strip()
                    if name:
                        effective_fund = re.sub(r"[A-Da-d]类?$", "", name).strip() or name
                        break
            if not effective_fund:
                for r in sub_fees_raw:
                    name = (r.基金名称 or "").strip()
                    if name:
                        effective_fund = re.sub(r"[A-Da-d]类?$", "", name).strip() or name
                        break

            for r in fee_rates:
                if effective_fund and not r.基金名称:
                    r.基金名称 = effective_fund
                if r.原文 and not r.snippet:
                    r.snippet = excerpt_for_display(r.原文)
            apply_row_group_snippet(fee_rates, op_snip)

            sub_fees = sub_fees_raw
            for r in sub_fees:
                if effective_fund and not r.基金名称:
                    r.基金名称 = effective_fund
                if not (r.费率类型 or "").strip():
                    r.费率类型 = "百分比"
                if r.原文 and not r.snippet:
                    r.snippet = excerpt_for_display(r.原文)
            apply_row_group_snippet(sub_fees, sub_snip)

            billing_map: dict[str, str] = {}
            for key, val in [
                ("认购费", parsed.认购费计费方式),
                ("申购费", parsed.申购费计费方式),
                ("赎回费", parsed.赎回费计费方式),
            ]:
                v = (val or "").strip()
                if v:
                    billing_map[key] = v
            # Row-level 计费方式 overrides top-level summary
            for r in sub_fees:
                fee_type = (r.申赎费类型 or "").strip()
                row_billing = (r.计费方式 or "").strip()
                if fee_type and row_billing:
                    billing_map[fee_type] = row_billing

            perf_raw = (parsed.业绩报酬原文 or "").strip() or None
            perf_flag = (parsed.是否计提业绩报酬 or "").strip() or None

            crm_fields: dict[str, str] = {}
            for field in CRM_PERFORMANCE_FEE_FIELDS:
                v = (getattr(parsed, field, None) or "").strip()
                if v:
                    crm_fields[field] = v

            chapter_fee_fields: dict[str, str] = {}
            for field in _CHAPTER_FEE_FIELDS:
                v = (getattr(parsed, field, None) or "").strip()
                if v:
                    chapter_fee_fields[field] = v

            crm_snip = excerpt_for_display(
                parsed.业绩报酬CRM原文 or parsed.业绩报酬原文 or ""
            ) or None

            return (
                fee_rates,
                sub_fees,
                billing_map,
                perf_raw,
                perf_flag,
                crm_fields,
                chapter_fee_fields,
                meta_snip or None,
                crm_snip,
                [],
            )
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break

    return [], [], {}, None, None, {}, {}, None, None, [
        ExtractionWarning(
            field="fees_combined",
            code="llm_fees_combined_failed",
            message=last_err or "unknown",
            suggestion="请检查 OPENAI_API_KEY 与网络连接后重试",
        )
    ]
