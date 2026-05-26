from __future__ import annotations

import re
from typing import Any

from backend.app.extract.schemas import FieldValue, LockPeriodRow

_RE_LOCK_TIME = re.compile(
    r"(\d+(?:\.\d+)?)\s*(天|月|年|开放日)", re.IGNORECASE
)
_RE_START_RULE = re.compile(
    r"交易(申请|确认)日[（(]?(含|不含)[）)]?"
)
_RE_UNLOCK = re.compile(r"(一次性解锁|分批解锁)")


def _field_text(fv: FieldValue | dict | None) -> str | None:
    if fv is None:
        return None
    if isinstance(fv, dict):
        val = fv.get("value")
    else:
        val = fv.value
    if val is None or str(val).strip() == "":
        return None
    return str(val).strip()


def extract_lock_periods_rules(
    fund_name: str | None,
    lock_summary: FieldValue | dict | None,
    subscription_text: str,
) -> list[LockPeriodRow]:
    lock_text = _field_text(lock_summary) or ""
    combined = f"{lock_text}\n{subscription_text}"
    if not fund_name and not lock_text:
        return []

    has_lock = bool(lock_text) and not re.search(r"无锁定期|不设锁", lock_text)
    row = LockPeriodRow(
        产品名称=fund_name,
        锁定期="有" if has_lock else ("无" if lock_text else None),
        投资者类型="全部投资者" if has_lock else None,
    )

    time_m = _RE_LOCK_TIME.search(combined)
    if time_m:
        row.锁定时间 = f"{time_m.group(1)}{time_m.group(2)}"

    start_m = _RE_START_RULE.search(combined)
    if start_m:
        inc = start_m.group(2)
        row.起始规则 = f"交易{start_m.group(1)}日（{inc}）"

    unlock_m = _RE_UNLOCK.search(combined)
    if unlock_m:
        row.解锁方式 = unlock_m.group(1)

    share_m = re.search(r"(A|B|C|D)\s*类(?:份额)?", combined)
    if share_m:
        row.份额类型 = f"{share_m.group(1)}份额"

    if not any(
        getattr(row, f) for f in ("锁定期", "锁定时间", "份额类型", "起始规则")
    ):
        if not has_lock and not lock_text:
            return []
    return [row]
