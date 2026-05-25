import os

import pytest

from backend.app.extract.pipeline import extract_document_sync
from backend.app.parse import parse_docx
from backend.app.parse.schemas import document_to_dict


@pytest.fixture
def sample_document(example_docx_path):
    doc = parse_docx(str(example_docx_path))
    return document_to_dict(doc)


class _LlmOff:
    available = False
    model_name = ""


def test_pipeline_without_llm(sample_document):
    os.environ.pop("OPENAI_API_KEY", None)
    result, warnings = extract_document_sync(sample_document, llm_client=_LlmOff())  # type: ignore[arg-type]
    pe = result.product_elements
    filled = sum(1 for fv in pe.values() if fv.value not in (None, ""))
    assert filled >= 7
    assert len(result.fee_rates) >= 2
    assert isinstance(warnings, list)
