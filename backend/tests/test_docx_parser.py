from backend.app.parse import parse_docx


def test_parse_example_docx(example_docx_path):
    doc = parse_docx(str(example_docx_path))
    assert doc["format"] == "docx"
    assert len(doc["blocks"]) > 0
    assert len(doc["outline"]) >= 1
    assert any(b.get("section_id") for b in doc["blocks"])
