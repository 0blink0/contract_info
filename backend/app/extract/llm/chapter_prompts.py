from __future__ import annotations

from backend.app.extract.field_catalog import (
    CHAPTER_FIELDS,
    MANUAL_ONLY_PRODUCT,
    SKIP_PRODUCT_FIELDS,
)
from backend.app.extract.text_limits import text_for_llm_prompt

_ENUM_HINTS: dict[str, str] = {
    "风险等级": "R1/R2/R3/R4/R5",
    "基金面值": "1/100/1000",
    "产品类型（协会）": (
        "【重要】禁止直接使用合同中「基金的类型：XX类」或「基金类型：XX类」标注值，"
        "须从投资范围/投资限制章节的资产占比约束独立判断，仅填以下5类之一：\n"
        "权益类：合同明确规定≥80%【总资产】投于股票等权益类资产；\n"
        "固定收益类：合同明确规定≥80%【总资产】投于债券/固定收益类资产；\n"
        "期货和衍生品类：合同明确规定≥80%【总资产】投于期货/衍生品；\n"
        "私募证券投资母基金：合同规定主要投于其他私募基金/资管产品；\n"
        "混合类：以下任一情形→混合类：①80%约束分母为「已投资产」而非总资产"
        "（如「不低于本基金已投资产的80%」）；②同时列举多类资产；③无单类≥80%总资产约束。\n"
        "⚠️「已投资产」≠「总资产」：「不低于已投资产80%」属混合类，不属于权益类/固收类。\n"
        "若投资范围/限制文本不在本窗口，留空。"
    ),
    "是否封闭": (
        "封闭/不封闭；"
        "封闭 = 合同设有封闭期，在封闭期内不开放申购赎回"
        "（含「满足XX条件后方可申请赎回」等条件性开放，有封闭期即为封闭）；"
        "不封闭 = 无封闭期约定，开放式运作"
    ),
    "是否支持金额赎回": "支持/不支持",
    "是否支持基金转换": "支持/不支持",
    "海外基金": "否/是",
    "结构类型": "普通/母子结构",
    "份额结构": "不分级/分级结构（由基本情况份额分类表/A–D类推断，LLM 可留空）",
    "计费频率": "按日/按月/按季/按年；「每日计提」「逐日计提」→按日；无明确则留空",
    "计费基准": "前一日资产净值/期间均值/其他；无明确说明则留空",
    "年计提天数": "实际天数/365/360；「当年实际天数」「÷N（N为当年天数）」→实际天数；无明确则留空",
    "费用计算方式": "系统计算/管理人计算；合同含「每日计提」「自动扣划」→系统计算；无明确说明则留空",
    "管理类型": (
        "自主管理型/顾问管理型/银行委外合作(信托通道)/券商委外合作(信托通道)/其他；"
        "无管理类型标签时推断：合同明确聘请「投资顾问」负责投资决策→顾问管理型；"
        "管理人自主投资决策（或无顾问条款）→自主管理型；无法确定则留空"
    ),
    "默认分红方式": "现金分红/红利再投资/投资者意愿/不分配",
    "是否量化/对冲基金": "量化/对冲/非量化对冲",
    "量化策略": "CTA/股票多空/市场中性/统计套利/指数增强/其他量化；合同无明确策略名称则留空",
    "冷静期回访": "暂不实施/实施（如有具体要求则摘录关键条款）；合同无专条则留空",
    "双录": "暂不实施/实施；合同无专条则留空",
}


def build_messages(window_key: str, text: str) -> list[dict[str, str]]:
    fields = CHAPTER_FIELDS.get(window_key, [])
    field_list = "、".join(fields) if fields else "（无额外字段）"
    hints = []
    for name in fields:
        if name in _ENUM_HINTS:
            hints.append(f"{name}：{_ENUM_HINTS[name]}")
    hint_block = "\n".join(hints) if hints else "（无额外枚举提示）"

    system = (
        "你是私募基金合同要素抽取助手。仅根据给定合同片段输出一个 JSON 对象，"
        "键名为中文（与需抽取字段一致），值为字符串；无法确定则该键为空字符串。"
        "日期尽量规范为 yyyy/m/d。禁止输出解释、markdown 或多余键。"
        f"以下字段勿编造（合同无则留空）：{'、'.join(sorted(MANUAL_ONLY_PRODUCT | SKIP_PRODUCT_FIELDS))}。"
    )
    user = (
        f"【章节窗口】{window_key}\n"
        f"【需抽取字段】{field_list}\n"
        f"【枚举参考】\n{hint_block}\n\n"
        f"【合同片段】\n{text_for_llm_prompt(text)}\n\n"
        "请仅输出 JSON 对象。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_rag_history_block(rag_cases: list[dict[str, str]] | None) -> str:
    cases = rag_cases or []
    if not cases:
        return ""

    lines = ["【历史案例参考】"]
    for idx, case in enumerate(cases, start=1):
        field_name = str(case.get("field_name", "") or "").strip()
        field_value = str(case.get("field_value", "") or "").strip()
        snippet = str(case.get("snippet", "") or "").strip()
        lines.append(f"{idx}. 字段名：{field_name}")
        lines.append(f"   字段值：{field_value}")
        lines.append(f"   原文摘录：{text_for_llm_prompt(snippet)}")
    return "\n".join(lines)
