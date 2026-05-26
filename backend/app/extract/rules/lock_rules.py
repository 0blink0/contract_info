from __future__ import annotations

import re

from backend.app.extract.schemas import FieldValue, LockPeriodRow

_RE_LOCK_TIME = re.compile(
    r"(\d+(?:\.\d+)?)\s*(天|月|年|开放日)", re.IGNORECASE
)
_RE_START_RULE = re.compile(
    r"交易(申请|确认)日[（(]?(含|不含)[）)]?"
)
_RE_UNLOCK = re.compile(r"(一次性解锁|分批解锁)")
_RE_UNLOCK_BATCH = re.compile(r"分批解锁[^。\n]{0,40}?(\d+)\s*(?:个)?批")
_RE_INHERIT = re.compile(r"转让|转换|红利")
_INVESTOR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("一般投资者", re.compile(r"一般投资者|普通投资者|其他投资者")),
    (
        "管理人及其员工",
        re.compile(r"管理人[及其和与]?员工|员工跟投|管理人跟投|管理人及其员工"),
    ),
)
_RE_EMPLOYEE_LOCK = re.compile(
    r"管理人[及其和与]?员工|员工跟投|管理人跟投"
)
_RE_GENERAL_LOCK_CLAUSE = re.compile(r"份额锁定期限|本基金设置.{0,20}锁定期")


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


def _share_type_from_text(combined: str) -> str | None:
    if re.search(
        r"[ABCD]\s*类\s*[/、]\s*[ABCD]\s*类",
        combined,
        re.IGNORECASE,
    ):
        return "全部"
    letters = set(re.findall(r"([ABCD])\s*类", combined, re.IGNORECASE))
    if len(letters) >= 2:
        return "全部"
    if len(letters) == 1:
        return f"{letters.pop()}类"
    return None


def _build_lock_row(
    fund_name: str | None,
    combined: str,
    *,
    has_lock: bool,
    lock_text: str,
    investor_type: str | None = None,
) -> LockPeriodRow:
    row = LockPeriodRow(
        产品名称=fund_name,
        锁定期="有" if has_lock else ("无" if lock_text else None),
        投资者类型=investor_type,
    )

    time_m = _RE_LOCK_TIME.search(combined)
    if time_m:
        row.锁定时间 = f"{time_m.group(1)}{time_m.group(2)}"

    start_m = _RE_START_RULE.search(combined)
    if start_m:
        row.起始规则 = f"交易{start_m.group(1)}日（{start_m.group(2)}）"

    unlock_m = _RE_UNLOCK.search(combined)
    if unlock_m:
        row.解锁方式 = unlock_m.group(1)

    batch_m = _RE_UNLOCK_BATCH.search(combined)
    if batch_m:
        row.解锁批次 = batch_m.group(1)

    if _RE_INHERIT.search(combined):
        parts: list[str] = []
        if "转让" in combined:
            parts.append("转让")
        if "转换" in combined:
            parts.append("转换")
        if "红利" in combined:
            parts.append("红利再投")
        row.继承原交易锁定期 = "，".join(parts) if parts else "转让，转换，红利再投"

    share = _share_type_from_text(combined)
    if share:
        row.份额类型 = share

    return row


def extract_lock_periods_rules(
    fund_name: str | None,
    lock_summary: FieldValue | dict | None,
    subscription_text: str,
) -> list[LockPeriodRow]:
    lock_text = _field_text(lock_summary) or ""
    if not lock_text.strip():
        return []

    combined = f"{lock_text}\n{subscription_text}"
    if not fund_name and not lock_text:
        return []

    has_lock = bool(lock_text) and not re.search(r"无锁定期|不设锁", lock_text)

    investor_hits = [
        label for label, pat in _INVESTOR_PATTERNS if pat.search(combined)
    ]
    if len(investor_hits) >= 2:
        return [
            _build_lock_row(
                fund_name,
                combined,
                has_lock=has_lock,
                lock_text=lock_text,
                investor_type=label,
            )
            for label in investor_hits
        ]

    # 合同常写「员工跟投」条款 + 面向其他投资者的通用锁定期，但未写「一般投资者」四字
    if (
        has_lock
        and _RE_EMPLOYEE_LOCK.search(combined)
        and _RE_GENERAL_LOCK_CLAUSE.search(combined)
    ):
        return [
            _build_lock_row(
                fund_name,
                combined,
                has_lock=has_lock,
                lock_text=lock_text,
                investor_type="一般投资者",
            ),
            _build_lock_row(
                fund_name,
                combined,
                has_lock=has_lock,
                lock_text=lock_text,
                investor_type="管理人及其员工",
            ),
        ]

    row = _build_lock_row(
        fund_name,
        combined,
        has_lock=has_lock,
        lock_text=lock_text,
        investor_type="全部投资者" if has_lock else None,
    )

    if not any(
        getattr(row, f) for f in ("锁定期", "锁定时间", "份额类型", "起始规则")
    ):
        if not has_lock and not lock_text:
            return []
    return [row]
