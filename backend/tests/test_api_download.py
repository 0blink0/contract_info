import uuid
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.config import PROJECT_ROOT


def test_download_requires_exported(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="parsed",
        product_xlsx_path=None,
        fee_xlsx_path=None,
        filename="a.docx",
        error_message=None,
        extraction_warnings=None,
        outline_preview=None,
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/download/product-elements",
            headers=api_headers,
        )
    assert response.status_code == 409


def test_download_success_when_exported(api_client, api_headers, tmp_path, monkeypatch):
    job_id = uuid.uuid4()
    export_file = tmp_path / "product_elements.xlsx"
    export_file.write_bytes(b"PK")

    rel = f"exports/{job_id}/product_elements.xlsx"
    full = PROJECT_ROOT / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(b"PK")

    record = SimpleNamespace(
        id=job_id,
        status="exported",
        product_xlsx_path=rel,
        fee_xlsx_path=None,
        filename="a.docx",
        error_message=None,
        extraction_warnings=[],
        outline_preview=None,
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/download/product-elements",
            headers=api_headers,
        )
    assert response.status_code == 200
    assert "spreadsheet" in response.headers.get("content-type", "")
