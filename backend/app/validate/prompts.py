from __future__ import annotations

import json

from backend.app.validate.schemas import ValidationCandidate

SYSTEM_PROMPT = """你是私募基金合同抽取结果的质检员。仅根据每条记录提供的「摘录」(evidence) 判断「抽取值」(value) 是否与摘录一致、是否合理。

规则：
- value 的核心含义必须在摘录中有依据 → pass
- 摘录过短或无法判断 → warn
- value 与摘录明显矛盾，或 value 在摘录中找不到依据 → fail（见下方非必填例外）
- 当事人字段（管理人、托管人、投资顾问、外包机构）：value 须为机构/公司全称，且全称须出现在摘录中；若摘录写的是另一主体或简称对不上 → fail（管理人、托管人为核心必填；投资顾问等合同未聘机构时 value 为空则不输出该校验项）
- 每条 item 的 reason 必须为非空字符串（禁止 null）
- 预警线/止损线：摘录出现「不设置预警线、止损线」或同时否定两者时，value 为「无」→ pass
- 基金面值/币种：摘录含「初始募集面值」且金额为 X元 时，面值可 pass；未写「人民币」但以元计价、且无美元/港币等外币时，币种「人民币现钞」可 pass
- 追加起点为「无追加起点限制」且最小变动单位摘录为「追加不低于1万元」时，两者不矛盾
- 申赎表「计费方式」：摘录含「申购份额=（申购金额-申购费用）/…」或「申购费用=申购金额×费率/(1+费率)」→ 价内法 pass；含「申购份额=申购金额/(1+申购费率)」→ 价外法 pass。摘录同时含份额分类表与【合同条款·计费公式】时，以公式段为准，勿因表内仅列费率而判 warn

非必填字段（如业绩比较基准、风险收益特征、投资目标/范围/策略/限制、投资顾问、封闭期、锁定期、path_b 路径 B 等）：
- 合同无专节或摘录不足以核对时 → warn，reason 写明「合同未载明或摘录不足，导出可留空」
- 勿对非必填字段使用 fail 要求运营必须改值；只有核心必填（基金全称、管理人）在明显错误时用 fail

禁止引用合同外信息或黄金模板表。只输出 JSON。"""


def build_validation_messages(
    candidates: list[ValidationCandidate],
) -> list[dict[str, str]]:
    payload = [
        {
            "field": c.field,
            "value": c.value,
            "evidence": c.evidence_text,
            "party_field": c.party,
        }
        for c in candidates
    ]
    user_content = (
        "请校验以下字段，返回 JSON："
        '{"items":[{"field":"...","status":"pass|warn|fail","reason":"...","suggestion":null}]}'
        "\n\n字段列表：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
