"""Map product fields to chapter windows for group-level 原文 excerpts."""

from __future__ import annotations

from backend.app.extract.text_limits import excerpt_for_display


def apply_row_group_snippet(rows: list, group_snippet: str | None) -> None:
    """Attach one group 原文 to every row (export/validation use per-row snippet)."""
    snip = (group_snippet or "").strip()
    if not snip:
        return
    snip = excerpt_for_display(snip)
    for row in rows:
        if getattr(row, "snippet", None) in (None, ""):
            row.snippet = snip
