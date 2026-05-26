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
    elif combined_text and len(set(re.findall(r"([ABCD])\s*类", combined_text, re.I))) >= 2:
        data["份额类型"] = "全部"

    return LockPeriodRow(**data)


def merge_lock_rows(
    llm_rows: list[LockPeriodRow],
    rule_rows: list[LockPeriodRow],
    *,
    combined_text: str = "",
) -> list[LockPeriodRow]:
    """Normalize LLM rows; fill gaps from rule layer."""
    rule = rule_rows[0] if rule_rows else None
    fill_fields = (
        "锁定期",
        "锁定时间",
        "份额类型",
        "起始规则",
        "解锁方式",
        "解锁批次",
        "继承原交易锁定期",
    )
    if not llm_rows:
        return rule_rows
    out: list[LockPeriodRow] = []
    for raw in llm_rows:
        row = normalize_lock_row(raw, combined_text=combined_text)
        if rule:
            patched = row.model_dump()
            rule_d = rule.model_dump()
            for key in fill_fields:
                if not patched.get(key) and rule_d.get(key):
                    patched[key] = rule_d[key]
            if not patched.get("产品名称") and rule_d.get("产品名称"):
                patched["产品名称"] = rule_d["产品名称"]
            row = LockPeriodRow(**patched)
        out.append(row)
    return out
