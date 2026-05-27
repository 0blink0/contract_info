from __future__ import annotations

import re

from backend.app.extract.schemas import FieldValue, LockPeriodRow

_RE_LOCK_TIME = re.compile(
    r"(\d+(?:\.\d+)?)\s*(天|月|年|开放日)", re.IGNORECASE
)
_RE_LOCK_NATURAL_DAYS = re.compile(r"(\d+(?:\.\d+)?)\s*个自然日", re.IGNORECASE)
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
_RE_GENERAL_LOCK_CLAUSE = re.compile(
    r"份额锁定期限|本基金设置.{0,24}份额锁定期|基金份额锁定期"
)
_RE_GENERAL_LOCK_SENTENCE = re.compile(
    r"本基金设置的份额锁定期限为[^。]+。"
)
_RE_EMPLOYEE_LOCK_SENTENCE = re.compile(
    r"本基金的管理人[及其和与]?员工[^。]+锁定期[^。]+。"
)
_RE_EMPLOYEE_LOCK_DURATION = re.compile(
    r"员工[^。]{0,120}?(\d+)\s*个月[（(](\d+)\s*个自然日[）)]",
    re.IGNORECASE,
)


def _parse_lock_duration(text: str) -> str | None:
    m = _RE_LOCK_NATURAL_DAYS.search(text)
    if m:
        return f"{m.group(1)}天"
    m = _RE_LOCK_TIME.search(text)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    return None


def _lock_duration_in_subscription(subscription_text: str) -> str | None:
    """Pick lock duration only when adjacent to share-lock wording (not 保存20年等)."""
    for m in _RE_LOCK_NATURAL_DAYS.finditer(subscription_text):
        start = max(0, m.start() - 48)
        window = subscription_text[start : m.end() + 24]
        if re.search(r"份额锁定|锁定期限|持有期低于", window):
            return f"{m.group(1)}天"
    for m in _RE_LOCK_TIME.finditer(subscription_text):
        start = max(0, m.start() - 48)
        window = subscription_text[start : m.end() + 24]
        if re.search(r"份额锁定|锁定期限|持有期低于", window):
            return f"{m.group(1)}{m.group(2)}"
    return None


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


def _lock_excerpt(combined: str) -> str:
    """Narrow window so unrelated 'B类份额' elsewhere does not set 份额类型."""
    m = _RE_GENERAL_LOCK_SENTENCE.search(combined)
    if m:
        return m.group(0)
    m = _RE_GENERAL_LOCK_CLAUSE.search(combined)
    if m:
        start = max(0, m.start() - 10)
        end = min(len(combined), m.end() + 320)
        return combined[start:end]
    emp = _RE_EMPLOYEE_LOCK_SENTENCE.search(combined)
    if emp:
        start = max(0, emp.start() - 80)
        end = min(len(combined), emp.end() + 40)
        return combined[start:end]
    return combined[:400]


def _share_type_from_text(combined: str) -> str | None:
    excerpt = _lock_excerpt(combined)
    if re.search(
        r"[ABCD]\s*类\s*[/、]\s*[ABCD]\s*类",
        excerpt,
        re.IGNORECASE,
    ):
        return "全部"
    letters = sorted(set(re.findall(r"([ABCD])\s*类", excerpt, re.IGNORECASE)))
    if len(letters) >= 2:
        return "全部"
    if len(letters) == 1:
        letter = letters[0]
        if re.search(
            rf"{letter}\s*类[^。\n]{{0,40}}锁定期|锁定期[^。\n]{{0,40}}{letter}\s*类",
            excerpt,
            re.IGNORECASE,
        ):
            return f"{letter}类"
    return None


def _employee_lock_duration(text: str) -> str | None:
    m = _RE_EMPLOYEE_LOCK_DURATION.search(text)
    if m:
        return f"{m.group(2)}天"
    m = re.search(r"员工[^。]{0,120}?(\d+)\s*个自然日", text)
    if m:
        return f"{m.group(1)}天"
    return None


def _general_lock_duration(text: str) -> str | None:
    m = re.search(r"份额锁定期限为\s*(\d+)\s*个自然日", text)
    if m:
        return f"{m.group(1)}天"
    return _lock_duration_in_subscription(text)


def _build_lock_row(
    fund_name: str | None,
    combined: str,
    *,
    has_lock: bool,
    lock_text: str,
    investor_type: str | None = None,
) -> LockPeriodRow:
    duration_source = lock_text or combined
    row = LockPeriodRow(
        产品名称=fund_name,
        锁定期="有" if has_lock else ("无" if lock_text else None),
        投资者类型=investor_type,
    )

    if investor_type == "管理人及其员工":
        dur = _employee_lock_duration(duration_source) or _parse_lock_duration(
            duration_source
        )
    elif investor_type == "一般投资者":
        dur = _general_lock_duration(duration_source) or _parse_lock_duration(
            duration_source
        )
    else:
        dur = _parse_lock_duration(duration_source)

    if dur:
        row.锁定时间 = dur
    elif not row.锁定时间:
        fallback_text = duration_source if investor_type == "管理人及其员工" else combined
        row.锁定时间 = _lock_duration_in_subscription(fallback_text)

    start_m = _RE_START_RULE.search(combined)
    if start_m:
        row.起始规则 = f"交易{start_m.group(1)}日（{start_m.group(2)}）"
    elif "认购份额自基金成立日起算" in combined:
        row.起始规则 = "认购份额自基金成立日起算，申购份额自申购确认日起算"
    elif "申购份额自申购确认日起算" in combined:
        row.起始规则 = "申购份额自申购确认日起算"

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
    elif has_lock:
        row.份额类型 = "全部"

    return row


def _no_lock_row(fund_name: str | None) -> LockPeriodRow:
    """CRM 要求无锁定期也占一行：锁定期=无，全部投资者。"""
    return LockPeriodRow(
        产品名称=fund_name,
        份额类型="全部",
        锁定期="无",
        投资者类型="全部投资者",
    )


def _subscription_implies_lock(subscription_text: str) -> bool:
    if re.search(r"无锁定期|不设锁定期|不设锁", subscription_text):
        return False
    if _RE_GENERAL_LOCK_CLAUSE.search(subscription_text):
        return True
    return _lock_duration_in_subscription(subscription_text) is not None


def _dual_investor_lock_rows(
    fund_name: str | None,
    combined: str,
    *,
    has_lock: bool,
    lock_text: str,
) -> list[LockPeriodRow]:
    gen_snip = _RE_GENERAL_LOCK_SENTENCE.search(combined)
    emp_snip = _RE_EMPLOYEE_LOCK_SENTENCE.search(combined)
    general_text = gen_snip.group(0) if gen_snip else lock_text
    employee_text = emp_snip.group(0) if emp_snip else combined
    return [
        _build_lock_row(
            fund_name,
            combined,
            has_lock=has_lock,
            lock_text=general_text,
            investor_type="一般投资者",
        ),
        _build_lock_row(
            fund_name,
            combined,
            has_lock=has_lock,
            lock_text=employee_text,
            investor_type="管理人及其员工",
        ),
    ]


def extract_lock_periods_rules(
    fund_name: str | None,
    lock_summary: FieldValue | dict | None,
    subscription_text: str,
) -> list[LockPeriodRow]:
    lock_text = _field_text(lock_summary) or ""
    if not lock_text.strip():
        if not fund_name:
            return []
        if _subscription_implies_lock(subscription_text):
            lock_text = _lock_duration_in_subscription(subscription_text) or "有"
        else:
            return [_no_lock_row(fund_name)]

    if re.search(r"^(无|无锁定期|不设锁定期?)$", lock_text.strip()):
        return [_no_lock_row(fund_name)]

    combined = f"{lock_text}\n{subscription_text}"
    if not fund_name and not lock_text:
        return []

    has_lock = bool(lock_text) and not re.search(r"无锁定期|不设锁", lock_text)

    if (
        has_lock
        and _RE_EMPLOYEE_LOCK.search(combined)
        and _RE_GENERAL_LOCK_CLAUSE.search(combined)
    ):
        return _dual_investor_lock_rows(
            fund_name, combined, has_lock=has_lock, lock_text=lock_text
        )

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

    row = _build_lock_row(
        fund_name,
        combined,
        has_lock=has_lock,
        lock_text=lock_text,
        investor_type="全部投资者" if has_lock else None,
    )

    if not has_lock:
        return [_no_lock_row(fund_name)]
    return [row]
