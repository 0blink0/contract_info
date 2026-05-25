from pathlib import Path

from docx import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from backend.app.parse.outline import detect_outline
from backend.app.parse.schemas import Block, Document


def _iter_block_items(document: DocxDocument):
    parent_elm = document.element.body
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _outline_title(text: str, detected: dict) -> str:
    title = detected.get("title", "").strip()
    return title if title else text


def parse_docx(file_path: str) -> Document:
    path = Path(file_path)
    docx = DocxDocument(str(path))

    outline: list[dict] = []
    blocks: list[Block] = []
    current_section_id: str | None = None
    sec_counter = 0
    block_counter = 0
    table_counter = 0
    paragraph_counter = 0

    for element in _iter_block_items(docx):
        if isinstance(element, Paragraph):
            text = element.text.strip()
            if not text:
                continue
            detected = detect_outline(text)
            if detected is not None:
                sec_counter += 1
                current_section_id = f"sec_{sec_counter:03d}"
                outline.append(
                    {
                        "anchor_id": current_section_id,
                        "title": _outline_title(text, detected),
                        "level": detected.get("level", 1),
                    }
                )
            block_counter += 1
            blocks.append(
                {
                    "id": f"b_{block_counter:03d}",
                    "type": "paragraph",
                    "section_id": current_section_id,
                    "text": text,
                }
            )
            paragraph_counter += 1
        elif isinstance(element, Table):
            rows: list[list[str]] = []
            for row in element.rows:
                rows.append([cell.text.strip().replace("\n", " ") for cell in row.cells])
            if not any(any(cell for cell in r) for r in rows):
                continue
            table_counter += 1
            blocks.append(
                {
                    "id": f"t_{table_counter:03d}",
                    "type": "table",
                    "section_id": current_section_id,
                    "rows": rows,
                }
            )

    return {
        "source_file": path.name,
        "format": "docx",
        "metadata": {
            "paragraph_count": paragraph_counter,
            "table_count": table_counter,
            "block_count": len(blocks),
        },
        "outline": outline,
        "blocks": blocks,
    }
