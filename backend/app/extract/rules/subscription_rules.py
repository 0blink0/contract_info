from __future__ import annotations

import re
from typing import Any

from backend.app.extract.schemas import ShareClassRow, SubscriptionFeeRow
from backend.app.extract.section_windows import (
    _classify_section,
    gather_outline_chapter_text,
    section_title_map,
)
from backend.app.extract.text_limits import excerpt_for_display

_SHARE_COL = re.compile(r"([A-D])\s*类(?:份额)?", re.IGNORECASE)
_RATE_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_SHARE_LETTER = re.compile(r"^([A-D])\s*类", re.IGNORECASE)

_REDEEM_LT = re.compile(
    r"[（(]t[）)]?\s*[<＜]\s*(\d+)\s*日[^。\n]{0,120}?短期赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)
_REDEEM_RANGE = re.compile(
    r"(\d+)\s*日\s*[≤<=]\s*[（(]t[）)]?\s*[<＜]\s*(\d+)\s*日[^。\n]{0,120}?短期赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)
_REDEEM_GTE = re.compile(
    r"[（(]t[）)]?\s*[≥>＞=]\s*(\d+)\s*日[^。\n]{0,80}?不收取短期赎回"
)
_RE_RANGE_BEFORE_LT = re.compile(r"\d+\s*日\s*[≤<=]")
_RE_PURCHASE_RATE = re.compile(r"申购费率为\s*(\d+(?:\.\d+)?)\s*%")
_RE_SUBSCRIBE_RATE = re.compile(r"认购费率为\s*(\d+(?:\.\d+)?)\s*%")
_RE_REDEEM_HOLD_LT = re.compile(
    r"持有期低于\s*(\d+)\s*天[^。]{0,200}?赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)
_RE_REDEEM_HOLD_RANGE = re.compile(
    r"持有期在\s*(\d+)\s*天及以上但低于\s*(\d+)\s*天[^。]{0,120}?赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)
_RE_REDEEM_HOLD_GTE = re.compile(
    r"持有期在\s*(\d+)\s*天及以上(?!但低于)[^。]{0,100}?赎回费率为\s*(\d+(?:\.\d+)?)\s*%"
)

# CRM 申赎表：计费基准=不分段 / 区间（分段赎回）；区间开始/结束填天数；价内/价外在计费方式列
_BASIS_FLAT = "不分段"
_BASIS_SEGMENT = "区间"


def _segment_tier(**fields: str) -> dict[str, str]:
    out: dict[str, str] = {"计费基准": _BASIS_SEGMENT, "时间区间单位": "天"}
    out.update(fields)
    return out


def format_subscription_fund_name(full_name: str | None, share_letter: str) -> str:
    """石云：全称+份额字母；福禄：截至「一号」+ X类。"""
    if not full_name:
        return share_letter
    letter = share_letter.upper()
    if "福禄" in full_name and "一号" in full_name:
        idx = full_name.index("一号")
        return f"{full_name[: idx + 2]}{letter}类"
    if "证券投资基金" in full_name:
        return f"{full_name}{letter}"
    return f"{full_name}{letter}类"


def _parse_rate_cell(cell: object) -> str | None:
    if cell is None:
        return None
    text = str(cell).strip()
    if not text:
        return None
    m = _RATE_PCT.search(text)
    if m:
        return m.group(1)
    return None


def _share_letter_from_row(row: ShareClassRow) -> str | None:
    for raw in (row.分级份额简称, row.分级份额名称, row.代码类型):
        if not raw:
            continue
        m = _SHARE_LETTER.match(str(raw).strip())
        if m:
            return m.group(1).upper()
    return None


def _letters_from_share_classes(share_classes: list[ShareClassRow]) -> list[str]:
    letters: list[str] = []
    seen: set[str] = set()
    for row in share_classes:
        letter = _share_letter_from_row(row)
        if letter and letter not in seen:
            seen.add(letter)
            letters.append(letter)
    return letters


def _normalize_section_title(title: str) -> str:
    return re.sub(r"\t\d+\s*$", "", (title or "").strip())


def _is_basic_info_section(section_id: str | None, title_map: dict[str, str]) -> bool:
    title = _normalize_section_title(title_map.get(section_id or "", ""))
    if _classify_section(title) == "basic":
        return True
    return bool(re.search(r"基本情况|份额分类", title))


def _parse_share_fee_table_block(
    block: dict[str, Any],
) -> dict[str, dict[str, str]] | None:
    """Parse one table block → {letter: {认购费, 申购费, 赎回费}}."""
    if block.get("type") != "table":
        return None
    rows = block.get("rows") or []
    if len(rows) < 2:
        return None
    header = [str(c or "").strip() for c in rows[0]]
    col_letters: dict[int, str] = {}
    for idx, cell in enumerate(header):
        if idx == 0:
            continue
        m = _SHARE_COL.search(cell)
        if m:
            col_letters[idx] = m.group(1).upper()
    if len(col_letters) < 2:
        return None
    has_sub = any("认购" in str(r[0]) for r in rows[1:] if r)
    if not has_sub:
        return None
    out: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        if not row:
            continue
        label = str(row[0] or "").strip()
        fee_key: str | None = None
        if "认购" in label:
            fee_key = "认购费"
        elif "申购" in label:
            fee_key = "申购费"
        elif "赎回" in label:
            fee_key = "赎回费"
        else:
            continue
        for col_idx, letter in col_letters.items():
            if col_idx >= len(row):
                continue
            rate = _parse_rate_cell(row[col_idx])
            if rate is None:
                continue
            out.setdefault(letter, {})[fee_key] = rate
    return out or None


def _format_share_fee_table_excerpt(
    block: dict[str, Any],
    *,
    letter: str | None = None,
    fee_type: str | None = None,
) -> str:
    rows = block.get("rows") or []
    if not rows:
        return ""
    lines: list[str] = []
    header = [str(c or "").strip() for c in rows[0]]
    lines.append("\t".join(header))
    fee_label = {"认购费": "认购", "申购费": "申购", "赎回费": "赎回"}.get(fee_type or "", "")
    for row in rows[1:]:
        if not row:
            continue
        label = str(row[0] or "").strip()
        if fee_label and fee_label not in label:
            continue
        if letter:
            col_idx = None
            for idx, cell in enumerate(header):
                if idx == 0:
                    continue
                m = _SHARE_COL.search(str(cell))
                if m and m.group(1).upper() == letter.upper():
                    col_idx = idx
                    break
            if col_idx is not None and col_idx < len(row):
                lines.append(f"{label}\t{row[col_idx]}")
                continue
        lines.append("\t".join(str(c or "").strip() for c in row))
    return excerpt_for_display("\n".join(lines))


def parse_share_fee_table(
    document: dict[str, Any],
) -> tuple[dict[str, dict[str, str]], dict[str, Any] | None]:
    """
    基本情况中的份额分类表优先；返回 (费率, 表 block)。
    费率供导出；表摘录供校验「费率」列。
    """
    title_map = section_title_map(document)
    best: tuple[int, int, dict[str, Any], dict[str, dict[str, str]]] | None = None
    for block in document.get("blocks") or []:
        rates = _parse_share_fee_table_block(block)
        if not rates:
            continue
        in_basic = _is_basic_info_section(block.get("section_id"), title_map)
        score = (3 if in_basic else 1, sum(len(v) for v in rates.values()))
        if best is None or score > (best[0], best[1]):
            best = (score[0], score[1], block, rates)
    if not best:
        return {}, None
    return best[3], best[2]


def _parse_share_fee_table(document: dict[str, Any]) -> dict[str, dict[str, str]]:
    rates, _ = parse_share_fee_table(document)
    return rates


def _tier_from_redeem_line(line: str) -> dict[str, str] | None:
    """Parse one numbered short-redemption bullet; avoid matching t<360 inside 180≤t<360."""
    text = line.strip()
    if "短期赎回" not in text and "t" not in text.lower():
        return None

    m = _REDEEM_GTE.search(text)
    if m:
        return _segment_tier(区间开始=m.group(1), 费率="0")

    m = _REDEEM_RANGE.search(text)
    if m:
        return _segment_tier(
            区间开始=m.group(1),
            区间结束=m.group(2),
            费率=m.group(3),
        )

    if _RE_RANGE_BEFORE_LT.search(text):
        return None
    m = _REDEEM_LT.search(text)
    if m:
        return _segment_tier(区间结束=m.group(1), 费率=m.group(2))
    return None


def _collect_short_redemption_lines(
    subscription_text: str, document: dict[str, Any]
) -> list[str]:
    lines: list[str] = []
    if subscription_text.strip():
        lines.extend(subscription_text.splitlines())
    for block in document.get("blocks") or []:
        if block.get("type") != "paragraph":
            continue
        chunk = str(block.get("text") or "").strip()
        if "短期赎回" in chunk:
            lines.extend(chunk.splitlines())
    return lines


def _extract_redeem_tiers(
    subscription_text: str, document: dict[str, Any]
) -> list[dict[str, str]]:
    lines = _collect_short_redemption_lines(subscription_text, document)
    if not any("短期赎回" in ln for ln in lines):
        return []
    tiers: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for line in lines:
        tier = _tier_from_redeem_line(line)
        if not tier:
            continue
        key = (
            tier.get("计费基准", ""),
            tier.get("区间开始", ""),
            tier.get("区间结束", ""),
            tier.get("费率", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        tiers.append(tier)
    return tiers


_RAISING_BLOCK_MARKERS = (
    "认购费率为",
    "认购费率",
    "认购的费率",
    "认购费用",
    "认购份额",
    "净认购金额",
)
_SUBSCRIPTION_BLOCK_MARKERS = (
    "申购和赎回",
    "申购费用",
    "申购费率",
    "申购费率为",
    "赎回费率",
    "赎回费率为",
    "短期赎回",
    "持有期低于",
    "持有期在",
    "价内法",
    "价外法",
    "净申购金额",
)
_COMBINED_RULE_MARKERS = _RAISING_BLOCK_MARKERS + _SUBSCRIPTION_BLOCK_MARKERS

_RATE_MARKERS_SUBSCRIBE = ("认购费率为", "认购费率")
_RATE_MARKERS_PURCHASE = ("申购费率为", "申购费率", "申购和赎回的费率")
_BILLING_MARKERS_SUBSCRIBE = (
    "净认购金额=",
    "净认购金额＝",
    "认购份额=",
    "认购份额＝",
    "认购费用=认购金额",
    "认购费用＝认购金额",
    "认购金额×认购费率/（1+认购费率）",
)
_BILLING_MARKERS_PURCHASE = (
    "净申购金额=",
    "净申购金额＝",
    "申购份额=",
    "申购份额＝",
    "申购费用=申购金额",
    "申购费用＝申购金额",
    "申购金额×申购费率/（1+申购费率）",
)
_SNIPPET_MARKERS_SUBSCRIBE = _RATE_MARKERS_SUBSCRIBE + _BILLING_MARKERS_SUBSCRIBE
_SNIPPET_MARKERS_PURCHASE = _RATE_MARKERS_PURCHASE + _BILLING_MARKERS_PURCHASE
_SNIPPET_MARKERS_REDEEM = (
    "赎回费率为",
    "赎回费率",
    "短期赎回费率为",
    "持有期低于",
    "持有期在",
    "不收取短期赎回",
)


def _append_paragraph_blocks(document: dict[str, Any], markers: tuple[str, ...], chunks: list[str]) -> None:
    seen: set[str] = set(chunks)
    for block in document.get("blocks") or []:
        if block.get("type") != "paragraph":
            continue
        text = str(block.get("text") or "").strip()
        if not text or text in seen:
            continue
        if any(m in text for m in markers):
            chunks.append(text)
            seen.add(text)


def gather_raising_fee_text(
    document: dict[str, Any],
    windows: dict[str, str],
) -> str:
    """募集章（按 outline 目录定位，兼容「基金的募集/私募基金的募集」）+ 遗漏段落补全。"""
    chunks: list[str] = []
    outline_text = gather_outline_chapter_text(document, "raising").strip()
    if outline_text:
        chunks.append(outline_text)
    else:
        part = (windows.get("raising") or "").strip()
        if part:
            chunks.append(part)
    _append_paragraph_blocks(document, _RAISING_BLOCK_MARKERS, chunks)
    return "\n".join(chunks)


def gather_subscription_chapter_text(
    document: dict[str, Any],
    windows: dict[str, str],
) -> str:
    """申赎章（按 outline 目录）+ 申购/赎回费率与分段段落补全。"""
    chunks: list[str] = []
    outline_text = gather_outline_chapter_text(document, "subscription").strip()
    if outline_text:
        chunks.append(outline_text)
    else:
        part = (windows.get("subscription") or "").strip()
        if part:
            chunks.append(part)
    _append_paragraph_blocks(document, _SUBSCRIPTION_BLOCK_MARKERS, chunks)
    return "\n".join(chunks)


def gather_subscription_rules_text(
    document: dict[str, Any],
    windows: dict[str, str],
) -> str:
    """申赎 + 募集章节及含认购/申购计算公式的段落（计费方式推断用）。"""
    chunks: list[str] = []
    raising = gather_raising_fee_text(document, windows)
    subscription = gather_subscription_chapter_text(document, windows)
    if raising:
        chunks.append(raising)
    if subscription:
        chunks.append(subscription)
    _append_paragraph_blocks(document, _COMBINED_RULE_MARKERS, chunks)
    return "\n".join(chunks)


def _best_snippet_around_markers(text: str, markers: tuple[str, ...]) -> str:
    """Pick first matching marker in priority order (specific phrases before generic)."""
    if not text.strip():
        return ""
    for marker in markers:
        pos = text.find(marker)
        if pos < 0:
            continue
        start = max(0, pos - 160)
        end = min(len(text), pos + max(420, len(marker) + 300))
        return excerpt_for_display(text[start:end])
    return excerpt_for_display(text)


def _billing_snippet_from_chapter(
    fee_type: str,
    document: dict[str, Any],
    windows: dict[str, str],
) -> str | None:
    """价内/价外依据：募集章（认购）或申赎章（申购/赎回）中的计算公式。"""
    if fee_type == "认购费":
        source = gather_raising_fee_text(document, windows)
        markers = _BILLING_MARKERS_SUBSCRIBE
    elif fee_type == "申购费":
        source = gather_subscription_chapter_text(document, windows)
        markers = _BILLING_MARKERS_PURCHASE
    else:
        source = gather_subscription_chapter_text(document, windows)
        markers = _SNIPPET_MARKERS_REDEEM
    if not source.strip():
        return None
    return _best_snippet_around_markers(source, markers) or None


def _rate_snippet_from_chapter(
    fee_type: str,
    document: dict[str, Any],
    windows: dict[str, str],
) -> str | None:
    """无份额分类表时，从对应章节叙述中取费率摘录。"""
    if fee_type == "认购费":
        source = gather_raising_fee_text(document, windows)
        markers = _RATE_MARKERS_SUBSCRIBE
    elif fee_type == "申购费":
        source = gather_subscription_chapter_text(document, windows)
        markers = _RATE_MARKERS_PURCHASE
    else:
        source = gather_subscription_chapter_text(document, windows)
        markers = _SNIPPET_MARKERS_REDEEM
    if not source.strip():
        return None
    return _best_snippet_around_markers(source, markers) or None


def compose_subscription_row_snippet(
    fee_type: str,
    document: dict[str, Any],
    windows: dict[str, str],
    *,
    table_block: dict[str, Any] | None = None,
    letter: str | None = None,
    rate_from_table: bool = False,
) -> str | None:
    """摘录：有基本情况份额分类表则费率引表；价内/价外公式引募集或申赎章；无表则均在相应章节。"""
    parts: list[str] = []
    if rate_from_table and table_block:
        table_part = _format_share_fee_table_excerpt(
            table_block, letter=letter, fee_type=fee_type
        )
        if table_part:
            parts.append(f"【基本情况·份额分类表】\n{table_part}")
    elif not rate_from_table:
        rate_part = _rate_snippet_from_chapter(fee_type, document, windows)
        if rate_part:
            parts.append(f"【合同条款·费率】\n{rate_part}")
    billing_part = _billing_snippet_from_chapter(fee_type, document, windows)
    if billing_part:
        parts.append(f"【合同条款·计费公式】\n{billing_part}")
    if not parts:
        return subscription_fee_snippet(fee_type, document, windows)
    return excerpt_for_display("\n\n".join(parts))


def subscription_fee_snippet(
    fee_type: str | None,
    document: dict[str, Any],
    windows: dict[str, str],
) -> str | None:
    """Fallback：按费种取对应章节摘录。"""
    if not fee_type:
        return None
    if fee_type == "认购费":
        source = gather_raising_fee_text(document, windows)
        markers = _SNIPPET_MARKERS_SUBSCRIBE
    elif fee_type == "申购费":
        source = gather_subscription_chapter_text(document, windows)
        markers = _SNIPPET_MARKERS_PURCHASE
    else:
        source = gather_subscription_chapter_text(document, windows)
        markers = _SNIPPET_MARKERS_REDEEM
    if not source.strip():
        return None
    snip = _best_snippet_around_markers(source, markers)
    return snip or None


def _collect_fee_section_text(
    document: dict[str, Any],
    windows: dict[str, str],
) -> str:
    return gather_subscription_rules_text(document, windows)


def infer_subscription_billing_rules(text: str) -> dict[str, str]:
    """规则 fallback：按认购/申购/赎回计算公式分别推断价内/价外。"""
    if not text.strip():
        return {}
    out: dict[str, str] = {}

    if re.search(
        r"申购份额\s*=\s*申购金额\s*/\s*（?\s*1\s*\+\s*申购费率",
        text,
    ) or re.search(
        r"申购金额\s*/\s*（?\s*1\s*\+\s*申购费率\s*）?\s*/\s*申购价格",
        text,
    ):
        out["申购费"] = "价外法"
    elif re.search(
        r"申购费用\s*=\s*申购金额\s*[×x＊]?\s*申购费率\s*/\s*（?\s*1\s*\+\s*申购费率",
        text,
    ) or re.search(
        r"申购份额\s*=\s*[（(]?\s*申购金额\s*[-－]\s*申购费用",
        text,
    ):
        out["申购费"] = "价内法"

    if re.search(
        r"认购费用\s*=\s*认购金额\s*[×x＊]\s*认购费率\s*/\s*（?\s*1\s*\+\s*认购费率",
        text,
    ) or re.search(
        r"认购份额\s*=\s*[（(]?\s*认购金额\s*[-－]\s*认购费用",
        text,
    ):
        out["认购费"] = "价内法"
    elif re.search(
        r"认购金额\s*/\s*（?\s*1\s*\+\s*认购费率",
        text,
    ) or re.search(
        r"净认购金额\s*=\s*认购金额\s*/\s*（?\s*1\s*\+\s*认购费率",
        text,
    ):
        out["认购费"] = "价外法"

    if re.search(
        r"赎回金额\s*=\s*[^。\n]{0,160}?赎回费用",
        text,
    ) or re.search(
        r"赎回费用\s*=\s*赎回(?:份数|份额)\s*[×x＊]\s*赎回价格\s*[×x＊]\s*赎回费率",
        text,
    ):
        out["赎回费"] = "价内法"
    elif re.search(
        r"赎回份额\s*=\s*赎回金额\s*/\s*（?\s*1\s*\+\s*赎回费率",
        text,
    ):
        out["赎回费"] = "价外法"

    if "价内法" in text or "价内收费" in text:
        if "认购" in text and "认购费" not in out:
            out.setdefault("认购费", "价内法")
        if "申购" in text and "申购费" not in out:
            out.setdefault("申购费", "价内法")
    if "价外法" in text or "价外收费" in text:
        if "认购" in text and "认购费" not in out:
            out.setdefault("认购费", "价外法")
        if "申购" in text and "申购费" not in out:
            out.setdefault("申购费", "价外法")
    return out


def apply_subscription_billing(
    rows: list[SubscriptionFeeRow],
    billing_by_type: dict[str, str],
) -> None:
    for row in rows:
        fee_type = row.申赎费类型
        if fee_type in ("认购费", "申购费", "赎回费") and billing_by_type.get(fee_type):
            row.计费方式 = billing_by_type[fee_type]


def _infer_subscription_billing(text: str) -> str | None:
    by_type = infer_subscription_billing_rules(text)
    return by_type.get("申购费") or by_type.get("认购费")


def _holding_period_redeem_tiers(text: str) -> list[dict[str, str]]:
    tiers: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()

    def _add(tier: dict[str, str]) -> None:
        key = (
            tier.get("计费基准", ""),
            tier.get("区间开始", ""),
            tier.get("区间结束", ""),
            tier.get("费率", ""),
        )
        if key in seen:
            return
        seen.add(key)
        tiers.append(tier)

    for m in _RE_REDEEM_HOLD_LT.finditer(text):
        _add(_segment_tier(区间结束=m.group(1), 费率=m.group(2)))
    for m in _RE_REDEEM_HOLD_RANGE.finditer(text):
        _add(
            _segment_tier(
                区间开始=m.group(1),
                区间结束=m.group(2),
                费率=m.group(3),
            )
        )
    for m in _RE_REDEEM_HOLD_GTE.finditer(text):
        _add(_segment_tier(区间开始=m.group(1), 费率=m.group(2)))
    return tiers


def _extract_narrative_subscription_fees(
    fund_name: str,
    fee_text: str,
    *,
    fund_code: str | None,
    document: dict[str, Any],
    windows: dict[str, str],
) -> list[SubscriptionFeeRow]:
    """无份额分类表时，从申购赎回章节叙述抽取（如正仁）。"""
    rows: list[SubscriptionFeeRow] = []
    billing_map = infer_subscription_billing_rules(fee_text)
    raising_text = gather_raising_fee_text(document, windows)
    sub_text = gather_subscription_chapter_text(document, windows)

    if m := _RE_SUBSCRIBE_RATE.search(raising_text) or _RE_SUBSCRIBE_RATE.search(fee_text):
        rows.append(
            SubscriptionFeeRow(
                基金名称=fund_name,
                基金代码=fund_code,
                申赎费类型="认购费",
                费率=m.group(1),
                费率类型="百分比",
                计费基准=_BASIS_FLAT,
                计费方式=billing_map.get("认购费"),
                snippet=compose_subscription_row_snippet(
                    "认购费", document, windows, rate_from_table=False
                ),
            )
        )
    purchase_src = sub_text or fee_text
    if m := _RE_PURCHASE_RATE.search(purchase_src) or _RE_PURCHASE_RATE.search(fee_text):
        rows.append(
            SubscriptionFeeRow(
                基金名称=fund_name,
                基金代码=fund_code,
                申赎费类型="申购费",
                费率=m.group(1),
                费率类型="百分比",
                计费基准=_BASIS_FLAT,
                计费方式=billing_map.get("申购费"),
                snippet=compose_subscription_row_snippet(
                    "申购费", document, windows, rate_from_table=False
                ),
            )
        )

    fake_doc = {
        "blocks": [
            {"type": "paragraph", "text": line}
            for line in fee_text.splitlines()
            if line.strip()
        ]
    }
    redeem_snip = compose_subscription_row_snippet(
        "赎回费", document, windows, rate_from_table=False
    )
    redeem_billing = infer_subscription_billing_rules(sub_text or fee_text).get(
        "赎回费"
    )
    for tier in _holding_period_redeem_tiers(sub_text or fee_text):
        rows.append(
            SubscriptionFeeRow(
                基金名称=fund_name,
                基金代码=fund_code,
                申赎费类型="赎回费",
                费率类型="百分比",
                计费方式=redeem_billing,
                snippet=redeem_snip,
                **tier,
            )
        )
    for tier in _extract_redeem_tiers(sub_text or fee_text, fake_doc):
        rows.append(
            SubscriptionFeeRow(
                基金名称=fund_name,
                基金代码=fund_code,
                申赎费类型="赎回费",
                费率类型="百分比",
                计费方式=redeem_billing,
                snippet=redeem_snip,
                **tier,
            )
        )
    return rows


def extract_subscription_fees_rules(
    document: dict[str, Any],
    windows: dict[str, str],
    *,
    fund_name: str | None,
    share_classes: list[ShareClassRow],
    product_elements: dict[str, Any],
) -> list[SubscriptionFeeRow]:
    del product_elements  # reserved for future fund-code lookup
    table_rates, table_block = parse_share_fee_table(document)
    letters = _letters_from_share_classes(share_classes) or sorted(table_rates.keys())

    rows: list[SubscriptionFeeRow] = []
    code_by_letter: dict[str, str | None] = {}
    for sc in share_classes:
        letter = _share_letter_from_row(sc)
        if letter:
            code_by_letter[letter] = sc.分级份额代码 or sc.基金代码

    raising_text = gather_raising_fee_text(document, windows)
    sub_chapter = gather_subscription_chapter_text(document, windows)
    fee_section = gather_subscription_rules_text(document, windows)
    billing_map = {
        **infer_subscription_billing_rules(raising_text),
        **infer_subscription_billing_rules(sub_chapter),
        **infer_subscription_billing_rules(fee_section),
    }

    if table_rates:
        for letter in letters:
            rates = table_rates.get(letter, {})
            display_name = format_subscription_fund_name(fund_name, letter)
            fund_code = code_by_letter.get(letter)
            for fee_type in ("认购费", "申购费"):
                rate = rates.get(fee_type)
                if rate is None:
                    continue
                rows.append(
                    SubscriptionFeeRow(
                        基金名称=display_name,
                        基金代码=fund_code,
                        申赎费类型=fee_type,
                        费率=rate,
                        费率类型="百分比",
                        计费基准=_BASIS_FLAT,
                        计费方式=billing_map.get(fee_type),
                        snippet=compose_subscription_row_snippet(
                            fee_type,
                            document,
                            windows,
                            table_block=table_block,
                            letter=letter,
                            rate_from_table=True,
                        ),
                    )
                )
            table_redeem = rates.get("赎回费")
            if table_redeem is not None:
                rows.append(
                    SubscriptionFeeRow(
                        基金名称=display_name,
                        基金代码=fund_code,
                        申赎费类型="赎回费",
                        费率=table_redeem,
                        费率类型="百分比",
                        计费基准=_BASIS_FLAT,
                        计费方式=billing_map.get("赎回费"),
                        snippet=compose_subscription_row_snippet(
                            "赎回费",
                            document,
                            windows,
                            table_block=table_block,
                            letter=letter,
                            rate_from_table=True,
                        ),
                    )
                )
    elif fund_name and fee_section.strip():
        parent_code: str | None = None
        for sc in share_classes:
            if sc.基金代码:
                parent_code = sc.基金代码
                break
        rows.extend(
            _extract_narrative_subscription_fees(
                fund_name,
                fee_section,
                fund_code=parent_code,
                document=document,
                windows=windows,
            )
        )

    sub_text = windows.get("subscription", "") or ""
    tiers = _extract_redeem_tiers(sub_text, document)
    has_tier_redeem = any(
        r.申赎费类型 == "赎回费" and r.计费基准 == _BASIS_SEGMENT for r in rows
    )
    if tiers and fund_name and (table_rates or not has_tier_redeem):
        parent_code: str | None = None
        for sc in share_classes:
            if sc.基金代码:
                parent_code = sc.基金代码
                break
        tier_snip = compose_subscription_row_snippet(
            "赎回费", document, windows, rate_from_table=bool(table_block)
        )
        for tier in tiers:
            rows.append(
                SubscriptionFeeRow(
                    基金名称=fund_name,
                    基金代码=parent_code,
                    申赎费类型="赎回费",
                    费率类型="百分比",
                    计费方式=billing_map.get("赎回费"),
                    snippet=tier_snip,
                    **tier,
                )
            )

    apply_subscription_billing(rows, billing_map)
    return rows
