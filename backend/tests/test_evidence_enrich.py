"""Tests for excerpt backfill on extraction results."""

from backend.app.extract.evidence_enrich import (
    enrich_extraction_dict,
    enrich_field_value,
    find_block_id_for_text,
)
from backend.app.extract.schemas import FieldValue
from backend.app.extract.section_windows import build_section_windows


def _doc_with_open_ended() -> dict:
    return {
        "blocks": [
            {
                "id": "b1",
                "type": "paragraph",
                "text": "本基金运作方式为开放式，每周开放申购与赎回。",
            }
        ],
        "outline": [],
    }


def test_enrich_field_value_fills_short_llm_value():
    doc = _doc_with_open_ended()
    windows, _ = build_section_windows(doc)
    fv = FieldValue(value="开放式", confidence="medium", source="llm")
    out = enrich_field_value(fv, "运作方式", windows, doc)
    assert out is not None
    assert out.snippet
    assert "开放式" in out.snippet
    assert out.block_id == "b1"


def test_enrich_skips_when_snippet_present():
    doc = _doc_with_open_ended()
    windows, _ = build_section_windows(doc)
    fv = FieldValue(
        value="开放式",
        snippet="已有摘录内容足够长可用于核对",
        source="llm",
    )
    out = enrich_field_value(fv, "运作方式", windows, doc)
    assert out.snippet == "已有摘录内容足够长可用于核对"


def test_enrich_extraction_dict_product_elements():
    doc = _doc_with_open_ended()
    extraction = {
        "product_elements": {
            "运作方式": {"value": "开放式", "source": "llm"},
        }
    }
    enrich_extraction_dict(extraction, doc)
    pe = extraction["product_elements"]["运作方式"]
    assert pe.get("snippet")
    assert "开放式" in pe["snippet"]


def test_find_block_id_for_text():
    doc = _doc_with_open_ended()
    assert find_block_id_for_text(doc, "运作方式为开放式") == "b1"
