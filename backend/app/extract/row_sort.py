from __future__ import annotations

import re

from backend.app.extract.schemas import FeeRateRow, SubscriptionFeeRow

_FEE_TYPE_ORDER: list[str] = [
    "管理费",
    "托管费",
    "基金服务费",
    "金融运营服务费",
    "销售服务费",
    "投资顾问费",
]

_SUB_FEE_TYPE_ORDER: list[str] = ["认购费", "申购费", "赎回费"]

_SHARE_LETTER = re.compile(
    r"(?:"
    r"([A-D])类(?:份额)?$|"
    r"证券投资基金([A-D])$|"
    r"一号([A-D])类$"
    r")",
    re.IGNORECASE,
)


def _type_rank(value: str | None, order: list[str]) -> int:
    if not value:
        return len(order) + 1
    try:
        return order.index(value)
    except ValueError:
        return len(order)


def _share_letter_from_fund_name(name: str | None) -> str:
    if not name:
        return "Z"
    m = _SHARE_LETTER.search(name.strip())
    if not m:
        return "Z"
    return (m.group(1) or m.group(2) or m.group(3) or "Z").upper()


def sort_fee_rates(rows: list[FeeRateRow]) -> list[FeeRateRow]:
    """Group by 运营费类型, then A–D within each type."""

    def key(row: FeeRateRow) -> tuple:
        return (
            _type_rank(row.运营费类型, _FEE_TYPE_ORDER),
            _share_letter_from_fund_name(row.基金名称),
            row.基金名称 or "",
        )

    return sorted(rows, key=key)


def sort_subscription_fees(rows: list[SubscriptionFeeRow]) -> list[SubscriptionFeeRow]:
    """Group by 申赎费类型, then share class; tiered 赎回费 rows after flat per-class rows."""

    def key(row: SubscriptionFeeRow) -> tuple:
        is_tier = row.计费基准 == "分段" or bool(row.区间开始 or row.区间结束)
        return (
            _type_rank(row.申赎费类型, _SUB_FEE_TYPE_ORDER),
            1 if is_tier else 0,
            _share_letter_from_fund_name(row.基金名称),
            row.基金名称 or "",
        )

    return sorted(rows, key=key)
