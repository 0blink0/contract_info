from __future__ import annotations

from backend.app.extract.schemas import ShareClassRow


def _row_score(row: ShareClassRow) -> int:
    score = 0
    if row.分级份额名称:
        score += 2
    if row.分级份额简称:
        score += 1
    if row.分级份额代码:
        score += 1
    if row.基金代码:
        score += 1
    return score


def merge_share_classes(
    rules: list[ShareClassRow],
    llm: list[ShareClassRow],
) -> list[ShareClassRow]:
    """Prefer the richer rules output when LLM returns sparse rows."""
    if not llm:
        return rules
    if not rules:
        return llm
    rules_score = sum(_row_score(r) for r in rules)
    llm_score = sum(_row_score(r) for r in llm)
    if len(rules) >= len(llm) and rules_score >= llm_score:
        return rules
    if len(llm) > len(rules) and llm_score > rules_score:
        return llm
    return rules
