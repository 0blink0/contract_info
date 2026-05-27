from __future__ import annotations

import re
from typing import Any

from backend.app.extract.rules.party_helpers import (
    block_is_risk_disclosure,
    clean_org_name,
    is_valid_party_name,
)
from backend.app.extract.field_catalog import SKIP_PRODUCT_FIELDS
from backend.app.extract.schemas import FieldValue
from backend.app.extract.text_limits import excerpt_for_display

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
_RE_OUTSOURCE = re.compile(
    r"(国泰海通|国泰君安)[^。\n]{0,80}?(?:份额登记|估值核算)",
    re.IGNORECASE,
)
_RE_ORG_FORM = re.compile(
    r"基金组织形式[：:\s]*(契约型|公司型|合伙型)", re.IGNORECASE
)
_RE_ISSUER = re.compile(r"发行机构[：:\s]*([^\n\r，,；;]+)")
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
_RE_FUND_CLOSED_NONE = re.compile(r"本基金的封闭期[：:\s]*无", re.IGNORECASE)
_RE_REDEEM_BY_SHARE = re.compile(
    r"基金赎回采用份额申请|赎回采用份额申请", re.IGNORECASE
)
_RE_REDEEM_BY_AMOUNT = re.compile(r"支持[^。\n]{0,20}金额赎回", re.IGNORECASE)
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
_RE_INV_MANAGER_HEADER = re.compile(r"1、本基金的投资经理[：:\s]*")
_RE_MANAGER_NAME_LINE = re.compile(r"^([\u4e00-\u9fff]{2,4})[，,、]")
_RE_MANAGER_BRACKET = re.compile(r"【([\u4e00-\u9fff]{2,4})】")
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
_RE_BENCHMARK_SECTION = re.compile(
    r"（八）业绩比较基准[\s\S]{0,600}?(本基金[^。]{4,200}。)", re.DOTALL
)
_RE_BENCHMARK_LINE = re.compile(
    r"业绩比较基准[：:\s]*([^。\n]{4,120})", re.IGNORECASE
)
_RE_RISK_RETURN_SECTION = re.compile(
    r"（十）风险收益特征[\s\S]{0,500}?(本基金[^。]{10,300}。)", re.DOTALL
)
_RE_MANAGER_SECTION = re.compile(
    r"（十二）投资经理[\s\S]{0,2500}?(?:1、)?投资经理简介",
    re.DOTALL,
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
        snippet=excerpt_for_display(snippet) if snippet else None,
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
                best = (score, name, excerpt_for_display(text), bid, sid)

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


def _extract_investment_manager_names(text: str) -> tuple[str | None, str | None]:
    """Extract all manager personal names; join with 、 (几个写几个)."""
    names: list[str] = []
    seen: set[str] = set()
    snippet_start: int | None = None

    hdr = _RE_INV_MANAGER_HEADER.search(text)
    if hdr:
        snippet_start = hdr.start()
        block = text[hdr.end() : hdr.end() + 2500]
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            if "本基金设置" in line and "投资经理" in line:
                break
            m = _RE_MANAGER_NAME_LINE.match(line)
            if m:
                name = m.group(1)
                if name not in seen:
                    names.append(name)
                    seen.add(name)
            elif names and not re.match(r"^[\u4e00-\u9fff]{2,4}[，,、]", line):
                if "投资经理" in line and len(line) > 20:
                    continue
                break

    if not names:
        setup = re.search(r"本基金设置.{0,16}名投资经理", text)
        if setup:
            snippet_start = snippet_start if snippet_start is not None else setup.start()
            window = text[setup.start() : setup.start() + 1200]
            for m in _RE_MANAGER_BRACKET.finditer(window):
                name = m.group(1)
                if name not in seen:
                    names.append(name)
                    seen.add(name)

    if not names:
        m = re.search(
            r"本基金的投资经理[：:\s]*((?:[\u4e00-\u9fff]{2,4}[、，,]\s*)+[\u4e00-\u9fff]{2,4})",
            text,
        )
        if m:
            raw = re.split(r"[、，,]\s*", m.group(1).strip())
            for part in raw:
                part = part.strip()
                if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", part) and part not in seen:
                    names.append(part)
                    seen.add(part)
            snippet_start = m.start()

    if not names:
        return None, None

    snip = (
        excerpt_for_display(text[snippet_start:])
        if snippet_start is not None
        else ""
    )
    return "、".join(names), snip or None


def _extract_investment_chapter(inv_text: str) -> dict[str, FieldValue]:
    from backend.app.extract.field_snippets import extract_section_body, resolve_field_snippet

    out: dict[str, FieldValue] = {}
    for label, pattern in (
        ("投资目标", _RE_INV_OBJECTIVE),
        ("投资范围", _RE_INV_SCOPE),
        ("投资策略", _RE_INV_STRATEGY),
        ("投资限制", _RE_INV_LIMITS),
    ):
        m = pattern.search(inv_text)
        if m:
            body = re.sub(r"\s+", " ", m.group(1).strip())
            if len(body) >= 8:
                snip = resolve_field_snippet(label, inv_text, body[:80]) or excerpt_for_display(
                    body
                )
                out[label] = _fv(body, snippet=snip)
        elif label not in out:
            plain_body, plain_snip = extract_section_body(label, inv_text)
            if plain_body and len(plain_body) >= 8:
                out[label] = _fv(
                    plain_body,
                    snippet=plain_snip or excerpt_for_display(plain_body),
                )

    bench_body, bench_snip = extract_section_body("业绩比较基准", inv_text)
    if bench_body:
        if re.search(r"不设|无业绩|不存在业绩|不设置业绩", bench_body):
            out["业绩比较基准"] = _fv(
                "无", snippet=bench_snip or excerpt_for_display(bench_body)
            )
        else:
            out["业绩比较基准"] = _fv(
                bench_body, snippet=bench_snip or excerpt_for_display(bench_body)
            )
    else:
        m = _RE_BENCHMARK_SECTION.search(inv_text) or _RE_BENCHMARK_LINE.search(
            inv_text
        )
        if m:
            raw = m.group(1).strip()
            snip = excerpt_for_display(m.group(0))
            if re.search(r"不设|无业绩|不存在业绩", raw):
                out["业绩比较基准"] = _fv("无", snippet=snip)
            elif len(raw) >= 2:
                out["业绩比较基准"] = _fv(raw, snippet=snip)

    risk_body, risk_snip = extract_section_body("风险收益特征", inv_text)
    if risk_body:
        out["风险收益特征"] = _fv(
            risk_body,
            snippet=risk_snip
            or resolve_field_snippet("风险收益特征", inv_text, risk_body[:80]),
        )
    else:
        m = _RE_RISK_RETURN_SECTION.search(inv_text)
        if m:
            body = re.sub(r"\s+", " ", m.group(1).strip())
            snip = resolve_field_snippet("风险收益特征", inv_text, body[:80]) or excerpt_for_display(
                body
            )
            out["风险收益特征"] = _fv(body, snippet=snip)

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

    if "备案编码" not in SKIP_PRODUCT_FIELDS:
        for block in document.get("blocks") or []:
            text = _block_text(block)
            m = _RE_FILING.search(text)
            if m:
                out["备案编码"] = _fv(
                    m.group(1),
                    snippet=text,
                    block_id=block.get("id"),
                    section_id=block.get("section_id"),
                )
                break

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

    full_text = "\n".join(
        _block_text(b)
        for b in document.get("blocks") or []
        if b.get("type") == "paragraph"
    )
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

    closed_none = _RE_FUND_CLOSED_NONE.search(search_sub)
    if closed_none:
        out["是否封闭"] = _fv("不封闭", snippet=closed_none.group(0))
        out["封闭期"] = _fv("无", snippet=closed_none.group(0))
    elif not _RE_NOT_CLOSED.search(search_sub):
        m = _RE_CLOSED_PERIOD.search(search_sub)
        if m and "锁定期" not in m.group(1) and "最短持有" not in m.group(1):
            out["封闭期"] = _fv(m.group(1).strip(), snippet=m.group(0))

    if _RE_REDEEM_BY_SHARE.search(search_sub):
        m = _RE_REDEEM_BY_SHARE.search(search_sub)
        out["是否支持金额赎回"] = _fv("不支持", snippet=m.group(0))
    elif _RE_REDEEM_BY_AMOUNT.search(search_sub):
        m = _RE_REDEEM_BY_AMOUNT.search(search_sub)
        out["是否支持金额赎回"] = _fv("支持", snippet=m.group(0))

    stop_search = inv_text + risk_text + full_text
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

    m = _RE_RISK_GRADE.search(risk_text + "\n" + full_text)
    if m:
        out["风险等级"] = _fv(m.group(1).upper(), snippet=m.group(0))

    out.update(_extract_investment_chapter(inv_text))
    missing_inv = {
        k
        for k in (
            "投资目标",
            "投资范围",
            "投资策略",
            "投资限制",
            "业绩比较基准",
            "风险收益特征",
        )
        if k not in out
    }
    if missing_inv:
        fallback = _extract_investment_chapter(full_text)
        for key in missing_inv:
            if key in fallback:
                out[key] = fallback[key]

    inv_combined = "\n".join(
        filter(
            None,
            (
                inv_text,
                risk_text,
                windows.get("basic", ""),
            ),
        )
    )

    from backend.app.extract.field_snippets import resolve_field_snippet

    mgr_text = inv_combined + "\n" + full_text
    names, mgr_snip = _extract_investment_manager_names(mgr_text)
    if names and "可" not in names[:3] and "变更" not in names:
        snip = (
            mgr_snip
            or resolve_field_snippet("投资经理", inv_combined, names)
            or names
        )
        out["投资经理"] = _fv(names, snippet=snip)
        out["投资经理信息"] = _fv(names, snippet=snip)

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
