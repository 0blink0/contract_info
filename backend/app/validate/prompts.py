from __future__ import annotations

import json

from backend.app.validate.schemas import ValidationCandidate

SYSTEM_PROMPT = """你是私募基金合同抽取结果的质检员。仅根据每条记录提供的「摘录」(evidence) 判断「抽取值」(value) 是否与摘录一致、是否合理。

规则：
- value 的核心含义必须在摘录中有依据 → pass
- 摘录过短或无法判断 → warn
- value 与摘录明显矛盾，或 value 在摘录中找不到依据 → fail
- 当事人字段（管理人、托管人、投资顾问、外包机构）：value 须为机构/公司全称，且全称须出现在摘录中；若摘录写的是另一主体或简称对不上 → fail

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
