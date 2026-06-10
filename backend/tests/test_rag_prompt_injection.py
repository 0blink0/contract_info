import pytest

from backend.app.extract.pipeline import extract_document_sync
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict


@pytest.fixture
def sample_document(example_docx_path):
    doc = parse_docx(str(example_docx_path))
    return document_to_dict(doc)


class _ClientOn:
    available = True
    model_name = "mock"


def test_fees_path_triggers_rag_search_and_injects_top_k(monkeypatch, sample_document):
    import backend.app.extract.pipeline as pipeline

    captured = {"query": None, "k": None, "called": 0}

    class _Kb:
        model_available = True

        async def search_similar_entries(self, query: str, k: int, *, field_name: str = ""):
            captured["query"] = query
            captured["k"] = k
            captured["called"] += 1
            return [
                {"field_name": "字段A", "field_value": "值A", "snippet": "摘录A"},
                {"field_name": "字段B", "field_value": "值B", "snippet": "摘录B"},
                {"field_name": "字段C", "field_value": "值C", "snippet": "摘录C"},
            ]

    _CRM_FIELDS_COUNT = 5  # 提取时点/业绩报酬提取方式/业绩基准类型/门槛净值类型/提取比例

    async def _fake_fees_combined(client, fees_text, sub_fees_text, *, fund_name, share_class_labels=None, rag_cases):
        # rag_cases should be 3 results × 5 fields = 15
        assert rag_cases is not None and len(rag_cases) == 3 * _CRM_FIELDS_COUNT
        return [], [], {}, "raw", "是", {}, {}, None, None, []

    async def _fake_product_combined(client, windows, *, fund_name):
        return {}, [], [], None, []

    monkeypatch.setattr(pipeline, "get_kb_service", lambda: _Kb())
    monkeypatch.setattr(pipeline, "extract_fees_combined_llm", _fake_fees_combined)
    monkeypatch.setattr(pipeline, "extract_product_combined_llm", _fake_product_combined)

    extract_document_sync(sample_document, llm_client=_ClientOn())  # type: ignore[arg-type]

    assert captured["called"] == _CRM_FIELDS_COUNT  # one search per CRM field
    assert captured["k"] == 3
    assert isinstance(captured["query"], str) and captured["query"].strip()
