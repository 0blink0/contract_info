import pytest

from backend.app.models import ContractFile
from backend.app.services.parse_service import persist_parse


@pytest.mark.integration
def test_persist_parse_roundtrip(example_docx_path, db_session):
    session, created_ids = db_session
    file_id = persist_parse(str(example_docx_path))
    created_ids.append(file_id)

    row = session.get(ContractFile, file_id)
    assert row is not None
    assert row.status == "parsed"
    assert row.parse_json is not None
    assert row.outline_preview is not None
    assert len(row.outline_preview) >= 1
