from __future__ import annotations

import re
from datetime import datetime


def normalize_date_slash(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    m = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}/{int(m.group(3))}"

    m = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日?", text)
    if m:
        return f"{int(m.group(1))}/{int(m.group(2))}/{int(m.group(3))}"

    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text[:10], fmt)
            return f"{dt.year}/{dt.month}/{dt.day}"
        except ValueError:
            continue
    return text
