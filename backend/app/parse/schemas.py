from typing import Any, Literal, TypedDict


class OutlineItem(TypedDict):
    anchor_id: str
    title: str
    level: int


class Block(TypedDict, total=False):
    id: str
    type: Literal["paragraph", "table"]
    section_id: str | None
    text: str
    rows: list[list[str]]


class Document(TypedDict):
    source_file: str
    format: Literal["docx"]
    metadata: dict[str, Any]
    outline: list[OutlineItem]
    blocks: list[Block]


def document_to_dict(doc: Document) -> dict[str, Any]:
    return {
        "source_file": doc["source_file"],
        "format": doc["format"],
        "metadata": doc["metadata"],
        "outline": doc["outline"],
        "blocks": doc["blocks"],
    }


def outline_preview_from_document(doc: Document) -> list[dict[str, Any]]:
    return [
        {
            "anchor_id": item["anchor_id"],
            "title": item["title"],
            "level": item.get("level", 1),
        }
        for item in doc["outline"]
    ]
