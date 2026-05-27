from __future__ import annotations

import re

from backend.app.extract.schemas import LockPeriodRow

_DURATION = re.compile(r"(\d+(?:\.\d+)?)\s*(天|月|年|开放日)")
_MULTI_SHARE = re.compile(
    r"[ABCD]\s*类\s*[/、]\s*[ABCD]\s*类|"
    r"(?:A|B|C|D)\s*类.*(?:A|B|C|D)\s*类",
    re.IGNORECASE,
)


def normalize_lock_row(row: LockPeriodRow, *, combined_text: str = "") -> LockPeriodRow:
    """CRM 语义：锁定期=有/无；时长在锁定时间；多份额类→全部。"""
    data = row.model_dump()
    lock_period = data.get("锁定期")
    if lock_period:
        text = str(lock_period).strip()
        m = _DURATION.search(text)
        if m:
            if not data.get("锁定时间"):
                data["锁定时间"] = f"{m.group(1)}{m.group(2)}"
            data["锁定期"] = "有"
        elif text in ("无", "无锁定期", "不设锁定期"):
            data["锁定期"] = "无"
        elif text not in ("有", "无") and re.search(r"\d", text):
            data["锁定期"] = "有"

    share = (data.get("份额类型") or "").strip()
    if share:
        if _MULTI_SHARE.search(share) or len(set(re.findall(r"([ABCD])\s*类", share, re.I))) >= 2:
            data["份额类型"] = "全部"
        elif re.fullmatch(r"[ABCD]类", share, re.I) and combined_text:
            if re.search(r"本基金设置的份额锁定期限|份额锁定期限为", combined_text):
                data["份额类型"] = "全部"
    elif combined_text and re.search(
        r"本基金设置的份额锁定期限|份额锁定期限为", combined_text
    ):
        data["份额类型"] = "全部"

    return LockPeriodRow(**data)


_FILL_FROM_RULE = (
    "锁定期",
    "锁定时间",
    "份额类型",
    "投资者类型",
    "起始规则",
    "解锁方式",
    "解锁批次",
    "继承原交易锁定期",
)


def _patch_lock_row(
    primary: LockPeriodRow,
    secondary: LockPeriodRow,
    *,
    combined_text: str = "",
) -> LockPeriodRow:
    row = normalize_lock_row(primary, combined_text=combined_text)
    patched = row.model_dump()
    other = normalize_lock_row(secondary, combined_text=combined_text).model_dump()
    for key in _FILL_FROM_RULE:
        if not patched.get(key) and other.get(key):
            patched[key] = other[key]
    if not patched.get("产品名称") and other.get("产品名称"):
        patched["产品名称"] = other["产品名称"]
    return LockPeriodRow(**patched)


def _dual_investor_rule_rows(rule_rows: list[LockPeriodRow]) -> bool:
    types = {r.投资者类型 for r in rule_rows if r.投资者类型}
    return len(rule_rows) >= 2 and len(types) >= 2


def merge_lock_rows(
    llm_rows: list[LockPeriodRow],
    rule_rows: list[LockPeriodRow],
    *,
    combined_text: str = "",
) -> list[LockPeriodRow]:
    """Prefer per-investor rule rows when subscription chapter defines split lock periods."""
    if not llm_rows:
        return rule_rows
    if not rule_rows:
        return [
            normalize_lock_row(raw, combined_text=combined_text) for raw in llm_rows
        ]

    if _dual_investor_rule_rows(rule_rows):
        out: list[LockPeriodRow] = []
        for rule in rule_rows:
            match = next(
                (
                    lr
                    for lr in llm_rows
                    if lr.投资者类型 and lr.投资者类型 == rule.投资者类型
                ),
                None,
            )
            base = match if match is not None else llm_rows[0]
            out.append(_patch_lock_row(rule, base, combined_text=combined_text))
        return out

    rule = rule_rows[0]
    out: list[LockPeriodRow] = []
    for raw in llm_rows:
        match_rule = next(
            (
                rr
                for rr in rule_rows
                if raw.投资者类型 and rr.投资者类型 == raw.投资者类型
            ),
            rule,
        )
        out.append(_patch_lock_row(raw, match_rule, combined_text=combined_text))
    return out
