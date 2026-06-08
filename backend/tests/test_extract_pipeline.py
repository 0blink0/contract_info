import os

import pytest

from backend.app.extract.field_catalog import DEFAULT_PRODUCT_VALUES, FIXED_PRODUCT_VALUES
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
    result, warnings, path_b = extract_document_sync(sample_document, llm_client=_LlmOff())  # type: ignore[arg-type]
    assert path_b == {}
    assert result.product_elements == {} or sum(
        1 for fv in result.product_elements.values() if fv.value
    ) == len(FIXED_PRODUCT_VALUES) + len(DEFAULT_PRODUCT_VALUES)
    assert result.fee_rates == []
    assert any(w.code == "llm_unavailable" for w in warnings)
