"""Combined LLM extraction for all product element fields + sub-tables + open day.

Replaces individual calls to:
  extract_chapter_fields("basic", "subscription", "investment",
                         "raising", "distribution", "risk"),
  extract_lock_periods_llm, extract_share_classes_llm,
  extract_open_day_section_llm
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from backend.app.config import get_settings
from backend.app.extract.field_snippets import resolve_field_snippet
from backend.app.extract.llm.snippet_groups import apply_row_group_snippet
from backend.app.extract.schemas import (
    ExtractionWarning,
    FieldValue,
    LockPeriodRow,
    ShareClassRow,
)
from backend.app.extract.text_limits import excerpt_for_display, text_for_llm_prompt
from backend.app.llm.client import LlmClient

_CODE_TYPE_BY_LETTER: dict[str, str] = {
    "A": "A份额",
    "B": "B份额",
    "C": "C份额",
    "D": "D份额",
}


def _infer_share_code_type(row: ShareClassRow) -> None:
    if (row.代码类型 or "").strip():
        return
    letter = (row.分级份额简称 or "").strip().upper()
    if len(letter) == 1 and letter in _CODE_TYPE_BY_LETTER:
        row.代码类型 = _CODE_TYPE_BY_LETTER[letter]


def _normalize_lock_row(row: LockPeriodRow, fund_name: str | None) -> None:
    if fund_name and not (row.产品名称 or "").strip():
        row.产品名称 = fund_name
    if (row.锁定时间 or "").strip() and not (row.锁定期 or "").strip():
        row.锁定期 = "有"


# Matches "某某标签：" prefix that DeepSeek prepends to 字段摘录 context sentences
_LABEL_PREFIX_RE = re.compile(r"^[^：\n]{1,20}：\s*")


def _clean_snippet_value(v: str) -> str:
    """Strip leading 'label：' prefix from context sentences returned by DeepSeek."""
    m = _LABEL_PREFIX_RE.match(v)
    if m:
        rest = v[m.end():]
        return rest if rest.strip() else v
    return v


_WINDOW_LABELS: dict[str, str] = {
    "cover_parties": "当事人与合同前言章节",
    "basic": "基金基本情况章节",
    "subscription": "申购赎回章节",
    "investment": "投资范围与策略章节",
    "raising": "募集与销售章节",
    "distribution": "收益分配章节",
    "risk": "风险揭示章节",
}

_PRODUCT_WINDOW_KEYS = tuple(_WINDOW_LABELS.keys())


class _ProductCombinedResponse(BaseModel):
    # extra="allow" captures all product fields (including those with special chars
    # like 是否量化/对冲基金) without needing explicit Python attribute declarations.
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    字段摘录: dict[str, str] = Field(default_factory=dict)
    锁定期子表: list[LockPeriodRow] = Field(default_factory=list)
    份额分级子表: list[ShareClassRow] = Field(default_factory=list)
    开放日原文: str | None = None


_PRODUCT_SYSTEM = (
    "你是私募基金合同产品要素抽取助手。从各章节中提取产品要素字段、锁定期子表、份额分级子表及开放日原文，"
    "输出单个 JSON 对象，禁止 markdown 代码块。\n\n"
    "【产品要素字段】（无法确定则留空字符串，日期规范为 yyyy/m/d）\n"
    "基金全称、备案编码、管理人、托管人、投资顾问、外包机构（仅输出机构名称，如「广发证券股份有限公司」；不输出描述性句子）、"
    "基金面值（⚠️只填阿拉伯数字1、100或1000，禁止输出任何包含「元」「人民币」「/份」「认购」的内容；合同写「人民币1.000元，认购价格为1.000元/份」→填1；「100元/份」→填100）、"
    "币种（从以下选填：人民币现钞/美元现汇/多币种/欧元现汇/港元现汇/澳元现汇/日元现汇/其他/英镑现汇；⚠️合同写「人民币」不含「现钞」→必须填「人民币现钞」，禁止直接输出「人民币」）、"
    "合伙人类型、"
    "管理类型（仅输出以下之一，禁止输出描述性语句：自主管理型/顾问管理型/银行委外合作(信托通道)/券商委外合作(信托通道)/其他；"
    "合同明确聘请投资顾问负责投资决策→顾问管理型；管理人自主投资→自主管理型；无法确定则留空）、"
    "份额结构（仅填「不分级」或「分级」，不得留空；\n"
    "  ▸ 分级：合同「基金份额的分类」或「份额分类」章节列出 A/B/C/D 等两类及以上份额 → 填「分级」；\n"
    "    字段摘录取该章节首句定义类原文，示例：「本基金按照基金委托人的身份条件及收取的费用不同分为两个类别，即为A类基金份额和B类基金份额」；\n"
    "  ▸ 不分级：合同写「本基金不分级」「不存在优先级份额和劣后级份额」或全程只有单一类别 → 填「不分级」；\n"
    "    字段摘录取「本基金不分级，不存在优先级份额和劣后级份额的结构化基金份额设计」之类的原文；\n"
    "  ⚠️禁止把估值章节里「分级基金的子基金」「分级基金的母基金」等涉及公募产品估值的通用条款作为字段摘录）、\n"
    "结构类型（仅填「普通」或「母子结构」；合同「契约型【开放式】」「合伙型」是组织形式，不代表母子结构；"
    "合同无「母基金」「子基金」「FOF」「基金中基金」等母子结构专项表述→填「普通」；"
    "此字段无专项原文，字段摘录可不填）、"
    "海外基金（否/是；合同无「QDII」「境外募集」「跨境」「海外注册」等境外相关表述→默认否；不得留空）、"
    "母基金代码、产品分类、\n"
    "首次申购起点（⚠️只填金额+「万」如「100万」；禁止输出合同原文句子；合同写「不低于100万元人民币」→「100万」）、"
    "追加起点（⚠️只填金额+「万」如「1.0万」；禁止输出合同原文句子；合同写「不低于【1】万元人民币」→「1.0万」；无限制→「无追加起点限制」）、"
    "是否封闭（封闭/不封闭；合同明确约定封闭期→封闭；合同表述为「契约型开放式」「合伙型开放式」或运作方式章节无封闭期条款→不封闭；"
    "字段摘录取「基金的运作方式」章节原句，如「契约型【开放式】」，而非风险揭示段落）、封闭方式、封闭期、锁定期、"
    "最低持有类型（仅填「金额」或留空；合同有「赎回后持有资产净值不低于X万元」→填「金额」；合同无此限制→留空）、"
    "最低持有数量（⚠️只填金额+「万」如「100万」；禁止输出原文句子；合同写「赎回后持有基金资产净值不低于100万元」→「100万」；合同无明确最低持有限制→留空）、"
    "最小变动单位（⚠️只填金额+「万」如「1.0万」；禁止输出原文句子；"
    "仅当合同写「以X万元为单位递增」「超出起点部分以X万元整数倍追加」等递增单位表述时才填；"
    "「每次追加申购金额不低于X万元」是追加起点，不是最小变动单位；合同未写递增单位→留空）、\n"
    "开放日规则（格式固定：「申购、赎回｜每周X开放、非交易日向后递推」；多开放日用「/」分隔；"
    "不填入成立日期；若合同封闭期内不开放则前缀改为「赎回｜」）、\n"
    "产品类型（协会）（须从投资限制/范围中的资产占比约束独立判断，仅填以下之一；⚠️禁止在类别名称后追加「基金」二字，合同写「混合类基金」→输出「混合类」：\n"
    "  权益类：合同明确规定≥80%总资产投于股票等权益类；\n"
    "  固定收益类：≥80%总资产投于债券等固收类；\n"
    "  期货和衍生品类：≥80%总资产投于期货/衍生品；\n"
    "  私募证券投资母基金：主要投于其他私募基金/资管产品；\n"
    "  混合类：80%约束分母为「已投资产」而非总资产、或同时列举多类资产、或无单类≥80%总资产约束；\n"
    "  ⚠️「已投资产」≠「总资产」：「不低于已投资产80%」→混合类，不属于权益类/固收类）、\n"
    "预警线（⚠️禁止输出「本基金设置预警线…」等合同原文句子，只填净值数值。三种情形：\n"
    "  ①不分级基金有设置：填「X元」如「0.85元」；合同写「预警线【0.75】元」或「净值为0.8500元设置为预警线」→「0.75元」/「0.85元」\n"
    "  ②分级结构基金有设置：即使合同按整体净值设置预警线，也须按份额类别分列，"
    "格式「主份额/X元、A份额/X元、B份额/X元、C份额/X元」（有哪类写哪类，各类填同一数值），用「、」分隔；\n"
    "  示例：合同写「预警线【0.75】元」且份额结构=分级（有A/B/C类）→「主份额/0.75元、A份额/0.75元、B份额/0.75元、C份额/0.75元」\n"
    "  ③不设置预警线→「无」）、"
    "止损线（⚠️禁止输出「本基金设置止损线…」等合同原文句子，只填净值数值。三种情形：\n"
    "  ①不分级基金有设置：填「X元」如「0.80元」；合同写「止损线【0.70】元」→「0.70元」\n"
    "  ②分级结构基金有设置：格式同预警线，各份额填同一止损值；\n"
    "  示例：合同写「止损线【0.70】元」且份额结构=分级（有A/B/C类）→「主份额/0.70元、A份额/0.70元、B份额/0.70元、C份额/0.70元」\n"
    "  ③不设置→「无」）、"
    "投资目标、投资范围、投资策略、投资限制、风险收益特征、"
    "业绩比较基准（⚠️合同含「不设置业绩比较基准」「不设置」等→输出「无」；禁止输出合同原文句子；否则摘录基准描述）、"
    "投资经理信息（格式：「姓名（实际）」，多人用「、」分隔；禁止填写任职时间或日期）、\n"
    "销售机构信息、"
    "冷静期回访（合同有专项条款则摘录核心约定；无明确约定则固定填：「合同无明确约定（普通投资者默认需要回访，专业投资者默认不需要回访）」；不得留空）、"
    "双录（合同有双录条款则摘录；无则固定填：「普通投资者首次购买需智能自助双录」；不得留空）、\n"
    "投资收益分配（合同无定期强制分配条款则固定填「不分配」；有强制分配方案则摘录关键约定；不得留空）、\n"
    "风险等级（R1/R2/R3/R4/R5）\n\n"
    "【字段摘录】键名「字段摘录」，对象；键为产品要素字段名（仅填写有抽取值的字段），"
    "值为合同中直接支撑该字段值的原文句子（一字不改，1-2句为宜）；"
    "长文本字段（投资目标/投资范围/投资策略/投资限制/风险收益特征/业绩比较基准）"
    "可只摘首句或关键句，无需全文；无摘录依据的字段不填。\n\n"
    "【锁定期子表】键名「锁定期子表」，值为数组；列名须与「份额锁定期导入模板」一致，"
    "每元素对象须包含下列键（合同无对应信息则留空字符串，键不可省略）："
    "产品名称、份额类型、锁定期、投资者类型、客户名称、客户证件类型、客户证件号码、"
    "锁定时间、起始规则、解锁方式、解锁批次、继承原交易锁定期、生效时间、原文（可选）。\n"
    "  · 有锁定期条款时至少填：锁定期（有/无）、锁定时间（如90天/6个月/2年）；"
    "产品名称=基金全称；份额类型填 A份额/B份额 或 全部\n"
    "  · 投资者类型：全部投资者/一般投资者/管理人及员工等（合同区分时各写一行）\n"
    "  · 客户证件类型、客户证件号码：仅合同点名单一投资者时填写，否则留空\n"
    "  · 生效时间、解锁批次等运营字段：合同无则留空\n"
    "  · 原文：同一锁定期段落只在首行填，其余行留空；无锁定期规则时输出 []\n"
    "  示例：\"锁定期子表\":[{\"产品名称\":\"\",\"份额类型\":\"全部\",\"锁定期\":\"有\","
    "\"投资者类型\":\"一般投资者\",\"客户名称\":\"\",\"客户证件类型\":\"\",\"客户证件号码\":\"\","
    "\"锁定时间\":\"90天\",\"起始规则\":\"\",\"解锁方式\":\"\",\"解锁批次\":\"\","
    "\"继承原交易锁定期\":\"\",\"生效时间\":\"\",\"原文\":\"\"}]\n\n"
    "【份额分级子表】键名「份额分级子表」，值为数组；列名须与「分级份额导入模板」一致，"
    "每元素对象须包含下列键（合同无对应信息则留空字符串，键不可省略）："
    "基金全称、基金代码、分级份额名称、分级份额简称、分级份额代码、代码类型、分级类型、"
    "实际成立日期、投资起始日、预警线、止损线、预警止损原文、原文（可选）。\n"
    "  · 合同有 A/B/C/D 等分级份额时，每个份额一行；无分级时输出 []\n"
    "  · 基金代码、分级份额代码：合同通常无运营编码，留空\n"
    "  · 代码类型：必填，填 A份额/B份额/C份额/D份额（与简称 A/B/C/D 对应）\n"
    "  · 分级份额名称：「基金全称 + 类别后缀」，如「石云优选成长2号私募证券投资基金A类」；"
    "必须带字母后缀，禁止输出无后缀的纯基金全称\n"
    "  · 分级份额简称：仅填类别字母，如「A」「B」「C」「D」\n"
    "  · 实际成立日期、投资起始日：合同无则留空\n"
    "  · 预警线/止损线：从「（十一）基金的预警与止损」提取；填纯数字（如 0.850）或「无」；"
    "合同说「不设置」「不设」时填「无」\n"
    "  · 预警止损原文：一字不改引用（十一）中说明预警线/止损线的那一句原文；"
    "多行份额共用同一条时只在首行填，其余行留空字符串\n"
    "  · 原文：引用合同中专门描述该份额类别名称/定义的原文句子；每行各自填写本行份额对应的原文，"
    "勿跨行共用 A 类原文；勿把预警止损段落写入此字段\n"
    "  示例（不设置）：\"预警线\":\"无\",\"止损线\":\"无\","
    "\"预警止损原文\":\"本基金不设置预警线、止损线。\"\n"
    "  示例（有值）：\"预警线\":\"0.850\",\"止损线\":\"0.800\","
    "\"预警止损原文\":\"本基金设置预警线0.850元，止损线0.800元。\"\n"
    "  完整示例：\"份额分级子表\":[{\"基金全称\":\"\",\"基金代码\":\"\","
    "\"分级份额名称\":\"石云福禄1000指数增强一号A类\",\"分级份额简称\":\"A\","
    "\"分级份额代码\":\"\",\"代码类型\":\"A份额\",\"分级类型\":\"\","
    "\"实际成立日期\":\"\",\"投资起始日\":\"\",\"预警线\":\"无\",\"止损线\":\"无\","
    "\"预警止损原文\":\"本基金不设置预警线、止损线。\",\"原文\":\"\"}]\n\n"
    "【开放日原文】键名「开放日原文」，一字不改引用申购赎回章节中说明何时开放的原文"
    "（每月第X个交易日、封闭期内特殊安排、申购赎回时间窗口等）；"
    "不引用确认流程、款项划付、费用计算等无关内容；无相关内容则留空字符串"
)


async def extract_product_combined_llm(
    client: LlmClient | None,
    full_text: str,
    *,
    fund_name: str | None,
) -> tuple[
    dict[str, FieldValue],
    list[LockPeriodRow],
    list[ShareClassRow],
    str | None,
    list[ExtractionWarning],
]:
    """Combined extraction of all product element fields, lock periods, share classes, open day.

    Returns:
        (product_fields, lock_rows, share_rows, open_day_raw, warnings)
    """
    if not client or not client.available:
        return {}, [], [], None, []

    text = full_text.strip()
    if not text:
        return {}, [], [], None, []

    user = (
        f"【合同原文】\n{text_for_llm_prompt(text)}"
        + f"\n\n【基金全称】{fund_name or '（未知）'}\n\n请仅输出 JSON 对象。"
    )
    messages = [
        {"role": "system", "content": _PRODUCT_SYSTEM},
        {"role": "user", "content": user},
    ]

    settings = get_settings()
    last_err: str | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            parsed = await client.chat_json(messages, _ProductCombinedResponse)

            field_snippets_map: dict[str, str] = {
                k: excerpt_for_display(v)
                for k, v in (parsed.字段摘录 or {}).items()
                if v and str(v).strip()
            }
            all_data = parsed.model_dump(
                exclude={"锁定期子表", "份额分级子表", "开放日原文", "字段摘录"}
            )
            effective_fund = fund_name or str(all_data.get("基金全称") or "").strip() or None

            # Extract lock periods and share classes (typed sub-tables)
            lock_rows = [
                r for r in parsed.锁定期子表
                if any(
                    v
                    for k, v in r.model_dump().items()
                    if k != "原文" and v is not None and str(v).strip()
                )
            ]
            lock_group_snip = ""
            for r in lock_rows:
                _normalize_lock_row(r, effective_fund)
                row_snip = (getattr(r, "原文", None) or r.model_dump().get("原文") or "").strip()
                if row_snip and not lock_group_snip:
                    lock_group_snip = excerpt_for_display(row_snip)
            if not lock_group_snip:
                lock_group_snip = field_snippets_map.get("锁定期") or field_snippets_map.get("首次申购起点") or ""
            apply_row_group_snippet(lock_rows, lock_group_snip)

            share_rows = [
                r for r in parsed.份额分级子表
                if any(
                    v
                    for k, v in r.model_dump().items()
                    if k != "原文" and v is not None and str(v).strip()
                )
            ]
            share_group_snip = ""
            for r in share_rows:
                if effective_fund and not r.基金全称:
                    r.基金全称 = effective_fund
                _infer_share_code_type(r)
                row_snip = (getattr(r, "原文", None) or r.model_dump().get("原文") or "").strip()
                if row_snip:
                    if not r.snippet:
                        r.snippet = excerpt_for_display(row_snip)
                    if not share_group_snip:
                        share_group_snip = excerpt_for_display(row_snip)
            if not share_group_snip:
                share_group_snip = (
                    field_snippets_map.get("份额结构") or field_snippets_map.get("基金全称") or ""
                )
            apply_row_group_snippet(share_rows, share_group_snip)

            open_day_raw = (parsed.开放日原文 or "").strip() or None

            # DeepSeek sometimes puts field values inside 字段摘录 instead of
            # top-level keys. Fall back to 字段摘录 values when all_data is empty.
            # The values may be raw context sentences like "私募基金名称：石云xxx"；
            # strip the "label：" prefix to recover the clean field value.
            if not all_data and parsed.字段摘录:
                all_data = {
                    k: _clean_snippet_value(str(v).strip())
                    for k, v in parsed.字段摘录.items()
                    if v and str(v).strip()
                }
                field_snippets_map = {}  # values already ARE the field values here

            # Extract all product element fields from the full dump
            # (includes extra fields captured via extra="allow")
            product_fields: dict[str, FieldValue] = {}
            for key, val in all_data.items():
                if val is None:
                    continue
                value = str(val).strip()
                if not value:
                    continue
                snip = field_snippets_map.get(key)
                if not snip:
                    snip = resolve_field_snippet(key, text, value)
                product_fields[key] = FieldValue(
                    value=value,
                    confidence="medium",
                    source="llm",
                    snippet=snip,
                )
            if open_day_raw and "开放日规则" in product_fields:
                product_fields["开放日规则"].snippet = excerpt_for_display(open_day_raw)

            # Semantic retry: LLM returned valid JSON but extracted no product fields.
            if not product_fields and attempt < settings.llm_max_retries:
                last_err = "LLM returned valid JSON but no product fields were extracted"
                continue

            return product_fields, lock_rows, share_rows, open_day_raw, []

        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            if attempt >= settings.llm_max_retries:
                break

    return {}, [], [], None, [
        ExtractionWarning(
            field="product_combined",
            code="llm_product_combined_failed",
            message=last_err or "unknown",
            suggestion="请检查 OPENAI_API_KEY 与网络连接后重试",
        )
    ]
