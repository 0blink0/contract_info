from __future__ import annotations

import re
from typing import Any

from backend.app.export.date_format import normalize_date_slash

_EMPTY_VALUES = frozenset({"", "无", "不设", "未设", "none", "null"})


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"【[^】]*】", "", text)
    text = text.replace("\u3000", " ").strip()
    dated = normalize_date_slash(text)
    return dated if dated is not None else text


def normalize_pct(value: Any) -> str:
    text = normalize_cell(value)
    if not text:
        return ""
    text = text.replace("％", "%").strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*%?$", text)
    if m:
        num = m.group(1)
        if "." in num:
            return num.rstrip("0").rstrip(".") if "." in num else num
        return num
    return text


def normalize_party_name(value: Any) -> str:
    return normalize_cell(value)


def empty_equiv(a: Any, b: Any) -> bool:
    na = normalize_cell(a).lower()
    nb = normalize_cell(b).lower()
    if na in _EMPTY_VALUES:
        na = ""
    if nb in _EMPTY_VALUES:
        nb = ""
    return na == nb


def contains_normalized(haystack: Any, needle: Any) -> bool:
    h = normalize_cell(haystack)
    n = normalize_cell(needle)
    if not n:
        return empty_equiv(h, n)
    return n in h
