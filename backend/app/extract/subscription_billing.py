"""Apply LLM-inferred billing method to subscription fee rows."""

from __future__ import annotations

from backend.app.extract.schemas import SubscriptionFeeRow


def apply_subscription_billing(
    rows: list[SubscriptionFeeRow],
    billing_by_type: dict[str, str],
) -> None:
    for row in rows:
        fee_type = row.申赎费类型
        if (row.计费方式 or "").strip():
            continue
        if fee_type in ("认购费", "申购费", "赎回费") and billing_by_type.get(fee_type):
            row.计费方式 = billing_by_type[fee_type]
