"""Shared helpers for party / org-name extraction from contract text."""

from __future__ import annotations

import re
from typing import Any

# Values that look like boilerplate, not institution names
_INVALID_PARTY_MARKERS = (
    "保证",
    "登记",
    "承诺",
    "风险",
    "投资者",
    "若根据",
    "所涉",
    "有权代表",
    "经营风险",
    "技术系统",
)

_ORG_SUFFIX = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9（）()·]{2,60}?(?:有限公司|有限责任公司|股份有限公司))"
)


def clean_org_name(raw: str) -> str:
    s = raw.strip()
    s = re.sub(r"^[（(]简称[^）)]*[）)]\s*[：:]?\s*", "", s)
    s = re.sub(r"^[：:\s]+", "", s)
    s = s.strip("。，,；; ")
    m = _ORG_SUFFIX.search(s)
    if m:
        return m.group(1).strip()
    return s[:80].strip() if s else ""


def is_valid_party_name(name: str) -> bool:
    if not name or len(name) < 4:
        return False
    if any(m in name for m in _INVALID_PARTY_MARKERS):
        return False
    if not re.search(r"公司|银行|证券|信托|基金|有限", name):
        return False
    return True


def section_title_for_block(document: dict[str, Any], block: dict[str, Any]) -> str:
    title_map = {
        item.get("anchor_id", ""): str(item.get("title", ""))
        for item in document.get("outline", [])
        if item.get("anchor_id")
    }
    return title_map.get(block.get("section_id") or "", "")


def block_is_risk_disclosure(document: dict[str, Any], block: dict[str, Any]) -> bool:
    title = section_title_for_block(document, block)
    if "风险揭示" in title or "风险提示" in title:
        return True
    text = str(block.get("text") or "")
    if block.get("type") == "table":
        rows = block.get("rows") or []
        text = "\n".join("\t".join(str(c) for c in row) for row in rows)
    return "风险揭示书" in text[:200] or (
        "私募基金管理人保证" in text and "登记" in text
    )
