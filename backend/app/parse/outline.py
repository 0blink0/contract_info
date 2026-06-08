import re
from typing import Pattern

from backend.app.parse.schemas import OutlineItem

OUTLINE_PATTERNS: list[tuple[Pattern[str], int]] = [
    # 第X章 / 第X部分 / 第X篇 — all standard chapter formats in Chinese fund contracts
    (re.compile(r"^第[零一二三四五六七八九十百]+章[：:\s]?(.*)$"), 1),
    (re.compile(r"^第[零一二三四五六七八九十百]+部分[：:\s]?(.*)$"), 1),
    (re.compile(r"^第[零一二三四五六七八九十百]+篇[：:\s]?(.*)$"), 1),
    (re.compile(r"^([一二三四五六七八九十]+)[、．](.*)$"), 1),
    (re.compile(r"^(\d+)[、](.*)$"), 1),
]


def detect_outline(paragraph_text: str) -> OutlineItem | None:
    text = paragraph_text.strip()
    if not text:
        return None
    for pattern, level in OUTLINE_PATTERNS:
        match = pattern.match(text)
        if not match:
            continue
        groups = match.groups()
        title = groups[-1].strip() if groups[-1] else text
        if not title:
            title = text
        return {"anchor_id": "", "title": title, "level": level}
    return None


def build_outline(paragraph_texts: list[str]) -> list[OutlineItem]:
    outline: list[OutlineItem] = []
    counter = 0
    for paragraph in paragraph_texts:
        item = detect_outline(paragraph)
        if item is None:
            continue
        counter += 1
        item["anchor_id"] = f"sec_{counter:03d}"
        outline.append(item)
    return outline


def section_id_for_paragraph_index(
    paragraph_index: int, outline_paragraph_indices: list[tuple[int, str]]
) -> str | None:
    current: str | None = None
    for idx, anchor_id in outline_paragraph_indices:
        if idx <= paragraph_index:
            current = anchor_id
        else:
            break
    return current
