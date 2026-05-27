from __future__ import annotations

import re
from typing import Any

from backend.app.extract.rules.party_helpers import (
    block_is_risk_disclosure,
    clean_org_name,
    is_valid_party_name,
)
from backend.app.extract.schemas import FieldValue

_RE_MANAGER = re.compile(
    r"(?:私募)?基金管理人[^。\n]{0,50}[：:]\s*"
    r"([^\n\r。]{4,80}?(?:有限公司|有限责任公司|股份有限公司))",
    re.IGNORECASE,
)
_RE_MANAGER_LINE = re.compile(
    r"基金管理人[：:\s]+([^\n\r，,；;]{4,60}?(?:有限公司|有限责任公司|股份有限公司))",
    re.IGNORECASE,
)
_RE_CUSTODIAN = re.compile(
    r"私募基金托管人[^。\n]{0,40}[：:]\s*"
    r"([^\n\r，,；;。]{4,60}?(?:有限公司|有限责任公司|股份有限公司))",
    re.IGNORECASE,
)
_RE_CUSTODIAN_ALT = re.compile(
    r"基金托管人[^。\n]{0,30}[：:]\s*"
    r"([^\n\r，,；;。]{4,60}?(?:有限公司|有限责任公司|股份有限公司))",
    re.IGNORECASE,
)
_RE_ADVISOR_HIRE = re.compile(
    r"聘请[^。\n]{0,20}投资顾问[为是：:\s]+"
    r"([^\n\r，,；;]{4,50}?(?:有限公司|有限责任公司|股份有限公司))",
    re.IGNORECASE,
)
_RE_FILING = re.compile(r"备案编码[：:\s]*([A-Za-z0-9]+)")
_RE_FUND_CODE = re.compile(r"基金代码[：:\s]*([A-Za-z0-9]+)")
_RE_DATE = re.compile(
    r"(成立日期|备案日期|到期日期|清算完成日|清算起始日|投资起始日|封闭期起始日)"
    r"[：:\s]*(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})"
)
_RE_OUTSOURCE = re.compile(
    r"(国泰海通|国泰君安)[^。\n]{0,80}?(?:份额登记|估值核算)",
    re.IGNORECASE,
)
_RE_ORG_FORM = re.compile(
    r"基金组织形式[：:\s]*(契约型|公司型|合伙型)", re.IGNORECASE
)
_RE_ISSUER = re.compile(r"发行机构[：:\s]*([^\n\r，,；;]+)")
_RE_RAISING = re.compile(r"募集期[：:\s]*([^\n\r。]{4,80})")
_RE_MIN_HOLD = re.compile(
    r"最低持有(?:份额|金额|数量)?[：:\s]*(\d+(?:\.\d+)?)\s*(万份|份|元)?",
    re.IGNORECASE,
)
_RE_MIN_HOLD_TYPE = re.compile(r"最低持有(?:类型)?[：:\s]*(金额|份额)")
_RE_CLOSED_PERIOD = re.compile(r"封闭期[：:]\s*([^\n\r。，,；;、]{4,60})")
_RE_NO_STOP_LINES = re.compile(
    r"本基金不设置预警线[、,，\s]*止损线|"
    r"不设置预警线[、,，\s]*止损线|"
    r"未设预警线[、,，\s]*止损线|"
    r"预警线[、,，\s]*止损线[^。\n]{0,16}不设置|"
    r"本基金未设预警止损线|"
    r"未设预警|不设预警",
    re.IGNORECASE,
)
_RE_NOT_CLOSED = re.compile(r"不封闭|不存在封闭期|无封闭期", re.IGNORECASE)
_RE_FIRST_SUB_WAN = re.compile(
    r"首次(?:净)?申购[^。\n]{0,48}?应不低于\s*(\d+(?:\.\d+)?)\s*万元",
    re.IGNORECASE,
)
_RE_ADD_MIN_WAN = re.compile(
    r"追加(?:金额|申购)[^。\n]{0,32}?应不低于\s*(\d+(?:\.\d+)?)\s*万元",
    re.IGNORECASE,
)
_RE_NO_ADD_LIMIT = re.compile(r"无追加起点|不设追加起点|无追加起点限制")
_RE_FACE_VALUE = re.compile(
    r"(?:基金份额的)?初始募集面值[：:\s]*(?:人民币\s*)?([\d.]+)\s*元",
    re.IGNORECASE,
)
_RE_FOREIGN_CURRENCY = re.compile(r"美元|港币|港元|欧元|日元|英镑", re.IGNORECASE)


def _normalize_face_value(amount: str) -> str:
    face = amount.rstrip("0").rstrip(".") if "." in amount else amount
    if face in ("1", "1.0", "1.00", "1.0000"):
        return "1"
    return face


def _stop_lines_snippet(text: str, match: re.Match[str]) -> str:
    """Full sentence/clause so 预警线 and 止损线 share evidence including both terms."""
    start = max(0, text.rfind("\n", 0, match.start()) + 1)
    end = text.find("。", match.end())
    if end != -1 and end - start <= 160:
        return text[start : end + 1].strip()
    chunk = text[start : min(len(text), match.end() + 32)].strip()
    if "止损线" not in chunk and match.end() < len(text):
        extended = text[start : min(len(text), match.end() + 16)].strip()
        if "止损线" in extended:
            chunk = extended
    return chunk


def _currency_from_face_snippet(snippet: str) -> str:
    """面值以「元」计且未写明外币时，视为人民币现钞（行业惯例）。"""
    if _RE_FOREIGN_CURRENCY.search(snippet):
        return "人民币现钞" if "人民币" in snippet else ""
    if "人民币" in snippet or re.search(r"[\d.]+\s*元", snippet):
        return "人民币现钞"
    return ""
_RE_CONFIRM = re.compile(r"(T\+\d+[^。\n]{0,20}确认|交易确认[^。\n]{0,30})")
_RE_STOP_LINES = re.compile(
    r"(止损线|预警线)[：:\s]*(\d+(?:\.\d+)?)\s*元?", re.IGNORECASE
)
_RE_BANK = re.compile(
    r"(募集账户|托管账户|银行账户)[：:\s]*([^\n\r]{10,200})", re.IGNORECASE
)
_RE_RISK_GRADE = re.compile(
    r"风险等级为\s*\[?\s*(R[1-5])\s*\]?", re.IGNORECASE
)
_RE_INV_MANAGER = re.compile(
    r"本基金的投资经理[：:]\s*([^\n\r。；;，,]{2,80})"
)
_RE_INV_MANAGER_ALT = re.compile(
    r"1、本基金的投资经理[：:]\s*([^\n\r。；;，,]{2,80})"
)
_RE_LOCK_DAYS = re.compile(r"份额锁定期限为\s*(\d+)\s*天")
_RE_OPEN_SCHEDULE = re.compile(r"本基金的开放日为[^。\n]{10,300}")
_RE_INV_OBJECTIVE = re.compile(
    r"（二）投资目标[：:\s]*\n?\s*([^（]+?)(?=（三）|$)", re.DOTALL
)
_RE_INV_SCOPE = re.compile(
    r"（三）投资范围[：:\s]*\n?\s*(.*?)(?=（四）投资策略|（四）|$)", re.DOTALL
)
_RE_INV_STRATEGY = re.compile(
    r"（四）投资策略[：:\s]*\s*(.*?)(?=（五）投资限制|（五）|$)", re.DOTALL
)
_RE_INV_LIMITS = re.compile(
    r"（五）投资限制\s*\n?\s*(.*?)(?=（六）|本基金为|$)", re.DOTALL
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


def _block_text(block: dict[str, Any]) -> str:
    if block.get("type") == "table":
        rows = block.get("rows") or []
        return "\n".join("\t".join(str(c) for c in row) for row in rows)
    return str(block.get("text") or "")


def _score_party_match(text: str, *, role: str) -> int:
    score = 0
    if role == "custodian":
        if "私募基金托管人" in text:
            score += 20
        if "简称" in text and "托管人" in text:
            score += 10
        if re.match(r"基金托管人[：:\s]", text.strip()):
            score -= 8
    if role == "manager" and "私募基金管理人" in text:
        score += 15
    return score


def _find_party(
    document: dict[str, Any],
    patterns: list[re.Pattern[str]],
    *,
    prefer_cover: str = "",
    role: str = "manager",
) -> tuple[str | None, str, str | None, str | None]:
    best: tuple[int, str, str, str | None, str | None] | None = None

    def consider(text: str, bid: str | None, sid: str | None) -> None:
        nonlocal best
        for pattern in patterns:
            m = pattern.search(text)
            if not m:
                continue
            name = clean_org_name(m.group(1))
            if not is_valid_party_name(name):
                continue
            score = _score_party_match(text, role=role)
            if best is None or score > best[0]:
                best = (score, name, text[:500], bid, sid)

    if prefer_cover:
        consider(prefer_cover, None, None)

    for block in document.get("blocks") or []:
        if block_is_risk_disclosure(document, block):
            continue
        text = _block_text(block)
        consider(text, block.get("id"), block.get("section_id"))

    if best:
        return best[1], best[2], best[3], best[4]
    return None, "", None, None


def _extract_investment_chapter(inv_text: str) -> dict[str, FieldValue]:
    out: dict[str, FieldValue] = {}
    for label, pattern in (
        ("投资目标", _RE_INV_OBJECTIVE),
        ("投资范围", _RE_INV_SCOPE),
        ("投资策略", _RE_INV_STRATEGY),
        ("投资限制", _RE_INV_LIMITS),
    ):
        m = pattern.search(inv_text)
        if not m:
            continue
        body = re.sub(r"\s+", " ", m.group(1).strip())
        if len(body) >= 8:
            out[label] = _fv(body[:4000], snippet=body[:500])
    return out


def extract_product_rules(
    document: dict[str, Any],
    windows: dict[str, str],
) -> dict[str, FieldValue]:
    out: dict[str, FieldValue] = {}
    cover = windows.get("cover_parties", "")
    inv_text = windows.get("investment", "")
    risk_text = windows.get("risk", "")
    sub_text = windows.get("subscription", "")

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

    val, snip, bid, sid = _find_party(
        document,
        [_RE_MANAGER, _RE_MANAGER_LINE],
        prefer_cover=cover,
        role="manager",
    )
    if val:
        out["管理人"] = _fv(val, snippet=snip, block_id=bid, section_id=sid)

    val, snip, bid, sid = _find_party(
        document,
        [_RE_CUSTODIAN, _RE_CUSTODIAN_ALT],
        prefer_cover=cover,
        role="custodian",
    )
    if val:
        out["托管人"] = _fv(val, snippet=snip, block_id=bid, section_id=sid)

    val, snip, bid, sid = _find_party(document, [_RE_ADVISOR_HIRE], prefer_cover=cover)
    if val:
        out["投资顾问"] = _fv(val, snippet=snip, block_id=bid, section_id=sid)

    for label, pattern in (
        ("备案编码", _RE_FILING),
        ("基金代码", _RE_FUND_CODE),
    ):
        for block in document.get("blocks") or []:
            text = _block_text(block)
            m = pattern.search(text)
            if m:
                out[label] = _fv(
                    m.group(1),
                    snippet=text,
                    block_id=block.get("id"),
                    section_id=block.get("section_id"),
                )
                break

    for block in document.get("blocks") or []:
        text = _block_text(block)
        for m in _RE_DATE.finditer(text):
            label = m.group(1)
            date_str = f"{m.group(2)}/{int(m.group(3))}/{int(m.group(4))}"
            out[label] = _fv(
                date_str,
                snippet=text,
                block_id=block.get("id"),
                section_id=block.get("section_id"),
            )

    m = _RE_OUTSOURCE.search(cover + "\n" + windows.get("basic", ""))
    if not m:
        for block in document.get("blocks") or []:
            text = _block_text(block)
            m = _RE_OUTSOURCE.search(text)
            if m:
                out["外包机构"] = _fv(
                    "国泰海通证券股份有限公司",
                    snippet=m.group(0),
                    block_id=block.get("id"),
                    section_id=block.get("section_id"),
                )
                break
    else:
        out["外包机构"] = _fv("国泰海通证券股份有限公司", snippet=m.group(0))

    for label, pattern in (
        ("基金组织形式", _RE_ORG_FORM),
        ("发行机构", _RE_ISSUER),
    ):
        for block in document.get("blocks") or []:
            text = _block_text(block)
            m = pattern.search(text)
            if m:
                out[label] = _fv(
                    m.group(1).strip(),
                    snippet=text,
                    block_id=block.get("id"),
                    section_id=block.get("section_id"),
                )
                break

    raising_text = windows.get("raising", "") + "\n" + cover
    m = _RE_RAISING.search(raising_text)
    if m and "返还投资人" not in m.group(1):
        out["募集期"] = _fv(m.group(1).strip(), snippet=m.group(0))

    full_text = "\n".join(
        _block_text(b)
        for b in document.get("blocks") or []
        if b.get("type") == "paragraph"
    )[:200000]
    search_sub = sub_text + "\n" + full_text

    m = _RE_FIRST_SUB_WAN.search(search_sub)
    if m:
        out["首次申购起点"] = _fv(f"{m.group(1)}万", snippet=m.group(0))

    m_add = _RE_ADD_MIN_WAN.search(search_sub)
    if m_add:
        amount = m_add.group(1)
        out["最小变动单位"] = _fv(
            f"{amount}万" if not str(amount).endswith("万") else str(amount),
            snippet=m_add.group(0),
        )

    m_no_add = _RE_NO_ADD_LIMIT.search(search_sub)
    if m_no_add:
        out["追加起点"] = _fv("无追加起点限制", snippet=m_no_add.group(0))
    elif m_add and float(m_add.group(1)) <= 1.01:
        out["追加起点"] = _fv("无追加起点限制", snippet=m_add.group(0))

    m = _RE_CONFIRM.search(search_sub)
    if m:
        out["交易确认规则"] = _fv(m.group(1).strip(), snippet=m.group(0))

    m = _RE_MIN_HOLD_TYPE.search(search_sub)
    if m:
        out["最低持有类型"] = _fv(m.group(1), snippet=m.group(0))
    m = _RE_MIN_HOLD.search(search_sub)
    if m:
        unit = m.group(2) or ""
        out["最低持有数量"] = _fv(f"{m.group(1)}{unit}", snippet=m.group(0))

    if not _RE_NOT_CLOSED.search(search_sub):
        m = _RE_CLOSED_PERIOD.search(search_sub)
        if m and "锁定期" not in m.group(1) and "最短持有" not in m.group(1):
            out["封闭期"] = _fv(m.group(1).strip(), snippet=m.group(0))

    stop_search = inv_text + risk_text + full_text[:80000]
    no_stop = _RE_NO_STOP_LINES.search(stop_search)
    if no_stop:
        snippet = _stop_lines_snippet(stop_search, no_stop)
        out["预警线"] = _fv("无", snippet=snippet)
        out["止损线"] = _fv("无", snippet=snippet)
    else:
        for m in _RE_STOP_LINES.finditer(inv_text + "\n" + cover):
            label = m.group(1)
            out[label] = _fv(m.group(2), snippet=m.group(0))

    lock_days = _RE_LOCK_DAYS.search(search_sub)
    if lock_days:
        out["锁定期"] = _fv(f"{lock_days.group(1)}天", snippet=lock_days.group(0))
    else:
        lock_m = re.search(r"锁定期限为\s*(\d+)\s*天", search_sub)
        if lock_m:
            out["锁定期"] = _fv(f"{lock_m.group(1)}天", snippet=lock_m.group(0))

    open_m = _RE_OPEN_SCHEDULE.search(search_sub)
    if open_m:
        out["开放日规则"] = _fv(open_m.group(0).strip(), snippet=open_m.group(0))
    else:
        open_m2 = re.search(
            r"开放日为[^。\n]{10,200}",
            search_sub,
        )
        if open_m2 and "基金管理人办理" not in open_m2.group(0):
            out["开放日规则"] = _fv(open_m2.group(0).strip(), snippet=open_m2.group(0))

    m = _RE_RISK_GRADE.search(risk_text + "\n" + full_text[:80000])
    if m:
        out["风险等级"] = _fv(m.group(1).upper(), snippet=m.group(0))

    for pattern in (_RE_INV_MANAGER, _RE_INV_MANAGER_ALT):
        m = pattern.search(inv_text + "\n" + full_text[:100000])
        if m:
            names = m.group(1).strip().strip("：:")
            if names and "可" not in names[:3] and "变更" not in names:
                out["投资经理"] = _fv(names, snippet=m.group(0))
                out["投资经理信息"] = _fv(names, snippet=m.group(0))
                break

    out.update(_extract_investment_chapter(inv_text))
    if "投资策略" not in out or "投资范围" not in out:
        out.update(_extract_investment_chapter(full_text))

    basic_text = windows.get("basic", "") + "\n" + cover
    m = _RE_FACE_VALUE.search(basic_text)
    if m:
        snippet = m.group(0)
        face = _normalize_face_value(m.group(1))
        out["基金面值"] = _fv(face, snippet=snippet)
        currency = _currency_from_face_snippet(snippet)
        if currency:
            out["币种"] = _fv(currency, snippet=snippet)

    return out
