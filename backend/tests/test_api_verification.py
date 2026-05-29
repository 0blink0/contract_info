import uuid
from types import SimpleNamespace
from unittest.mock import patch


def test_verification_requires_extracted(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="pending",
        extraction_result={"product_elements": {}},
        parse_json={},
        validation_result=None,
        filename="a.docx",
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/verification/product-elements",
            headers=api_headers,
        )
    assert response.status_code == 409


def test_verification_404(api_client, api_headers):
    from fastapi import HTTPException

    job_id = uuid.uuid4()

    def _missing(_id):
        raise HTTPException(status_code=404, detail="Job not found")

    with patch("backend.app.api.routes.jobs._get_record", side_effect=_missing):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/verification/product-elements",
            headers=api_headers,
        )
    assert response.status_code == 404


def test_verification_success(api_client, api_headers):
    job_id = uuid.uuid4()
    record = SimpleNamespace(
        id=job_id,
        status="extracted",
        extraction_result={
            "product_elements": {"基金全称": {"value": "测试"}},
        },
        parse_json={},
        validation_result=None,
        filename="a.docx",
    )

    with patch("backend.app.api.routes.jobs._get_record", return_value=record):
        response = api_client.get(
            f"/api/v1/jobs/{job_id}/verification/product-elements",
            headers=api_headers,
        )
    assert response.status_code == 200
    body = response.json()
    assert "rows" in body
    assert body["table_key"] == "product-elements"
    assert len(body["rows"]) >= 1


def test_invalid_table_key_422(api_client, api_headers):
    job_id = uuid.uuid4()
    response = api_client.get(
        f"/api/v1/jobs/{job_id}/verification/not-a-table",
        headers=api_headers,
    )
    assert response.status_code == 422
