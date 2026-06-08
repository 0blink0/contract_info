"""Text length helpers: chapter text for LLM prompts may cap at model limits."""

from __future__ import annotations

import re

# Strip 【digit】 template placeholders — a common contract-template marker where
# the drafter fills in a number surrounded by fullwidth brackets (e.g. 【1】%).
# Normalising once before regex matching lets all extractors see plain digits.
_TEMPLATE_NUM_RE = re.compile(r"【(\d+(?:\.\d+)?)】")


def normalize_template_brackets(text: str) -> str:
    """Replace 【digit】 with digit; leave non-numeric 【…】 intact."""
    return _TEMPLATE_NUM_RE.sub(r"\1", text)

# Rules / section windows: no artificial cap (full classified chapter text).
# LLM: very high default; truncate only at paragraph boundary when exceeded.
LLM_PROMPT_MAX_CHARS = 200_000


def text_for_llm_prompt(text: str, *, max_chars: int = LLM_PROMPT_MAX_CHARS) -> str:
    """Send full chapter text to LLM when possible; avoid mid-sentence hard cuts."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last_break = max(cut.rfind("\n\n"), cut.rfind("\n"))
    if last_break > max_chars // 2:
        cut = cut[:last_break]
    return cut + "\n\n…（合同片段过长，已按段落截断供模型阅读；规则抽取仍使用全文）"


def excerpt_for_display(text: str, *, max_chars: int = 4000) -> str:
    """Evidence / preview snippets only — does not limit stored field values."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"
