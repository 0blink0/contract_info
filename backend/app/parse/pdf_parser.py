from pathlib import Path

import fitz

from backend.app.parse.outline import detect_outline
from backend.app.parse.schemas import Block, Document


def _in_any_table(cx: float, cy: float, table_bboxes: list) -> bool:
    pt = fitz.Point(cx, cy)
    return any(pt in tr for tr in table_bboxes)


def parse_pdf(file_path: str) -> Document:
    path = Path(file_path)
    doc = fitz.open(str(path))

    outline: list[dict] = []
    blocks: list[Block] = []
    current_section_id: str | None = None
    sec_counter = 0
    block_counter = 0
    table_counter = 0
    paragraph_counter = 0

    for page in doc:
        tabs = page.find_tables()
        table_bboxes = [fitz.Rect(t.bbox) for t in tabs.tables]

        # (y0, sort_key, kind, text_or_rows)
        page_items: list[tuple[float, int, str, object]] = []

        for t in tabs.tables:
            rows = t.extract()
            clean = [
                [str(cell or "").strip().replace("\n", " ") for cell in row]
                for row in rows
            ]
            if not any(any(c for c in r) for r in clean):
                continue
            page_items.append((t.bbox[1], 1, "table", clean))

        for bx0, by0, bx1, by1, text, _blk_no, blk_type in page.get_text("blocks"):
            if blk_type != 0:
                continue
            text = text.strip()
            if not text:
                continue
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            if _in_any_table(cx, cy, table_bboxes):
                continue
            # Merge wrapped lines into one paragraph
            merged = " ".join(line.strip() for line in text.splitlines() if line.strip())
            page_items.append((by0, 0, "paragraph", merged))

        page_items.sort(key=lambda x: (x[0], x[1]))

        for _y0, _sk, kind, payload in page_items:
            if kind == "paragraph":
                text = str(payload)
                detected = detect_outline(text)
                if detected is not None:
                    sec_counter += 1
                    current_section_id = f"sec_{sec_counter:03d}"
                    outline.append(
                        {
                            "anchor_id": current_section_id,
                            "title": detected.get("title") or text,
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
            else:
                table_counter += 1
                blocks.append(
                    {
                        "id": f"t_{table_counter:03d}",
                        "type": "table",
                        "section_id": current_section_id,
                        "rows": payload,
                    }
                )

    doc.close()

    return {
        "source_file": path.name,
        "format": "pdf",
        "metadata": {
            "paragraph_count": paragraph_counter,
            "table_count": table_counter,
            "block_count": len(blocks),
        },
        "outline": outline,
        "blocks": blocks,
    }
