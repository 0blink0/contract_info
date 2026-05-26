import pytest

from backend.app.services.export_service import persist_export


@pytest.mark.integration
def test_export_persist_roundtrip(db_session, example_docx_path):
    from backend.app.services.extract_service import persist_extract_from_path

    session, created_ids = db_session
    file_id = persist_extract_from_path(str(example_docx_path))
    created_ids.append(file_id)

    product_path, fee_path, lock_path, share_path, subscription_path = persist_export(
        file_id
    )
    from backend.app.models.contract_file import ContractFile

    row = session.get(ContractFile, file_id)
    assert row.status == "exported"
    assert row.product_xlsx_path
    assert row.fee_xlsx_path
    assert row.lock_xlsx_path
    assert row.share_xlsx_path
    assert row.subscription_xlsx_path
    assert subscription_path
    assert row.path_b_json
    assert row.path_b_json.get("open_day")
    assert row.path_b_json.get("source_snippets")
