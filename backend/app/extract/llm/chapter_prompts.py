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
    "产品类型（协会）": "权益类、期货和衍生品类、混合类、固定收益类、私募证券投资母基金",
    "是否封闭": "封闭/不封闭",
    "是否支持金额赎回": "支持/不支持",
    "是否支持基金转换": "支持/不支持",
    "海外基金": "否/是",
    "结构类型": "普通/母子结构",
    "份额结构": "不分级/分级结构（由基本情况份额分类表/A–D类推断，LLM 可留空）",
    "管理类型": "自主管理型/顾问管理型/银行委外合作(信托通道)/券商委外合作(信托通道)/其他",
    "默认分红方式": "现金分红/红利再投资/投资者意愿/不分配",
    "是否量化/对冲基金": "量化/对冲/非量化对冲",
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
