from __future__ import annotations

import re

PRODUCT_SHEET = "产品要素模板"
PRODUCT_HEADER_ROW = 2
PRODUCT_DATA_ROW = 3

FEE_SHEET = "产品运营费率导入模板"
FEE_HEADER_ROW = 3
FEE_DATA_START_ROW = 4

PRODUCT_DATE_FIELDS = frozenset(
    {
        "成立日期",
        "备案日期",
        "到期日期",
        "清算完成日",
        "清算起始日",
        "封闭期起始日",
    }
)

# Logical field names that may appear on multiple template columns
DUPLICATE_LOGICAL_FIELDS = frozenset({"开放日规则", "止损线"})

FEE_EXTRACTION_TO_TEMPLATE: dict[str, str] = {
    "基金名称": "基金名称",
    "基金代码": "基金代码",
    "运营费类型": "运营费类型",
    "计费频率": "计费频率",
    "计费基准": "计费基准",
    "rate_annual_pct": "费率（单位：%/年）",
    "费率（%/年）": "费率（单位：%/年）",
    "费率（单位：%/年）": "费率（单位：%/年）",
    "固定金额": "固定金额",
    "计费起始日期": "计费起始日期",
    "计费截止日期": "计费截止日期",
}


def normalize_header(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"【[^】]*】", "", text)
    text = re.sub(r"\s+", "", text)
    return text


def template_header_for_fee_key(key: str) -> str:
    return FEE_EXTRACTION_TO_TEMPLATE.get(key, key)
