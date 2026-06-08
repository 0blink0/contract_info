"""Share-class text helpers (validation only)."""

from __future__ import annotations

import re

_SHARE_COL = re.compile(r"([A-D])\s*类(?:份额)?", re.IGNORECASE)


def share_letters_in_text(text: str) -> set[str]:
    return {m.group(1).upper() for m in _SHARE_COL.finditer(text)}
