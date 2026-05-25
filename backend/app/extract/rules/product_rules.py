from __future__ import annotations

import re
from typing import Any

from backend.app.extract.schemas import FieldValue

_RE_MANAGER = re.compile(
    r"私募基金管理人[：:\s]*([^\n\r，,；;]+)", re.IGNORECASE
)
_RE_CUSTODIAN = re.compile(
    r"私募基金托管人[：:\s]*([^\n\r，,；;]+)", re.IGNORECASE
)
_RE_ADVISOR = re.compile(r"投资顾问[：:\s]*([^\n\r，,；;]+)")
_RE_FILING = re.compile(r"备案编码[：:\s]*([A-Za-z0-9]+)")
_RE_DATE = re.compile(
    r"(成立日期|备案日期)[：:\s]*(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})"
)
_RE_SUBSCRIPTION_WAN = re.compile(
    r"(首次申购|追加申购|追加).*?(\d+(?:\.\d+)?)\s*万", re.IGNORECASE
)
_RE_CONFIRM = re.compile(r"(T\+\d+[^。\n]{0,20}确认|交易确认[^。\n]{0,30})")
_RE_STOP_LINES = re.compile(
    r"(止损线|预警线)[：:\s]*(\d+(?:\.\d+)?)\s*元?", re.IGNORECASE
)


def _fv(
    value: str | float | None,
    *,
    snippet: str,
    block_id: str | None = None,
    section_id: str | None = None,
) -> FieldValue:
    return FieldValue(
        value=value,
        confidence="high",
        source="rule",
        block_id=block_id,
        section_id=section_id,
        snippet=snippet[:500] if snippet else None,
    )


def _first_match_in_blocks(
    document: dict[str, Any], pattern: re.Pattern[str], group: int = 1
) -> tuple[str | None, str, str | None, str | None]:
    for block in document.get("blocks") or []:
        text = ""
        if block.get("type") == "paragraph":
            text = str(block.get("text") or "")
        elif block.get("type") == "table":
            rows = block.get("rows") or []
            text = "\n".join("\t".join(str(c) for c in row) for row in rows)
        m = pattern.search(text)
        if m:
            return (
                m.group(group).strip(),
                text,
                block.get("id"),
                block.get("section_id"),
            )
    return None, "", None, None


def extract_product_rules(
    document: dict[str, Any],
    windows: dict[str, str],
) -> dict[str, FieldValue]:
    out: dict[str, FieldValue] = {}
    cover = windows.get("cover_parties", "")

    meta = document.get("metadata") or {}
    fund_name = str(meta.get("title") or "").strip()
    if not fund_name or "合同" in fund_name or len(fund_name) > 80:
        fund_name = ""
    for block in (document.get("blocks") or [])[:20]:
        text = str(block.get("text") or "").strip()
        if re.search(r"私募证券投资基金$", text) and "合同" not in text and len(text) <= 60:
            fund_name = text
            break
    if not fund_name:
        m = re.search(r"([\u4e00-\u9fff0-9A-Za-z]+号私募证券投资基金)", cover)
        if m:
            fund_name = m.group(1).strip()
    if fund_name:
        out["基金全称"] = _fv(fund_name, snippet=fund_name)
        short = fund_name.split("私募")[0].strip() or fund_name[:20]
        out["基金简称"] = _fv(short, snippet=fund_name)

    for field, pattern in (
        ("管理人", _RE_MANAGER),
        ("托管人", _RE_CUSTODIAN),
        ("投资顾问", _RE_ADVISOR),
    ):
        val, snip, bid, sid = _first_match_in_blocks(document, pattern)
        if not val and cover:
            m = pattern.search(cover)
            if m:
                val, snip = m.group(1).strip(), cover[:500]
        if val:
            out[field] = _fv(val, snippet=snip, block_id=bid, section_id=sid)

    filing, snip, bid, sid = _first_match_in_blocks(document, _RE_FILING)
    if filing:
        out["备案编码"] = _fv(filing, snippet=snip, block_id=bid, section_id=sid)

    for block in document.get("blocks") or []:
        text = str(block.get("text") or "")
        for m in _RE_DATE.finditer(text):
            label = m.group(1)
            date_str = f"{m.group(2)}/{int(m.group(3))}/{int(m.group(4))}"
            out[label] = _fv(
                date_str,
                snippet=text,
                block_id=block.get("id"),
                section_id=block.get("section_id"),
            )

    sub_text = windows.get("subscription", "")
    full_text = "\n".join(
        str(b.get("text") or "") for b in document.get("blocks") or [] if b.get("type") == "paragraph"
    )[:200000]
    search_sub = sub_text + "\n" + full_text
    for m in _RE_SUBSCRIPTION_WAN.finditer(search_sub):
        label = "首次申购起点" if "首次" in m.group(1) else "追加起点"
        out[label] = _fv(m.group(2), snippet=m.group(0))

    m = _RE_CONFIRM.search(search_sub)
    if m:
        out["交易确认规则"] = _fv(m.group(1).strip(), snippet=m.group(0))

    inv_text = windows.get("investment", "") + "\n" + cover
    for m in _RE_STOP_LINES.finditer(inv_text):
        label = m.group(1)
        out[label] = _fv(m.group(2), snippet=m.group(0))

    lock_m = re.search(r"锁定期[^。\n]{0,80}", search_sub)
    if lock_m:
        out["锁定期"] = _fv(lock_m.group(0), snippet=lock_m.group(0))

    return out
