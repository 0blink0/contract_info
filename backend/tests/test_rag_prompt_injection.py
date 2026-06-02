import asyncio
from types import SimpleNamespace

import pytest

from backend.app.extract.pipeline import extract_document_sync
from backend.app.extract.llm.performance_fee import extract_performance_fee_section_llm
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict


@pytest.fixture
def sample_document(example_docx_path):
    doc = parse_docx(str(example_docx_path))
    return document_to_dict(doc)


class _ClientOn:
    available = True
    model_name = "mock"


class _ChatClient:
    available = True
    model_name = "mock"

    def __init__(self, result):
        self._result = result
        self.last_messages = None

    async def chat_json(self, messages, _schema):
        self.last_messages = messages
        return self._result


def test_fees_path_triggers_rag_search_and_injects_top_k(monkeypatch, sample_document):
    import backend.app.extract.pipeline as pipeline

    captured = {"query": None, "k": None, "called": 0}

    class _Kb:
        async def search_similar_entries(self, query: str, k: int):
            captured["query"] = query
            captured["k"] = k
            captured["called"] += 1
            return [
                {"field_name": "字段A", "field_value": "值A", "snippet": "摘录A"},
                {"field_name": "字段B", "field_value": "值B", "snippet": "摘录B"},
                {"field_name": "字段C", "field_value": "值C", "snippet": "摘录C"},
                {"field_name": "字段D", "field_value": "值D", "snippet": "摘录D"},
            ]

    async def _fake_extract_perf(client, fees_text, rag_cases):
        assert rag_cases is not None
        assert len(rag_cases) == 3
        return "raw", "是", []

    async def _fake_extract_open_day(client, text):
        return None, []

    monkeypatch.setattr(pipeline, "get_kb_service", lambda: _Kb())
    monkeypatch.setattr(pipeline, "extract_performance_fee_section_llm", _fake_extract_perf)
    monkeypatch.setattr(pipeline, "extract_open_day_section_llm", _fake_extract_open_day)

    extract_document_sync(sample_document, llm_client=_ClientOn())  # type: ignore[arg-type]

    assert captured["called"] == 1
    assert captured["k"] == 3
    assert isinstance(captured["query"], str) and captured["query"].strip()
    assert "业绩" in captured["query"] or "报酬" in captured["query"]


def test_prompt_injection_block_is_compact_and_has_no_score():
    parsed = SimpleNamespace(原文摘录="原文", 是否计提业绩报酬="是")
    client = _ChatClient(parsed)
    rag_cases = [
        {"field_name": "业绩报酬提取方式", "field_value": "高水位", "snippet": "示例摘录1", "score": 0.99},
        {"field_name": "提取时点", "field_value": "季度末", "snippet": "示例摘录2", "score": 0.88},
    ]

    asyncio.run(
        extract_performance_fee_section_llm(
            client,
            "本基金计提业绩报酬。",
            rag_cases=rag_cases,
        )
    )
    user_prompt = client.last_messages[1]["content"]

    assert "历史案例参考" in user_prompt
    assert "字段名：" in user_prompt
    assert "字段值：" in user_prompt
    assert "原文摘录：" in user_prompt
    assert "score" not in user_prompt.lower()
    assert "相似度" not in user_prompt


def test_empty_rag_cases_do_not_inject_block_and_still_succeed():
    parsed = SimpleNamespace(原文摘录="原文", 是否计提业绩报酬="是")
    client = _ChatClient(parsed)

    raw, flag, warnings = asyncio.run(
        extract_performance_fee_section_llm(
            client,
            "本基金计提业绩报酬。",
            rag_cases=[],
        )
    )
    user_prompt = client.last_messages[1]["content"]

    assert raw == "原文"
    assert flag == "是"
    assert warnings == []
    assert "历史案例参考" not in user_prompt
    assert "暂无案例" not in user_prompt
